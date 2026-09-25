"""Tells an employee a suggestion is waiting - without saying what it is.

An intervention that only exists in a database row is not an intervention:
the product's premise is that it reaches someone *early*, and an employee
who does not happen to open the dashboard that week is exactly the person
it was built for.

The privacy rule here is stricter than elsewhere in the system, and
deliberately so. Work email is not a private channel: it is archived,
scanned by DLP, synced to phones that sit unlocked on desks, and in most
jurisdictions readable by the employer by default. So the notification
carries no pattern, no signal, no risk state and no wellness text - only
the fact that something is waiting behind the employee's own login. The
content stays on the authenticated dashboard where only they can read it.

Channels are pluggable because deployments differ; `log` is the default so
a fresh install never silently emails staff before an admin has chosen to.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from apps.backend.core.config import get_settings
from apps.backend.core.observability import REGISTRY

logger = logging.getLogger("workwell.notifications")

SUBJECT = "WorkWell: a new suggestion is waiting for you"

BODY = """Hello,

You have a new suggestion waiting for you in WorkWell.

    {url}

Only you can see it. This message deliberately says nothing about why -
naming it here would disclose it to anyone with access to your mailbox.
Your manager receives nothing about you individually either.

To stop receiving these, turn notifications off in your Privacy Center.
"""


def _record(channel: str, outcome: str) -> None:
    REGISTRY.increment(
        "workwell_notifications_total", {"channel": channel, "outcome": outcome}
    )


def notify_intervention_available(recipient_email: str, employee_id: str) -> bool:
    """Returns True when the notification was handed to a transport.

    Never raises: a mail server being down must not fail - or retry - the
    analysis that produced the suggestion. The suggestion is already
    durable in the database and visible at next login.
    """
    settings = get_settings()
    channel = (settings.notification_channel or "log").lower()
    url = settings.app_base_url.rstrip("/") + "/"

    try:
        if channel == "none":
            _record(channel, "skipped")
            return False
        if channel == "log":
            # Deliberately logs the employee id, not the address: operational
            # logs are a weaker privacy boundary than the mail transport.
            logger.info("intervention notification ready for %s", employee_id)
            _record(channel, "sent")
            return True
        if channel == "smtp":
            _send_smtp(settings, recipient_email, url)
            _record(channel, "sent")
            return True
        if channel == "webhook":
            _send_webhook(settings, recipient_email, url)
            _record(channel, "sent")
            return True

        logger.error("unknown notification channel: %s", channel)
        _record(channel, "misconfigured")
        return False
    except Exception as exc:
        logger.warning("notification failed over %s: %s", channel, type(exc).__name__)
        _record(channel, "failed")
        return False


def _send_smtp(settings, recipient_email: str, url: str) -> None:
    if not settings.smtp_host:
        raise RuntimeError("NOTIFICATION_CHANNEL=smtp but SMTP_HOST is unset")

    message = EmailMessage()
    message["Subject"] = SUBJECT
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = recipient_email
    message.set_content(BODY.format(url=url))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_starttls:
            server.starttls(context=ssl.create_default_context())
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)


def _send_webhook(settings, recipient_email: str, url: str) -> None:
    import httpx

    if not settings.notification_webhook_url:
        raise RuntimeError("NOTIFICATION_CHANNEL=webhook but NOTIFICATION_WEBHOOK_URL is unset")

    # Same rule as email: the receiving system (Slack, Teams, an internal
    # relay) is not a confidential channel either, so it gets the address
    # and a link and nothing else.
    response = httpx.post(
        settings.notification_webhook_url,
        json={"email": recipient_email, "subject": SUBJECT, "url": url},
        timeout=10.0,
    )
    response.raise_for_status()
