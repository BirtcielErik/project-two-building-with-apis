"""Template filters for the shelf app. Load them with ``{% load shelf_extras %}``."""

from django import template

from shelf import openlibrary

register = template.Library()


@register.filter
def cover_url(cover_id: int | None, size: str = "M") -> str:
    """Return the Open Library cover URL for a cover ID, or ``""`` when there is none.

    Usage: ``{{ book.cover_id|cover_url:"M" }}`` (sizes ``S``, ``M``, ``L``).
    """
    return openlibrary.cover_url(cover_id, size) or ""
