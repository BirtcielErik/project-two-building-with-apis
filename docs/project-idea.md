This is a new Django application named One More Chapter. The purpose of this app is for users to search for new books to read, keep track of the books they are currently reading or have read in the past, store notes or ideas about the books that they have read, and share their current reading list with friends.

The application has the following requirements:

1) Users searching for books are served via the Open Library API
2) Users can save books to their "bookshelf" - a user's bookshelf should remain available to them even if the Open Library API is unavailable
3) Users can add new details to books that are not offered by the API, such as notes, a star rating, and reading status (To Be Read, Currently Reading, Finished, Did Not Finish)
4) Users can fully browse their bookshelf - utilizing search, filtering, sorting, and pagination
5) A user must be signed in to view their bookshelf. A user can only ever edit their own bookshelf - never another user's. A user can request a link to their bookshelf which they can send to other people in order to share a read-only version of their current bookshelf - these rules must be enforced by both the website and the API
6) One More Chapter must provide its own API - which must support listing, creating, updating, and deleting saved entries
7) One More Chapter must be able to handle unsuccessful external requests and return a useful message when the provider is unavailable or a request fails

The application must use the following tech stack:

- Django
- Django REST Framework (DRF)
- SQLite
- uv
- Ruff
- Python
- Tailwind with DaisyUI (Forest theme)
- HTMX
- Pytest