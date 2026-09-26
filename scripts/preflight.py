"""Check the deployment config without a Docker daemon.

This exists because of a specific failure: the backend Dockerfile was
missing `COPY safety` for weeks, and then `COPY apps/worker`. Both would
have crashed the container on its first import, and neither was visible
in an environment with no Docker daemon - the test suite passes, the
imports resolve locally, and the broken image is only discovered on the
deploy it breaks.

So this checks statically what a build would otherwise discover
expensively:

  * every COPY source in every Dockerfile exists in its build context
  * every module a compose `command` runs is importable
  * every host path a compose file bind-mounts exists
  * every `${VAR:?required}` has a value, and maps to a real setting

It is not a substitute for building the images. It catches the class of
mistake that makes the first deploy fail for a reason that had nothing to
do with the deploy.

    python scripts/preflight.py [--env .env]
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILES = ["docker-compose.yml", "docker-compose.prod.yml"]

# Referenced in compose but supplied by the image or the platform rather
# than by our settings model.
NON_SETTING_VARS = {
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "BACKEND_PORT",
    "FRONTEND_PORT",
    "VITE_API_BASE_URL",
}

# Mounted at deploy time, not present in the repo.
EXPECTED_MISSING_MOUNTS = {"./docker/tls"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.checks = 0

    def check(self, ok: bool, message: str, warn_only: bool = False) -> None:
        self.checks += 1
        if ok:
            return
        (self.warnings if warn_only else self.errors).append(message)


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def dockerfile_copy_sources(dockerfile: Path) -> list[str]:
    sources: list[str] = []
    for raw in dockerfile.read_text().splitlines():
        line = raw.strip()
        if not line.upper().startswith("COPY "):
            continue
        parts = line.split()[1:]
        # `COPY --from=build /app/dist ...` copies from an earlier stage,
        # not from the build context.
        if any(p.startswith("--from=") for p in parts):
            continue
        parts = [p for p in parts if not p.startswith("--")]
        sources.extend(parts[:-1])
    return sources


def _build_paths(build) -> tuple[Path, Path]:
    context = ROOT / (build.get("context", ".") if isinstance(build, dict) else build)
    name = build.get("dockerfile", "Dockerfile") if isinstance(build, dict) else "Dockerfile"
    # A dockerfile path in compose is relative to the build context.
    return context, (context / name)


def check_build_contexts(compose: dict, compose_name: str, report: Report) -> None:
    for service, spec in (compose.get("services") or {}).items():
        build = spec.get("build")
        if not build:
            continue
        context, dockerfile = _build_paths(build)

        report.check(
            dockerfile.exists(), f"{compose_name}: {service} references missing {dockerfile}"
        )
        if not dockerfile.exists():
            continue

        for source in dockerfile_copy_sources(dockerfile):
            report.check(
                (context / source).exists(),
                f"{compose_name}: {service} would COPY '{source}', which is not in "
                f"its build context ({context.relative_to(ROOT)}) - the image would "
                f"build and then fail on import",
            )


def dockerfile_entrypoints(dockerfile: Path) -> list[str]:
    """Whatever the image is told to run: its own CMD/ENTRYPOINT."""
    lines = []
    for raw in dockerfile.read_text().splitlines():
        line = raw.strip()
        if line.upper().startswith(("CMD ", "ENTRYPOINT ")):
            lines.append(line.split(None, 1)[1])
    return lines


def modules_invoked(command) -> list[str]:
    """Modules a command line runs, whether via `python -m pkg` or
    `uvicorn pkg.module:app`."""
    text = " ".join(command) if isinstance(command, list) else str(command)
    text = text.replace('"', " ").replace("'", " ").replace(",", " ").replace("[", " ").replace("]", " ")
    parts = text.split()

    modules = []
    for i, part in enumerate(parts):
        if part == "-m" and i + 1 < len(parts):
            modules.append(parts[i + 1])
        elif ":" in part and "." in part.split(":")[0] and "/" not in part:
            modules.append(part.split(":")[0])
    return modules


def module_source(module: str) -> Path | None:
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ValueError):
        return None
    if spec is None:
        return None
    if spec.submodule_search_locations:
        return Path(list(spec.submodule_search_locations)[0])
    return Path(spec.origin) if spec.origin else None


def check_commands(compose: dict, compose_name: str, report: Report) -> None:
    """The check that matters: a module the container is told to run must
    also be copied into the image.

    Importable-on-this-machine is not the question - that was true of
    `apps.worker` while the Dockerfile that builds its image did not copy
    it. The image would build cleanly and the container would exit on
    start.
    """
    for service, spec in (compose.get("services") or {}).items():
        build = spec.get("build")
        if not build:
            continue

        context, dockerfile = _build_paths(build)
        if not dockerfile.exists():
            continue

        copied = [context / src for src in dockerfile_copy_sources(dockerfile)]
        commands = [spec["command"]] if spec.get("command") else dockerfile_entrypoints(dockerfile)

        for command in commands:
            for module in modules_invoked(command):
                source = module_source(module)
                report.check(
                    source is not None,
                    f"{compose_name}: {service} runs '{module}', which is not importable",
                )
                if source is None:
                    continue
                in_image = any(
                    source == path or path in source.parents for path in copied
                )
                report.check(
                    in_image,
                    f"{compose_name}: {service} runs '{module}' but "
                    f"{dockerfile.relative_to(ROOT)} never copies "
                    f"{source.relative_to(ROOT)} into the image - the container "
                    f"would exit on start",
                )


def check_mounts(compose: dict, compose_name: str, report: Report) -> None:
    for service, spec in (compose.get("services") or {}).items():
        for volume in spec.get("volumes") or []:
            if not isinstance(volume, str) or not volume.startswith("."):
                continue
            host = volume.split(":")[0]
            if host in EXPECTED_MISSING_MOUNTS:
                report.check(
                    (ROOT / host).exists(),
                    f"{compose_name}: {service} mounts {host}, supplied at deploy time",
                    warn_only=True,
                )
                continue
            report.check(
                (ROOT / host).exists(), f"{compose_name}: {service} mounts missing path {host}"
            )


FIRST_PARTY = {"agents", "ml", "rag", "safety", "integrations", "shared", "apps", "database"}
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([a-z_][a-z0-9_]*)", re.M)


def check_first_party_imports(compose: dict, compose_name: str, report: Report) -> None:
    """Transitive coverage: a package the copied code imports must itself
    be copied.

    This is the `COPY safety` omission. The image built, `apps.backend`
    was present, and the container died on the first import of a package
    nobody had listed - invisible locally, where every package is on the
    path whether the Dockerfile mentions it or not.
    """
    seen: set[Path] = set()

    for service, spec in (compose.get("services") or {}).items():
        build = spec.get("build")
        if not build:
            continue
        context, dockerfile = _build_paths(build)
        if not dockerfile.exists() or dockerfile in seen:
            continue
        seen.add(dockerfile)

        copied = [context / src for src in dockerfile_copy_sources(dockerfile)]
        copied_names = {
            path.relative_to(ROOT).parts[0] for path in copied if ROOT in path.parents or path == ROOT
        }
        if not copied_names & FIRST_PARTY:
            continue  # not a Python image (the frontend build)

        needed: dict[str, str] = {}
        for path in copied:
            if not path.exists():
                continue
            files = [path] if path.is_file() else path.rglob("*.py")
            for file in files:
                if file.suffix != ".py":
                    continue
                for package in IMPORT_RE.findall(file.read_text(errors="ignore")):
                    if package in FIRST_PARTY and package not in copied_names:
                        needed.setdefault(package, str(file.relative_to(ROOT)))

        for package, importer in sorted(needed.items()):
            report.check(
                False,
                f"{compose_name}: {dockerfile.relative_to(ROOT)} copies code that "
                f"imports '{package}' ({importer}) but never copies '{package}' - "
                f"the container would die on its first import",
            )


def required_vars(text: str) -> set[str]:
    return set(re.findall(r"\$\{([A-Z0-9_]+):\?", text))


def referenced_vars(text: str) -> set[str]:
    return set(re.findall(r"\$\{([A-Z0-9_]+)[:}]", text))


def check_env(compose_text: str, compose_name: str, env: dict, report: Report) -> None:
    for var in sorted(required_vars(compose_text)):
        value = env.get(var) or os.environ.get(var)
        report.check(
            bool(value),
            f"{compose_name}: {var} is required (${{{var}:?}}) but has no value",
        )
    check_provider_pair(compose_name, env, report)


def check_provider_pair(compose_name: str, env: dict, report: Report) -> None:
    """AI_PROVIDER and GEMINI_API_KEY are only valid together.

    The key cannot simply be ${GEMINI_API_KEY:?}: running with no model at
    all is a documented, supported configuration - the statistics do not
    depend on one. But leaving AI_PROVIDER at its gemini default with no
    key is a container that exits at boot, so the pair is checked here
    rather than the key alone."""
    def value(var: str) -> str:
        return (env.get(var) or os.environ.get(var) or "").strip()

    provider = value("AI_PROVIDER") or "gemini"
    if provider.lower() == "local":
        # Worth saying out loud rather than passing silently: this deploy
        # will show canned sentences to every employee, and no health check
        # will ever complain about it.
        report.check(
            False,
            f"{compose_name}: AI_PROVIDER=local - detection is unaffected, but every "
            f"explanation shown to an employee will be canned text, not generated",
            warn_only=True,
        )
        return
    report.check(
        bool(value("GEMINI_API_KEY")),
        f"{compose_name}: AI_PROVIDER={provider} needs GEMINI_API_KEY, which has no value "
        f"- set the key, or set AI_PROVIDER=local to run without a model",
    )


def check_settings_coverage(compose_text: str, compose_name: str, report: Report) -> None:
    """A compose file that sets FOO_BAR when the settings model calls it
    FOOBAR is silently ignored by pydantic-settings - the container starts
    with the default and the operator believes they configured it."""
    from apps.backend.core.config import Settings

    known = {name.upper() for name in Settings.model_fields}
    for var in sorted(referenced_vars(compose_text) | set(re.findall(r"^\s+([A-Z0-9_]+):", compose_text, re.M))):
        if var in NON_SETTING_VARS or var in known:
            continue
        report.check(
            False,
            f"{compose_name}: sets '{var}', which matches no field on Settings - "
            f"pydantic-settings will ignore it",
            warn_only=True,
        )


def check_env_example(report: Report) -> None:
    """Anything the settings model reads should be discoverable in
    .env.example, or an operator has to read the source to configure it."""
    from apps.backend.core.config import Settings

    documented = set(load_env_file(ROOT / ".env.example"))
    undocumented = sorted(
        name.upper()
        for name in Settings.model_fields
        if name.upper() not in documented
    )
    for name in undocumented:
        report.check(False, f".env.example does not document {name}", warn_only=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=".env", help="env file to validate against")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    env = load_env_file(ROOT / args.env)
    report = Report()

    for name in COMPOSE_FILES:
        path = ROOT / name
        if not path.exists():
            report.check(False, f"missing {name}")
            continue

        text = path.read_text()
        try:
            compose = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            report.check(False, f"{name}: invalid YAML - {exc}")
            continue

        check_build_contexts(compose, name, report)
        check_commands(compose, name, report)
        check_first_party_imports(compose, name, report)
        check_mounts(compose, name, report)
        check_settings_coverage(text, name, report)
        if name.endswith("prod.yml") and env:
            check_env(text, name, env, report)

    check_env_example(report)

    if not env:
        # Structure is still worth checking in CI, where there is no .env
        # and nothing to check values against.
        report.warnings.append(
            f"no {args.env} found - checked structure only, not configured values"
        )

    print(f"preflight: {report.checks} checks")
    for warning in report.warnings:
        print(f"  warn  {warning}")
    for error in report.errors:
        print(f"  FAIL  {error}")

    if report.errors:
        print(f"\n{len(report.errors)} problem(s) would break a deploy.")
        return 1

    print(f"\nno blocking problems ({len(report.warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
