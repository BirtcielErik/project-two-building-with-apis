"""Admin site registration for the shelf app."""

from django.contrib import admin

from shelf.models import Book, Note, ShelfEntry


class NoteInline(admin.TabularInline):
    """Show an entry's notes on its admin page."""

    model = Note
    extra = 0
    readonly_fields = ["created_at"]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    """Books are snapshots from Open Library; the admin is mainly for looking them up."""

    list_display = ["title", "authors", "first_publish_year", "ol_work_key"]
    search_fields = ["title", "authors", "ol_work_key"]


@admin.register(ShelfEntry)
class ShelfEntryAdmin(admin.ModelAdmin):
    """Every user's shelf entries, filterable by status."""

    list_display = ["book", "user", "status", "rating", "finished_on", "added_at"]
    list_filter = ["status"]
    search_fields = ["book__title", "user__username"]
    autocomplete_fields = ["book"]
    inlines = [NoteInline]
