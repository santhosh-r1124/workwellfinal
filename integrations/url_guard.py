"""Fetching a URL somebody else chose.

The ICS connector's whole point is that an employee pastes their own
private calendar link. That makes it a server-side request to an address
the server does not control, which is the shape of SSRF: `http://169.254.169.254/`
reaches cloud instance metadata, `http://localhost:6379/` reaches Redis,
and anything on the private network is one hostname away.

The parser only keeps DTSTART/DTEND, so a successful attack exfiltrates
very little. "Very little" is not the standard for a product whose
argument is that it is careful with data, and a blind request into the
private network is useful on its own.

So: https by default, every resolved address checked against the private
ranges before connecting, redirects re-checked rather than trusted, and a
size cap so a hostile endpoint cannot stream until the worker dies.

This is not a complete SSRF defence - nothing that resolves DNS in the
application can fully close the TOCTOU window between the check and the
connect. Behind that, an egress allowlist at the network layer is the
real control, and docs/deployment.md says so.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.request
from urllib.parse import urlparse

MAX_BYTES = 5 * 1024 * 1024
TIMEOUT_SECONDS = 15
MAX_REDIRECTS = 3


class UnsafeUrl(ValueError):
    """The URL points somewhere the server must not be made to reach."""


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def assert_safe(url: str, allow_http: bool = False) -> None:
    parsed = urlparse(url)

    if parsed.scheme not in ("https", "http"):
        raise UnsafeUrl("Only https URLs are supported.")
    if parsed.scheme == "http" and not allow_http:
        raise UnsafeUrl("Only https URLs are accepted - an http calendar link is sent in clear.")
    if not parsed.hostname:
        raise UnsafeUrl("That URL has no host.")

    try:
        resolved = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise UnsafeUrl("That host could not be resolved.") from exc

    # Every address, not just the first: a host that resolves to one public
    # and one private address is the standard way round a naive check.
    for entry in resolved:
        address = entry[4][0]
        if not _is_public(address):
            raise UnsafeUrl(
                "That URL resolves to a private or local address, which this server will not fetch."
            )


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """Redirects are followed by hand so each hop is re-validated. An
    endpoint that passes the check and then 302s to 169.254.169.254 is the
    other standard way round it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise _Redirect(newurl)


class _Redirect(Exception):
    def __init__(self, url: str) -> None:
        super().__init__(url)
        self.url = url


def fetch_text(url: str, allow_http: bool = False) -> str:
    opener = urllib.request.build_opener(_NoRedirects)
    current = url

    for _ in range(MAX_REDIRECTS + 1):
        assert_safe(current, allow_http=allow_http)
        try:
            with opener.open(current, timeout=TIMEOUT_SECONDS) as response:
                # read(n+1) so an oversized body is detected rather than
                # silently truncated into a half-parsed calendar.
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise UnsafeUrl("That calendar is larger than this server will download.")
                return body.decode("utf-8", errors="replace")
        except _Redirect as redirect:
            current = redirect.url

    raise UnsafeUrl("That URL redirected too many times.")
