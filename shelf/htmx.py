"""Helpers for views that serve both HTMX requests and normal page loads.

HTMX sends an ``HX-Request: true`` header with every request it makes. For
those, a view returns only the piece of the page that changes (a "partial").
Every other request gets the full page, so each URL also works without
JavaScript and can be bookmarked or reloaded.
"""

from collections.abc import Mapping

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.cache import patch_vary_headers


def is_htmx(request: HttpRequest) -> bool:
    """Return whether this request should get a partial instead of a full page.

    When the user presses Back and HTMX doesn't have the old page saved, it
    re-requests the URL with ``HX-History-Restore-Request`` and needs the full
    page, so those requests count as normal page loads.
    """
    return (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-History-Restore-Request") != "true"
    )


def render_page_or_partial(
    request: HttpRequest,
    full_template: str,
    partial_template: str,
    context: Mapping[str, object],
) -> HttpResponse:
    """Render ``partial_template`` for HTMX requests and ``full_template`` otherwise.

    The response says it ``Vary``s on ``HX-Request`` so the browser never
    reuses a cached partial when it needs the full page (or the reverse).
    """
    template = partial_template if is_htmx(request) else full_template
    response = render(request, template, context)
    patch_vary_headers(response, ["HX-Request"])
    return response
