"""``python manage.py seed``: create two demo users with realistic shelves.

All book data is written into this file (real Open Library work keys and
cover IDs, looked up on 2026-11-14), so seeding never calls Open Library and
works offline.

It's safe to run again: each run resets only the two demo users' shelves to
the data below. Other users and their books are never touched.
"""

import datetime
from dataclasses import dataclass, field

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import new_share_token
from shelf.models import Book, Note, ShelfEntry

# Every demo user gets this password. It's only for exploring a local copy.
DEMO_PASSWORD = "one-more-chapter"

# Open Library work key -> (title, authors, first publish year, cover ID).
BOOKS: dict[str, tuple[str, str, int, int]] = {
    "OL27482W": ("The Hobbit", "J.R.R. Tolkien", 1937, 14627509),
    "OL893414W": ("Dune", "Frank Herbert", 1965, 11481354),
    "OL66554W": ("Pride and Prejudice", "Jane Austen", 1813, 14348537),
    "OL3140822W": ("To Kill a Mockingbird", "Harper Lee", 1960, 14351077),
    "OL468431W": ("The Great Gatsby", "F. Scott Fitzgerald", 1920, 10590366),
    "OL450063W": (
        "Frankenstein; or, The Modern Prometheus",
        "Mary Shelley",
        1818,
        12356249,
    ),
    "OL1095427W": ("Jane Eyre", "Charlotte Brontë", 1847, 8235363),
    "OL59800W": ("The Left Hand of Darkness", "Ursula K. Le Guin", 1969, 10618463),
    "OL59798W": ("A Wizard of Earthsea", "Ursula K. Le Guin", 1968, 13617691),
    "OL8479867W": ("The Name of the Wind", "Patrick Rothfuss", 2007, 11480483),
    "OL17091839W": ("The Martian", "Andy Weir", 2011, 11447888),
    "OL21745884W": ("Project Hail Mary", "Andy Weir", 2021, 11200092),
    "OL27258W": ("Neuromancer", "William Gibson", 1984, 283860),
    "OL46125W": ("Foundation", "Isaac Asimov", 1951, 14612610),
    "OL64365W": ("Brave New World", "Aldous Huxley", 1932, 8231823),
    "OL103123W": ("Fahrenheit 451", "Ray Bradbury", 1953, 12993656),
    "OL40873W": ("The Road", "Cormac McCarthy", 2006, 198120),
    "OL50548W": ("Beloved", "Toni Morrison", 1987, 8261367),
    "OL102749W": ("Moby Dick", "Herman Melville", 1851, 10544254),
    "OL21177W": ("Wuthering Heights", "Emily Brontë", 1846, 12818862),
    "OL3335245W": ("The Catcher in the Rye", "J. D. Salinger", 1945, 9273490),
    "OL29983W": ("Little Women", "Louisa May Alcott", 1848, 8775559),
    "OL2163649W": ("The Hitchhiker's Guide to the Galaxy", "Douglas Adams", 1979, 12986869),
    "OL453936W": ("Good Omens", "Terry Pratchett, Neil Gaiman", 1990, 10482258),
    "OL18012166W": ("Circe", "Madeline Miller", 2018, 8739376),
    "OL16086747W": ("The Night Circus", "Erin Morgenstern", 2011, 8773134),
    "OL17202418W": ("Station Eleven", "Emily St. John Mandel", 2014, 7369961),
    "OL59038W": ("Never Let Me Go", "Kazuo Ishiguro", 2005, 1047334),
    "OL36633W": ("Rebecca", "Daphne du Maurier", 1938, 8238729),
    "OL85892W": ("Dracula", "Bram Stoker", 1897, 12216503),
}

TBR = ShelfEntry.Status.TO_BE_READ
READING = ShelfEntry.Status.READING
FINISHED = ShelfEntry.Status.FINISHED
DNF = ShelfEntry.Status.DID_NOT_FINISH


@dataclass
class DemoEntry:
    """One book on a demo shelf, with the demo user's reading details."""

    work_key: str
    status: str
    rating: int | None = None
    finished_on: datetime.date | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class DemoUser:
    """A demo account and its shelf. ``sharing`` turns on a share link."""

    username: str
    display_name: str
    sharing: bool
    shelf: list[DemoEntry]


def day(text: str) -> datetime.date:
    """Turn ``"YYYY-MM-DD"`` into a date (keeps the lists below short)."""
    return datetime.date.fromisoformat(text)


# Each shelf is listed oldest-added first.
DEMO_USERS = [
    DemoUser(
        username="demo_maya",
        display_name="Maya",
        sharing=True,
        shelf=[
            DemoEntry(
                "OL27482W",
                FINISHED,
                5,
                day("2025-12-20"),
                [
                    "Bilbo's riddle game with Gollum is still the best chapter.",
                    "Reread it for the cozy winter feeling. Holds up perfectly.",
                ],
            ),
            DemoEntry(
                "OL59798W",
                FINISHED,
                4,
                day("2026-01-18"),
                ["Ged's shadow being his own pride is beautifully done."],
            ),
            DemoEntry(
                "OL59800W",
                FINISHED,
                5,
                day("2026-02-25"),
                [
                    "The ice crossing chapters are unforgettable.",
                    "Kemmer took me a while to wrap my head around.",
                ],
            ),
            DemoEntry(
                "OL18012166W",
                FINISHED,
                5,
                day("2026-04-02"),
                ["The prose reads like a myth told by firelight."],
            ),
            DemoEntry("OL16086747W", FINISHED, 3, day("2026-05-10")),
            DemoEntry(
                "OL8479867W",
                DNF,
                2,
                day("2026-06-01"),
                ["Stopped around the University section. Maybe I'll try again someday."],
            ),
            DemoEntry(
                "OL17202418W", FINISHED, 4, day("2026-07-14"), ["“Survival is insufficient.”"]
            ),
            DemoEntry("OL450063W", DNF),
            DemoEntry("OL59038W", FINISHED, 4, day("2026-09-03")),
            DemoEntry("OL66554W", TBR),
            DemoEntry("OL1095427W", TBR),
            DemoEntry("OL893414W", READING, notes=["Keeping the glossary open in another tab."]),
            DemoEntry("OL453936W", TBR),
            DemoEntry("OL36633W", READING),
            DemoEntry("OL85892W", TBR),
            DemoEntry("OL2163649W", TBR),
            DemoEntry("OL21177W", TBR),
            DemoEntry("OL21745884W", READING, notes=["Rocky is my favorite character already."]),
        ],
    ),
    DemoUser(
        username="demo_theo",
        display_name="",
        sharing=False,
        shelf=[
            DemoEntry("OL27258W", FINISHED, 3, day("2025-11-30")),
            DemoEntry(
                "OL46125W",
                FINISHED,
                4,
                day("2026-01-12"),
                ["Big ideas, thin characters, and that's fine."],
            ),
            DemoEntry(
                "OL17091839W",
                FINISHED,
                5,
                day("2026-02-14"),
                ["Laughed out loud at the potato math."],
            ),
            DemoEntry(
                "OL893414W",
                FINISHED,
                5,
                day("2026-03-08"),
                [
                    "Third reread. Still finding new things in the politics.",
                    "Paul is much less of a hero than I remembered.",
                ],
            ),
            DemoEntry(
                "OL102749W",
                DNF,
                2,
                day("2026-04-15"),
                ["The whaling chapters lost me. Page 300 is my limit."],
            ),
            DemoEntry("OL64365W", FINISHED, 4, day("2026-05-22")),
            DemoEntry("OL103123W", FINISHED, finished_on=day("2026-06-30")),
            DemoEntry("OL3335245W", DNF, 1),
            DemoEntry(
                "OL40873W",
                FINISHED,
                4,
                day("2026-08-19"),
                ["Bleak, but the father and son carry it."],
            ),
            DemoEntry("OL468431W", TBR),
            DemoEntry("OL3140822W", TBR),
            DemoEntry("OL29983W", TBR),
            DemoEntry("OL27482W", TBR),
            DemoEntry("OL21745884W", TBR),
            DemoEntry("OL2163649W", READING),
            DemoEntry(
                "OL50548W", READING, notes=["Reading slowly. Every page asks for attention."]
            ),
        ],
    ),
]


class Command(BaseCommand):
    """Create (or reset) the demo users and their shelves."""

    help = "Create two demo users with books, ratings, finished dates, and notes."

    def handle(self, *args: object, **options: object) -> None:
        """Seed every demo user in one transaction, then print how to log in."""
        with transaction.atomic():
            books = {key: self.get_book(key) for key in BOOKS}
            for demo in DEMO_USERS:
                self.seed_user(demo, books)

        self.stdout.write(self.style.SUCCESS("Demo data is ready. Log in with:"))
        for demo in DEMO_USERS:
            sharing = "share link on" if demo.sharing else "sharing off"
            self.stdout.write(
                f"  {demo.username} / {DEMO_PASSWORD}  ({len(demo.shelf)} books, {sharing})"
            )

    def get_book(self, work_key: str) -> Book:
        """Return the ``Book`` for ``work_key``, creating it from ``BOOKS`` if it's new.

        An existing row is left as it is, because other users may share it.
        """
        title, authors, year, cover_id = BOOKS[work_key]
        book, _ = Book.objects.get_or_create(
            ol_work_key=work_key,
            defaults={
                "title": title,
                "authors": authors,
                "first_publish_year": year,
                "cover_id": cover_id,
            },
        )
        return book

    def seed_user(self, demo: DemoUser, books: dict[str, Book]) -> None:
        """Create or reset one demo user, then rebuild their shelf from scratch."""
        user, _ = get_user_model().objects.get_or_create(username=demo.username)
        user.set_password(DEMO_PASSWORD)
        user.display_name = demo.display_name
        if not demo.sharing:
            user.share_token = None
        elif not user.share_token:
            # Keep an existing link, so re-seeding doesn't break it.
            user.share_token = new_share_token()
        user.save()

        # Deleting the entries also deletes their notes (cascade).
        user.shelf_entries.all().delete()

        now = timezone.now()
        count = len(demo.shelf)
        for index, item in enumerate(demo.shelf):
            entry = ShelfEntry.objects.create(
                user=user,
                book=books[item.work_key],
                status=item.status,
                rating=item.rating,
                finished_on=item.finished_on,
            )
            # Spread the "added" dates out (oldest first, three days apart) so
            # sorting by date added looks realistic. ``update()`` is used
            # because ``auto_now_add`` would ignore a value set on save.
            added_at = now - datetime.timedelta(days=3 * (count - index))
            ShelfEntry.objects.filter(pk=entry.pk).update(added_at=added_at)
            for hours, text in enumerate(item.notes, start=1):
                note = Note.objects.create(entry=entry, text=text)
                written_at = added_at + datetime.timedelta(hours=hours)
                Note.objects.filter(pk=note.pk).update(created_at=written_at)
