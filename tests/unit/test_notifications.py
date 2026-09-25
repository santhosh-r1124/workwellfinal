"""What a notification is allowed to say.

Work email is not a private channel: it is archived, scanned by DLP,
synced to phones that sit unlocked on desks, and in most jurisdictions
readable by the employer. So the notification may say that something is
waiting and nothing about what it is. These tests exist to make that
rule break loudly if someone later decides a helpful summary in the
subject line would improve engagement.
"""

from email import message_from_string

import pytest

from apps.backend.core.config import get_settings
from apps.backend.core.observability import REGISTRY
from apps.backend.services import notification_service

LEAKY_WORDS = [
    "after_hours",
    "after hours",
    "meeting",
    "burnout",
    "stress",
    "recovery",
    "pattern",
    "risk",
    "overtime",
    "typing",
]


class FakeSMTP:
    sent: list = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        pass

    def login(self, user, password):
        pass

    def send_message(self, message):
        FakeSMTP.sent.append(message)


@pytest.fixture()
def smtp(monkeypatch):
    FakeSMTP.sent = []
    settings = get_settings()
    monkeypatch.setattr(settings, "notification_channel", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_from", "workwell@example.com")
    monkeypatch.setattr(notification_service.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def test_the_email_says_something_is_waiting_and_nothing_about_what(smtp):
    assert notification_service.notify_intervention_available("emp@example.com", "emp_1") is True

    message = smtp.sent[0]
    body = message.get_payload()
    text = f"{message['Subject']} {body}".lower()

    for word in LEAKY_WORDS:
        assert word not in text, f"notification leaked '{word}' outside the authenticated app"


def test_the_email_carries_a_link_back_to_the_authenticated_dashboard(smtp):
    notification_service.notify_intervention_available("emp@example.com", "emp_1")

    body = smtp.sent[0].get_payload()
    assert get_settings().app_base_url.rstrip("/") in body


def test_the_email_goes_only_to_the_employee(smtp):
    notification_service.notify_intervention_available("emp@example.com", "emp_1")

    message = message_from_string(str(smtp.sent[0]))
    assert message["To"] == "emp@example.com"
    assert message["Cc"] is None
    assert message["Bcc"] is None


def test_a_mail_server_outage_does_not_fail_the_analysis(monkeypatch):
    """The suggestion is already durable and visible at next login, so a
    dead SMTP host must not retry - or fail - the job that produced it."""
    settings = get_settings()
    monkeypatch.setattr(settings, "notification_channel", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")

    def explode(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(notification_service.smtplib, "SMTP", explode)

    assert notification_service.notify_intervention_available("emp@example.com", "emp_1") is False


def test_smtp_selected_without_a_host_is_reported_not_silently_skipped(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "notification_channel", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "")

    assert notification_service.notify_intervention_available("emp@example.com", "emp_1") is False


def test_the_default_channel_sends_no_mail_at_all(monkeypatch):
    """A fresh install must not email staff before an admin has chosen to."""
    settings = get_settings()
    monkeypatch.setattr(settings, "notification_channel", "log")

    assert notification_service.notify_intervention_available("emp@example.com", "emp_1") is True


def test_channel_none_opts_out_entirely(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "notification_channel", "none")

    assert notification_service.notify_intervention_available("emp@example.com", "emp_1") is False


def test_delivery_outcomes_are_counted(monkeypatch):
    REGISTRY.reset()
    settings = get_settings()
    monkeypatch.setattr(settings, "notification_channel", "log")

    notification_service.notify_intervention_available("emp@example.com", "emp_1")

    counters, _, _ = REGISTRY.snapshot()
    assert counters[("workwell_notifications_total", (("channel", "log"), ("outcome", "sent")))] == 1
