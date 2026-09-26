"""What the app insists on before it will serve anything.

The docs say WorkWell runs with no model at all - every number on the
dashboard comes from `ml/`, and `AI_PROVIDER=local` is the documented
offline path. The startup check demanded GEMINI_API_KEY regardless, so
that path exited at boot: a container that dies on start, in the one
configuration a first-time reader is told to try.
"""

import pytest
from fastapi.testclient import TestClient

from apps.backend.api.deps import get_db
from apps.backend.core.config import get_settings
from apps.backend.main import create_app


@pytest.fixture()
def configure(monkeypatch):
    """APP_ENV=test bypasses the check, which is what hid this.

    Settings are cached process-wide, so every change goes through
    monkeypatch - a plain assignment here leaks into every test that runs
    after it.
    """
    settings = get_settings()
    monkeypatch.setattr(type(settings), "is_test", property(lambda self: False))
    monkeypatch.setattr(settings, "gemini_api_key", "")

    def set_provider(name: str):
        monkeypatch.setattr(settings, "ai_provider", name)
        return settings

    return set_provider


def _client(db_session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def test_the_documented_keyless_path_starts(db_session, configure):
    configure("local")

    with _client(db_session) as client:
        assert client.get("/health").json()["ai"] == "not_configured"


def test_naming_gemini_without_a_key_still_refuses(db_session, configure):
    """The original guard was right about this case: a deployment that
    thinks it is generating text, and silently is not, is worse than one
    that will not start."""
    configure("gemini")

    with pytest.raises(RuntimeError) as err:
        with _client(db_session):
            pass

    message = str(err.value)
    assert "GEMINI_API_KEY" in message
    # and it has to say what the alternative is, or the reader is stuck
    assert "AI_PROVIDER=local" in message


def test_a_provider_that_needs_no_key_says_so(configure):
    assert configure("local").ai_key_required is False
    assert configure("gemini").ai_key_required is True
