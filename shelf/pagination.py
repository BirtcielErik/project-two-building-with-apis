"""Pagination helpers shared by pages that show numbered page links."""

from django.core.paginator import Paginator


def page_links(paginator: Paginator, current: int) -> list[int | None]:
    """Return the shortened list of page numbers to show as links.

    Pages far from the current one are collapsed: ``None`` marks a gap that
    templates show as "…". For page 7 of 50 this gives
    ``[1, None, 6, 7, 8, None, 50]``.
    """
    numbers = paginator.get_elided_page_range(current, on_each_side=1, on_ends=1)
    return [None if number == Paginator.ELLIPSIS else number for number in numbers]
