"""Admin site registration for accounts."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class OneMoreChapterUserAdmin(UserAdmin):
    """Admin for the custom user, showing the extra sharing fields."""

    fieldsets = (
        *UserAdmin.fieldsets,
        ("Sharing", {"fields": ("display_name", "share_token")}),
    )
