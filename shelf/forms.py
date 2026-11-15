"""Forms for the shelf app."""

from django import forms
from django.utils import timezone

from shelf.models import Note, ShelfEntry

# The rating choices: "" means "no rating", then 1 to 5 stars.
RATING_CHOICES = [
    ("", "No rating"),
    *[(str(n), f"{n} star{'s' if n > 1 else ''}") for n in range(1, 6)],
]

# Short names that fit on the detail page's row of status buttons.
STATUS_SHORT_LABELS = {
    ShelfEntry.Status.TO_BE_READ: "TBR",
    ShelfEntry.Status.READING: "Reading",
    ShelfEntry.Status.FINISHED: "Finished",
    ShelfEntry.Status.DID_NOT_FINISH: "DNF",
}


class ShelfEntryForm(forms.ModelForm):
    """Edit the user's reading details for one book: status, rating, and finished date.

    The rules live on the ``ShelfEntry`` model (rating 1–5, finished date not
    in the future), and a ModelForm checks the model's rules when it
    validates, so the website and the API apply exactly the same ones.
    Rating and finished date are optional and allowed at any status.
    """

    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        empty_value=None,
        required=False,
    )

    class Meta:
        model = ShelfEntry
        fields = ["status", "rating", "finished_on"]
        widgets = {"finished_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Build the form and cap the date picker at today, so future days can't be picked."""
        super().__init__(*args, **kwargs)
        self.fields["finished_on"].widget.attrs.update(
            {"max": timezone.localdate().isoformat(), "class": "input input-sm w-48"}
        )

    def full_clean(self) -> None:
        """Validate the form, then give the date input a red border if it has an error."""
        super().full_clean()
        if "finished_on" in self.errors:
            self.fields["finished_on"].widget.attrs["class"] += " input-error"

    def status_choices(self) -> list[dict[str, object]]:
        """Return each status as a dict for the button group: value, label, short label, checked.

        The current choice is whatever the user just posted, or the saved status.
        """
        current = str(self["status"].value())
        return [
            {
                "value": value,
                "label": label,
                "short": STATUS_SHORT_LABELS[value],
                "checked": value == current,
            }
            for value, label in ShelfEntry.Status.choices
        ]

    def rating_value(self) -> str:
        """Return the chosen rating as text (``"1"``–``"5"``), or ``""`` for no rating."""
        value = self["rating"].value()
        return "" if value is None else str(value)


class NoteForm(forms.ModelForm):
    """Add a note to a book on the user's shelf.

    Django strips spaces and blank lines from the start and end of the text,
    so a note of only whitespace counts as empty and is rejected.
    """

    class Meta:
        model = Note
        fields = ["text"]
        labels = {"text": "New note"}
        error_messages = {"text": {"required": "Write something before adding a note."}}
        widgets = {
            "text": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "A thought, a quote, a question…",
                    "class": "textarea w-full",
                }
            )
        }

    def full_clean(self) -> None:
        """Validate the form, then give the text box a red border if it has an error."""
        super().full_clean()
        if "text" in self.errors:
            self.fields["text"].widget.attrs["class"] += " textarea-error"
