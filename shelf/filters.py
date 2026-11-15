"""The shelf FilterSet: search, filters, and sorting for a user's shelf entries.

The website's My Shelf page and the API list endpoint both use this one
FilterSet, so the same URL parameters give the same results in both places.
"""

from collections.abc import Sequence

import django_filters
from django.db.models import Count, F, OrderBy, Q, QuerySet

from shelf.models import ShelfEntry

# How many entries one page of the shelf shows (website and API).
PAGE_SIZE = 12

# Choices for the website's controls, as (URL value, label). "" means "no filter".
MIN_RATING_CHOICES = [
    ("", "Any rating"),
    ("5", "★★★★★ only"),
    ("4", "4★ and up"),
    ("3", "3★ and up"),
    ("2", "2★ and up"),
    ("1", "1★ and up"),
]
RATED_CHOICES = [("", "Rated or not"), ("yes", "Rated"), ("no", "Not rated")]
# "" is the default sort (most recently added first; see ShelfEntry.Meta.ordering).
ORDERING_CHOICES = [
    ("", "Recently added"),
    ("added", "Oldest added"),
    ("title", "Title A→Z"),
    ("-title", "Title Z→A"),
    ("author", "Author A→Z"),
    ("-author", "Author Z→A"),
    ("-rating", "Highest rated"),
    ("rating", "Lowest rated"),
    ("-finished", "Recently finished"),
    ("finished", "Earliest finished"),
    ("-updated", "Recently updated"),
    ("updated", "Least recently updated"),
]

# Always added after the chosen sort: newest additions first, then ID, so the
# order (and pagination) is the same every time.
TIEBREAK_ORDERING = ("-added_at", "-pk")


class NullsLastOrderingFilter(django_filters.OrderingFilter):
    """An ``OrderingFilter`` that always puts empty (NULL) values at the end.

    Databases normally treat NULL as the smallest value, so an unrated book
    would come first when sorting by rating from low to high. Adding
    ``nulls_last=True`` keeps books with no rating or finished date at the
    end in both directions.
    """

    def filter(self, qs: QuerySet, value: Sequence[str] | None) -> QuerySet:
        """Sort ``qs`` by the chosen ordering (``value``), with NULLs last.

        With no (valid) choice, the newest additions come first. Ties (two
        books both rated 4) are broken by newest addition, then by ID, so a
        book never appears on two pages or goes missing between them.
        """
        # get_ordering_value() (built in) turns a URL name such as "-finished"
        # into its model field, "-finished_on".
        chosen = [self._nulls_last(self.get_ordering_value(param)) for param in value or []]
        return qs.order_by(*chosen, *TIEBREAK_ORDERING)

    @staticmethod
    def _nulls_last(name: str) -> OrderBy:
        """Turn ``"field"`` or ``"-field"`` into an ordering that puts NULLs last."""
        if name.startswith("-"):
            return F(name[1:]).desc(nulls_last=True)
        return F(name).asc(nulls_last=True)


class ShelfEntryFilter(django_filters.FilterSet):
    """Filter and sort shelf entries from URL parameters.

    Every parameter is optional and they combine: ``?q=dune&status=finished``
    means "matches 'dune' AND is Finished". Invalid values are ignored by the
    website and rejected with a 400 by the API.
    """

    q = django_filters.CharFilter(method="search", label="Search title or author")
    status = django_filters.ChoiceFilter(choices=ShelfEntry.Status.choices)
    min_rating = django_filters.NumberFilter(
        field_name="rating", lookup_expr="gte", min_value=1, max_value=5
    )
    rated = django_filters.ChoiceFilter(
        choices=[("yes", "Rated"), ("no", "Not rated")], method="filter_rated"
    )
    ordering = NullsLastOrderingFilter(
        fields=(
            ("book__title", "title"),
            ("book__authors", "author"),
            ("rating", "rating"),
            ("added_at", "added"),
            ("updated_at", "updated"),
            ("finished_on", "finished"),
        ),
    )

    class Meta:
        model = ShelfEntry
        fields: list[str] = []

    def search(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Keep entries whose title or authors contain ``value`` (ignoring case)."""
        return queryset.filter(Q(book__title__icontains=value) | Q(book__authors__icontains=value))

    def filter_rated(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Keep only rated entries (``"yes"``) or only unrated ones (``"no"``)."""
        return queryset.filter(rating__isnull=(value == "no"))


def status_counts(entries: QuerySet) -> dict[str, int]:
    """Count ``entries`` per status in one query, e.g. ``{"tbr": 3, "finished": 2}``.

    Statuses with no entries are left out, so use ``.get(status, 0)``.
    """
    rows = entries.order_by().values_list("status").annotate(total=Count("pk"))
    return dict(rows)
