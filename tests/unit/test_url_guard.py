"""The ICS connector fetches a URL the employee chose, server-side.

That is the shape of SSRF. `allow_http=True` is used throughout so these
exercise the address check rather than the scheme check - otherwise every
case would pass for the wrong reason.
"""

import pytest

from integrations.url_guard import UnsafeUrl, assert_safe


@pytest.mark.parametrize(
    "url,why",
    [
        ("http://169.254.169.254/latest/meta-data/", "cloud instance metadata"),
        ("http://127.0.0.1:6379/", "loopback - Redis lives here"),
        ("http://localhost:8000/admin/settings", "loopback by name"),
        ("http://10.0.0.5/internal", "private range"),
        ("http://192.168.1.1/", "private range"),
        ("http://172.16.0.1/", "private range"),
        ("http://[::1]/", "loopback over IPv6"),
        ("http://0.0.0.0/", "unspecified"),
    ],
)
def test_the_server_refuses_to_be_pointed_at_its_own_network(url, why):
    with pytest.raises(UnsafeUrl):
        assert_safe(url, allow_http=True)


def test_a_normal_calendar_url_is_allowed():
    assert_safe("https://calendar.google.com/calendar/ical/x/private-abc/basic.ics") is None


def test_only_http_and_https_are_considered_at_all():
    for url in ("file:///etc/passwd", "ftp://example.com/x", "gopher://example.com/"):
        with pytest.raises(UnsafeUrl):
            assert_safe(url, allow_http=True)


def test_plain_http_is_refused_by_default():
    """A calendar subscribe URL is a bearer credential; sending it in
    clear hands it to anything on the path."""
    with pytest.raises(UnsafeUrl, match="https"):
        assert_safe("http://calendar.example.com/cal.ics")


def test_a_host_that_does_not_resolve_is_refused_rather_than_attempted():
    with pytest.raises(UnsafeUrl):
        assert_safe("https://this-host-does-not-exist.invalid/cal.ics")


def test_a_url_without_a_host_is_refused():
    with pytest.raises(UnsafeUrl):
        assert_safe("https:///cal.ics", allow_http=True)
