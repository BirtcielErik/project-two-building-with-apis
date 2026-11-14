"""Forms for user accounts."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from accounts.models import User


class DaisyFormMixin(forms.BaseForm):
    """Give every text input DaisyUI's ``input`` styling, and mark fields with errors.

    After validation, any field that has an error also gets ``input-error``
    (a red border), so the problem field stands out next to its message.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Build the form, then add the DaisyUI classes to each field's widget."""
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def full_clean(self) -> None:
        """Validate the form, then highlight each field that failed."""
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs["class"] += " input-error"


class SignupForm(DaisyFormMixin, UserCreationForm):
    """Django's built-in signup form (username + password twice), for our custom User.

    The built-in form points at Django's default user model, so we subclass it
    and tell it to create ``accounts.User`` instead.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


class LoginForm(DaisyFormMixin, AuthenticationForm):
    """Django's built-in login form, styled with DaisyUI."""
