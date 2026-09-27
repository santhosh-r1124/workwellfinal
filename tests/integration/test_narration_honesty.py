"""What the product is allowed to present as a model's words.

Running with no key configured is supported: every number comes from `ml/`,
and only the prose is lost. But the offline stand-in returns one fixed
string - a note to whoever deployed this, telling them to set
GEMINI_API_KEY - and `safe_generate` used to hand that straight to an
employee as a successful narration of their own work pattern.
"""

import pytest

from agents.narration import generates_text, safe_generate
from agents.providers.instrumented import InstrumentedProvider
from agents.providers.local_provider import LocalProvider


class Writes:
    """A provider that really does generate."""

    def generate(self, prompt, system=None):
        return "a sentence a model wrote"

    def embed(self, texts):
        return [[0.0]]


class Broken:
    generates_text = True

    def generate(self, prompt, system=None):
        raise RuntimeError("503")

    def embed(self, texts):
        return [[0.0]]


def test_the_offline_stand_in_does_not_claim_to_generate():
    assert generates_text(LocalProvider()) is False


def test_a_provider_that_says_nothing_is_assumed_to_generate():
    """A new vendor integration must never be silently downgraded to a
    stand-in because someone forgot to declare the attribute."""
    assert generates_text(Writes()) is True


def test_wrapping_a_provider_does_not_hide_what_it_cannot_do():
    """The factory always returns a wrapped provider, so a flag that
    stopped at the wrapper would read as True everywhere."""
    assert generates_text(InstrumentedProvider(LocalProvider(), "local")) is False


def test_the_stand_ins_own_string_never_reaches_an_employee():
    text, narrated = safe_generate(
        InstrumentedProvider(LocalProvider(), "local"),
        "why has my week changed?",
        None,
        fallback="Meetings are up 40% against your own median.",
    )

    assert narrated is False
    assert text == "Meetings are up 40% against your own median."
    assert "GEMINI_API_KEY" not in text
    assert "local-mode" not in text


def test_a_real_provider_is_still_used():
    text, narrated = safe_generate(Writes(), "prompt", None, fallback="evidence")

    assert narrated is True
    assert text == "a sentence a model wrote"


def test_an_unreachable_model_falls_back_without_raising():
    text, narrated = safe_generate(Broken(), "prompt", None, fallback="evidence")

    assert narrated is False
    assert text == "evidence"


@pytest.mark.parametrize("degraded_reason", ["not_configured", "unreachable"])
def test_the_api_names_which_kind_of_fallback_it_is(degraded_reason):
    """The two need different words: one is a deployment choice, the other
    is a fault someone should go and look at."""
    from shared.schemas.chat import ChatMessageOut

    out = ChatMessageOut(session_id="s", reply="r", degraded=True, degraded_reason=degraded_reason)

    assert out.degraded_reason == degraded_reason
