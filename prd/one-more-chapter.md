# PRD: One More Chapter

## Problem Statement

Readers who want to keep track of their reading have their information scattered. They find books in one place, remember what they've read (or meant to read) in their heads or in a notes app, lose the thoughts they had while reading, and have no easy way to show a friend what's on their shelf. Existing book sites either demand a lot of setup, mix personal notes with public reviews, or stop working when an outside service is down.

A reader needs one place where they can:
- find a book quickly,
- save it to a personal shelf with a reading status,
- rate it and keep private notes as they go,
- browse their own shelf easily as it grows, and
- share a read-only view of their shelf with friends, without exposing their private notes or their account.

Developers and scripts also need programmatic access to the same shelf, with the same privacy rules.

## Solution

One More Chapter is a Django web app with a matching REST API.

- **Search** uses the Open Library API. Users search by title, author, or keyword and save results to their shelf with one click (as To Be Read) or pick a different status from a split-button menu.
- **The bookshelf belongs to the user and is stored locally.** When a book is saved, the app stores a snapshot of its display information (title, authors, first publish year, cover ID) in its own database, so the shelf keeps working even when Open Library is unavailable.
- **Personal details** go beyond what Open Library offers: a reading status (To Be Read, Currently Reading, Finished, Did Not Finish), an optional 1–5 star rating, an optional finished date, and any number of private, timestamped notes.
- **Browsing** the shelf supports live search, filtering, sorting, and pagination, with bookmarkable URLs.
- **Sharing:** each user can create an unguessable share link, which they can regenerate or disable at any time. It gives anyone with the link a read-only, status-grouped view of their books, statuses, ratings, and finished dates. Notes and usernames are never shown.
- **API:** the app provides its own API for listing, creating, updating, and deleting shelf entries and notes, plus a public read-only endpoint for shared shelves. It uses session or token authentication and enforces the same ownership rules as the website.
- **Failures** of Open Library (timeouts, outages, rate limits, malformed data) produce clear, useful messages on the website and meaningful status codes in the API. Pages never crash because of them.

The UI uses Tailwind with DaisyUI (Forest theme) and HTMX for in-place updates.

## User Stories

### Accounts and navigation
1. As a visitor, I want a landing page that explains what One More Chapter does, so that I know whether to sign up.
2. As a visitor, I want to sign up with a username and password, so that I can start my own bookshelf.
3. As a new user, I want to be logged in automatically after signing up and taken to my shelf, so that I can start right away.
4. As a returning user, I want to log in and log out, so that my shelf stays private on shared computers.
5. As a logged-in user, I want visiting the home page to take me straight to My Shelf, so that I land where I do most of my work.
6. As a user, I want a navigation bar with Search, My Shelf, and a user menu (Profile, Log out), so that I can move around the app easily.
7. As a phone user, I want the navigation to collapse into a menu, so that the app is usable on a small screen.
8. As a visitor who is not logged in, I want to be sent to the login page when I try to open My Shelf, Search, or any book page, so that private data is protected.

### Searching Open Library
9. As a user, I want to search for books by title, author, or keyword, so that I can find something new to read.
10. As a user, I want search results to update without reloading the whole page, so that searching feels fast.
11. As a user, I want the search URL to reflect my query and page, so that I can bookmark or share a search and use the back button.
12. As a user, I want each result to show the cover, title, authors, and first publish year, so that I can recognize the right book.
13. As a user, I want a placeholder image when a book has no cover or the cover fails to load, so that the page still looks tidy.
14. As a user, I want results paginated (20 per page, up to page 50) with a shortened page list, so that large result sets are manageable.
15. As a user, I want to see the total number of matches, so that I know whether to refine my search.
16. As a user, I want a helpful message when my search finds nothing, so that I know to try different words.
17. As a user, I want submitting an empty search to show a hint instead of sending a request, so that I don't get confusing results.
18. As a user, I want a loading indicator and a disabled button while a search is running, so that I know something is happening and don't submit twice.
19. As a user, I want results for books already on my shelf to say "On your shelf" and link to that book, so that I don't save duplicates.
20. As a user, I want a one-click Save button that adds a book as To Be Read, so that saving is effortless.
21. As a user, I want a menu next to Save that lets me save a book as Currently Reading, Finished, or Did Not Finish, so that I can quickly add books I've already read.
22. As a user, I want the Save button to change to "On your shelf" in place and a confirmation toast to appear after saving, so that I know it worked without leaving the page.
23. As a user, I want a clear inline error on a result if saving fails, so that I know to try again.
24. As a user, I want a persistent message when Open Library is slow or down, explaining that my shelf still works and offering to try again, so that I'm not confused by a broken page.
25. As a user, I want repeated identical searches to return quickly, so that going back and forth through results feels snappy.
26. As a user, I want to see that book data comes from Open Library, so that the source is credited.

### Browsing My Shelf
27. As a user, I want to see my saved books as list rows showing cover, title, authors, year, status badge, star rating, finished date, date added, and number of notes, so that I can take in my shelf at a glance.
28. As a user, I want a "Currently Reading" strip at the top of my shelf, so that the books I'm in the middle of are always easy to reach.
29. As a user, I want the Currently Reading strip to hide while I'm filtering or searching, so that it doesn't get in the way of my results.
30. As a user, I want to search my shelf by title or author as I type, so that I can find a book quickly.
31. As a user, I want to filter my shelf by status from a sidebar that shows how many books are in each status, so that I can focus on one part of my reading life.
32. As a user, I want to filter my shelf by minimum star rating, so that I can find my favorites.
33. As a user, I want to filter my shelf to rated or unrated books, so that I can find books I still need to rate.
34. As a user, I want to sort my shelf by title, author, rating, date added, date updated, or finished date, in either direction, so that I can view it the way I want.
35. As a user, I want books with no rating or finished date to appear last when sorting by those fields, so that sorting stays meaningful.
36. As a user, I want my shelf paginated at 12 books per page, with the current range shown, so that large shelves stay fast and readable.
37. As a user, I want filtering, sorting, and paging to update the list without a full page reload, while keeping the URL bookmarkable, so that browsing feels smooth and I can come back to a view.
38. As a phone user, I want the shelf filters behind a Filters button, so that the list gets the screen space.
39. As a new user with an empty shelf, I want a message and a button that takes me to Search, so that I know how to get started.
40. As a user whose filters match nothing, I want a "Clear filters" button, so that I can get back to my full shelf.
41. As a user, I want my shelf to load and work normally even when Open Library is down, so that I can always see my books.

### Book detail and editing
42. As a user, I want to open a book from my shelf and see its cover, title, authors, first publish year, the date I added it, and a link to its Open Library page, so that I have its details in one place.
43. As a user, I want the book's cover and information to stay in view while I scroll through my notes on a large screen, so that the page always feels like that book's page.
44. As a user, I want to set the reading status with a row of buttons (TBR, Reading, Finished, DNF), so that changing it is one tap.
45. As a user, I want to give a book a 1–5 star rating at any status, including books I didn't finish, so that I can record my opinion.
46. As a user, I want to clear a rating, so that I can undo one I set by mistake.
47. As a user, I want to record an optional finished date at any status, so that I can remember when I read or abandoned a book.
48. As a user, I want to be stopped from entering a finished date in the future, so that my records stay accurate.
49. As a user, I want to save status, rating, and finished date together and see "Saved ✓" next to the button without a page reload, so that editing is quick and confirmed.
50. As a user, I want validation errors shown next to the field that caused them, so that I know what to fix.
51. As a user, I want to remove a book from my shelf after confirming, with a warning that its notes will be deleted too, so that I don't lose data by accident.
52. As a user, I want to return to My Shelf with a confirmation message after removing a book, so that I know it worked.
53. As a phone user, I want the detail page to stack into a single column, so that it's comfortable on a small screen.

### Notes
54. As a user, I want to add any number of notes to a book on my shelf, so that I can keep my thoughts as I read.
55. As a user, I want each note to show when I wrote it, so that I can follow my thinking over time.
56. As a user, I want notes listed newest first, so that my latest thoughts are at the top.
57. As a user, I want added notes to appear immediately without a page reload, so that note-taking flows.
58. As a user, I want to delete a note after confirming, so that I can remove mistakes.
59. As a user, I want to be stopped from adding an empty note, so that my notes list stays clean.
60. As a user, I want a friendly empty state when a book has no notes, so that I know where to start.
61. As a user, I want my notes to be completely private and never shown on my shared shelf or in the shared API, so that I can write freely.

### Sharing
62. As a user, I want to create a share link for my bookshelf from my profile, so that I can send it to friends.
63. As a user, I want the share link to be unguessable, so that only people I send it to can find my shelf.
64. As a user, I want a clear explanation of what the link shows (books, statuses, ratings, finished dates, never notes), so that I know what I'm sharing.
65. As a user, I want to copy or open my share link with one click, so that sharing is easy.
66. As a user, I want to regenerate my share link, after confirming, so that I can cut off people who have the old one.
67. As a user, I want to disable sharing entirely, after confirming, so that my shelf becomes private again.
68. As a user, I want to set an optional display name that appears on my shared shelf, so that friends know whose shelf it is without seeing my username.
69. As a visitor with a share link, I want to see the owner's display name (or "A shared bookshelf" if they haven't set one), so that I know what I'm looking at.
70. As a visitor with a share link, I want books grouped into Currently Reading, Finished (most recent first), To Be Read, and Did Not Finish, with empty groups hidden, so that I can understand the person's reading at a glance.
71. As a visitor with a share link, I want each group shown as a grid of covers with title, authors, and stars, so that the shelf is pleasant to browse.
72. As a visitor with a share link, I want each group to show 12 books with a "Show more" button that loads more in place, so that large shelves stay manageable.
73. As a visitor with a share link, I want to view the shelf without logging in, so that sharing works for anyone.
74. As a visitor, I want a plain "not found" page if a share link is invalid, regenerated, or disabled, so that old links fail cleanly.
75. As a visitor with a share link, I want no way to edit anything, so that the owner's shelf stays safe.

### Profile
76. As a user, I want a Profile page with sections for display name, share link, and API access, so that all my settings are in one place.
77. As a user, I want my API token masked by default, with Reveal and Copy buttons, so that it isn't exposed when someone sees my screen.
78. As a user, I want to regenerate my API token after a confirmation warning that the old one stops working, so that I can recover if it leaks.
79. As a user, I want profile actions to update their section in place and show a confirmation toast, so that settings feel responsive.

### API (for developers and scripts)
80. As an API client, I want to authenticate with either my browser session or a token in the request header, so that I can use the API from the browser or from scripts and tools like curl and Postman.
81. As an API client, I want to list my shelf entries with the same search, filter, sort, and pagination options as the website, so that I can query my shelf programmatically.
82. As an API client, I want to create a shelf entry by sending an Open Library work key plus optional status, rating, and finished date, so that I can save books from my own tools.
83. As an API client, I want the server to look up the book's details from Open Library itself, so that shared book data can't be faked.
84. As an API client, I want a 400 error when the work key is badly formatted, doesn't exist on Open Library, or the book is already on my shelf, so that I know exactly what went wrong.
85. As an API client, I want a 503 when Open Library is unavailable and a 502 when it returns something unexpected, so that I can tell temporary failures from bad requests.
86. As an API client, I want to retrieve one entry with its book information nested (including a ready-made cover URL), so that I don't need to know Open Library's URL scheme.
87. As an API client, I want to update an entry's status, rating, and finished date with full or partial updates, so that I can sync changes.
88. As an API client, I want a 400 error if I try to change which book an entry points to, so that I'm not silently ignored.
89. As an API client, I want to delete an entry (and its notes), so that I can remove books programmatically.
90. As an API client, I want to list, add, and delete notes on my own entries, so that I can manage my notes programmatically.
91. As an API client, I want a 405 if I try to edit a note, so that it's clear notes are add and delete only.
92. As an API client, I want requests for other users' entries or notes to return 404, so that I can't even discover that they exist.
93. As an API client, I want a public, read-only, paginated endpoint for a shared shelf by its token, without notes or user identifiers, so that I can build on shared shelves.
94. As an API client, I want any non-read request to the shared endpoint to be rejected, so that shared shelves are guaranteed read-only.
95. As an API client, I want to be told when I'm sending too many requests (429 with a retry time), so that I can slow down.

### Reliability and operations
96. As the app owner, I want the app to identify itself to Open Library with its name and a contact email from configuration, so that we get the higher rate limit and follow their rules.
97. As the app owner, I want API request rates limited per user, with stricter limits on creating entries and on the shared endpoint, so that scripts can't use our app to flood Open Library.
98. As the app owner, I want secrets and environment settings kept out of the repository, with a documented example file, so that credentials aren't leaked and others can set the project up.
99. As a developer, I want the test suite to run without a configuration file or an internet connection, so that tests are fast and reliable.

## Implementation Decisions

### Project structure and tooling
- Stack: Python, Django, Django REST Framework, SQLite, uv, Ruff, Pytest, Tailwind CSS with DaisyUI (Forest theme), and HTMX.
- The project package is named `config`. The Python project is renamed from `book-tracker` to `one-more-chapter`.
- Two Django apps:
  - **accounts**: the custom user model, signup/login/logout, and the Profile page (display name, share link controls, API token controls).
  - **shelf**: the book, shelf entry, and note models; the Open Library service module; the shared filter set; website views (search, shelf, detail, shared shelf); and the DRF API (serializers, viewsets, and API URL routes).
- Tailwind and DaisyUI are built with `django-tailwind-cli`, without Node.js. Its DaisyUI setting downloads `tailwind-cli-extra`, a build of the Tailwind CLI with DaisyUI 5 included.
- The Forest theme needs a project-owned CSS input file (the `TAILWIND_CLI_SRC_CSS` setting) that enables the DaisyUI plugin with Forest as the default theme. The library's auto-generated input file enables DaisyUI with only its default light and dark themes.
- HTMX is vendored into the project's static files at a pinned version, with no CDN at runtime.
- Configuration comes from environment variables (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `OPENLIBRARY_CONTACT_EMAIL`). Locally they're loaded from a git-ignored `.env` file through uv's `--env-file` option, and a committed `.env.example` documents them. Safe defaults keep debug off unless explicitly enabled and use a clearly labeled insecure development key only in debug mode. Tests must run without a `.env`.

### Data model
- **User**: a custom user model extending Django's `AbstractUser`, created before the first migration. Extra fields:
  - `share_token`: nullable and unique, generated with a cryptographically secure URL-safe token.
  - `display_name`: optional, blank by default.
  - There is no separate Profile model.
- **Book**: one row per Open Library *work*, shared across all users.
  - `ol_work_key` is unique and stored without the `/works/` prefix (for example `OL27482W`).
  - Also stores title, authors, first publish year (nullable), and cover ID (nullable).
  - Users never edit Book rows directly. Book rows are kept even when no shelf references them, so they act as a local cache.
  - There is no description or genre field.
- **ShelfEntry**: links a user to a book. Unique on (user, book). Fields:
  - `status`: text choices To Be Read / Currently Reading / Finished / Did Not Finish, default To Be Read.
  - `rating`: nullable small integer, validated 1–5, allowed at any status.
  - `finished_on`: nullable date, user-editable, must not be in the future, allowed at any status.
  - `added_at` and `updated_at`: automatic timestamps.
- **Note**: belongs to a shelf entry. Has text and a created timestamp.
  - Deleted when its entry is deleted (cascade).
  - Add and delete only; there is no editing.
  - Always private to the owner.

### Open Library integration
- All outbound calls go through a single Open Library service module. Views and viewsets call its functions through the module rather than importing the functions directly, so tests can replace them.
- Every request uses about a 5-second timeout and sends a User-Agent with the app name, version, and the configured contact email. Without the email, it falls back to an identifying User-Agent with no email.
- Search uses the search endpoint with a restricted `fields` list (key, title, author names, first publish year, cover ID) and 20 results per page. Result browsing is capped at page 50 (1,000 results). Requests beyond that make no outbound call and show "Try a more specific search."
- Saving a new book looks it up through the search endpoint with a `key:/works/<key>` query, which returns everything needed in one request. The lookup must add the `/works/` prefix back (the query matches nothing without it).
- Open Library returns HTTP 200 with zero matches for unknown keys. The service must treat that as "not found" rather than reading the first result.
- Work keys are validated against the format `OL<digits>W` before any outbound call, to block query injection and wasted requests.
- Error handling is done with custom exceptions:
  - **Open Library unavailable**: timeouts, connection errors, 5xx responses, and 429 responses. The website shows a friendly inline message; the API returns 503.
  - **Open Library bad response**: invalid JSON or an unexpected structure. The website shows a friendly inline message; the API returns 502.
  - **Not found**: shown as a field validation error; the API returns 400.
- There are no automatic retries.
- Search results are cached in Django's in-memory cache for about 10 minutes, keyed on the normalized query and page. Failures are never cached. The save lookup is not cached because the Book table already plays that role.
- Covers are displayed from Open Library's covers service by cover ID, in small, medium, and large sizes. The API exposes a computed cover URL (null when there is no cover ID).

### Saving flow (website and API)
- The client sends only the work key plus optional status, rating, and finished date. The server:
  1. validates the key format;
  2. rejects duplicates for that user with a 400 before any outbound call;
  3. reuses an existing Book or creates one from a single Open Library lookup;
  4. creates the ShelfEntry.
- An existing Book can be saved even during an Open Library outage. Only brand-new books need the external call.

### Browsing (shared by website and API)
- A single `django-filter` FilterSet for shelf entries is used by both the website shelf view and the API list endpoint:
  - **Search**: case-insensitive contains on title and authors.
  - **Filters**: status, minimum rating, and rated or not rated.
  - **Ordering**: a whitelist of title, author, rating, date added, date updated, and finished date, ascending or descending. Nulls sort last.
  - **Pagination**: 12 per page.

### Website views and HTMX behavior
- Views return a partial template for HTMX requests and a full page otherwise, so every page also works without JavaScript.
- **Landing (logged out)**: a hero with the tagline, Sign up and Log in buttons, and three feature cards. Logged-in users at the root URL are redirected to My Shelf.
- **Auth pages**: centered DaisyUI cards with inline field errors and cross-links. Signup uses Django's user creation form and logs the user in, then redirects to My Shelf.
- **Search page**: logged-in only. Submitting the form swaps only the results area and pushes the URL (no search-as-you-type). Results use the same list-row component as My Shelf.
  - Each row ends with a split button: Save (as To Be Read) plus a menu for the other statuses.
  - Books already on the user's shelf show "✓ On your shelf", linking to the detail page. This is determined with one database query per results page.
  - States covered: before searching, loading, results, no matches, Open Library unavailable (a persistent alert with Try again and a link to My Shelf), empty submit, past the page cap, saved, and save failed (inline error on the row).
  - A "Book data from Open Library" credit link appears in the Search page footer.
- **My Shelf**: a left sidebar with status filters (with counts), minimum rating, rated or not rated, and Clear all filters.
  - The main column has a debounced live search box and a sort dropdown, above the list rows (cover, title, authors, year, status badge, stars, finished date, added date, notes count) and pagination.
  - A Currently Reading strip sits above the search and sort bar and is hidden while any filter or search is active.
  - On phones the sidebar sits behind a Filters button.
  - Every change swaps the results via HTMX and pushes a bookmarkable URL.
  - Empty states: an empty shelf links to Search; no matches offers Clear filters.
- **Book detail**: two columns.
  - Left (sticky on desktop): large cover, title, authors, first publish year, "on your shelf since" date, Open Library link, and Remove from shelf.
  - Right: a "Your reading" card containing a single form with a status button group, a clickable 5-star rating with Clear, and a finished date input capped at today. Saving via HTMX shows an inline "Saved ✓".
  - Below the card, the notes section: an add-note box at the top, notes newest first with timestamps, and a delete button per note that asks for confirmation. Additions and deletions update in place.
  - Remove from shelf opens a confirmation dialog that states how many notes will be deleted, then redirects to My Shelf with a toast.
  - Stacks to one column on phones.
- **Shared shelf page**: public and read-only.
  - Headed by the display name, or "A shared bookshelf" when there is none.
  - Books are grouped as Currently Reading, Finished (most recently finished first), To Be Read, and Did Not Finish. Empty groups are hidden.
  - Each group is a cover grid with title, authors, and stars, showing 12 books with an HTMX "Show more" that appends the next 12.
  - Never shows notes, usernames, or user IDs. Invalid, regenerated, or disabled tokens return 404.
- **Profile page**: three stacked cards.
  1. **Display name**: an editable form.
  2. **Share your bookshelf**: changes with state. With no link, it shows the explanation and a Create button. With a link, it shows a read-only URL with Copy and Open, plus Regenerate and Disable (both confirmed). Each action is an HTMX POST that swaps the card and shows a toast.
  3. **API access**: the token masked except its last characters, with Reveal, Copy, and a confirmed Regenerate.
- **Feedback convention**:
  - Successes appear as auto-dismissing toasts. Django messages are delivered to HTMX responses through an out-of-band swap into a toast container.
  - Errors and validation messages appear inline and stay until resolved.
  - The detail form's "Saved ✓" stays inline.
  - HTMX requests show spinners and disable their triggering buttons while in flight.
- **Navigation**: a DaisyUI navbar with the logo, Search, My Shelf, and a user dropdown (Profile, Log out), collapsing to a menu on phones. A themed 404 page is used for missing or unauthorized objects.

### API
- **Authentication**: DRF Session and Token authentication. Users get tokens through the Profile page.
- **Endpoints**:
  - Entries: list and create; retrieve, full update, partial update, and delete.
  - Notes nested under an entry: list, create, and delete. There is no update; edit attempts return 405.
  - A public shared-shelf endpoint addressed by share token: GET only, paginated, as a flat list.
- **Scoping**: all owner endpoints are scoped to the requesting user. Other users' entries or notes return 404, never 403. Creating a note on an entry the user doesn't own returns 404.
- **Serializers**:
  - The owner entry serializer nests read-only book information (work key, title, authors, first publish year, cover URL).
  - The work key is accepted on create only. Sending it on update returns a strict 400.
  - A separate public serializer for shared shelves includes only book information, status, rating, and finished date. It has no notes, user ID, or username.
- **Error mapping**:
  - 400: invalid, unknown, or duplicate work keys, and invalid fields.
  - 503: Open Library unavailable.
  - 502: bad response from Open Library.
- **Throttling**: DRF user throttling at about 60 requests per minute, with stricter scoped limits (about 10 per minute) on entry creation and on the shared endpoint. Exceeding a limit returns 429 with a Retry-After header. Throttling uses the in-memory cache.

### Testing approach
- Pytest with pytest-django.
- The Open Library service module is tested at the HTTP level with the `responses` library, covering:
  - parsing,
  - the `/works/` prefix,
  - zero-match "not found",
  - timeouts, connection errors, 5xx and 429 responses,
  - malformed JSON,
  - caching behavior (an identical second search makes no HTTP call; failures aren't cached).
- View and API tests replace the service functions using pytest's `monkeypatch`, so they focus on permissions, messages, and status codes.
- A global fixture fails any test that tries to make a real network call.
- A fixture clears the cache between tests (covering both the search cache and throttle counters).
- Key behaviors to cover:
  - ownership and 404 rules on the website and the API;
  - the shared-shelf privacy rules (no notes key, no user identifiers, GET only, 404 after regenerate or disable);
  - duplicate and invalid-key handling before outbound calls;
  - rating and finished-date validation identical in forms and serializers;
  - filter, sort, and pagination parity between the website and the API;
  - notes add/delete and the 405 on edit;
  - throttling returning 429.

## Out of Scope

- Genre or subject classification and filtering. Open Library's subjects are too inconsistent, and genre was explicitly dropped.
- Fetching or storing book descriptions or other extended details from Open Library.
- Edition-level tracking (specific editions, ISBNs, page counts, publishers). Books are tracked at the work level only.
- A `started_on` date, automatic date-setting on status changes, and reading-progress tracking (pages or percent).
- Editing notes. Notes are add and delete only.
- Quick-edit controls on My Shelf rows. All editing happens on the detail page.
- Search-as-you-type on the Open Library search page. Live search applies only to the user's own shelf.
- Anonymous (logged-out) searching of Open Library.
- A dashboard or statistics page.
- A grid/list view toggle on My Shelf.
- Search, filter, or sort controls for visitors on shared shelves (pagination / "Show more" only).
- Multiple share links per user, expiring links, or per-link permissions.
- JWT, OAuth, social login, email verification, and password-reset emails.
- Automatic retries of failed Open Library requests.
- Throttling of website (non-API) requests.
- Persistent or shared caches (Redis, database cache).
- Re-syncing stored book snapshots with later changes on Open Library.

## Further Notes

- **Provider research.** The research document in the repo's docs folder covers Open Library and the alternatives. Key facts:
  - Open Library allows about 1 request per second anonymously, or 3 per second with an identifying User-Agent.
  - It asks clients to cache and to credit covers with a courtesy link.
  - Cover lookups by cover ID are not rate limited, but ISBN lookups are.
- **Verified live on 2026-11-12:**
  - `search.json?q=key:/works/<key>` with restricted fields returns exactly one document for valid keys (tested on The Hobbit, Dune, and an obscure 1977 title).
  - The same query returns zero documents (HTTP 200) for an unprefixed key or a nonexistent key.
  - The search `subject` field is an unstructured, multilingual list, which is why genre was dropped.
- **UI prototypes** that document the chosen layouts live in the repo's prototypes folder:
  - My Shelf: the sidebar-and-list variant plus the Currently Reading strip.
  - Book detail: the two-column variant.
  - Both use real Open Library data and the DaisyUI Forest theme.
- **Confirmed 2026-11-12:**
  - `django-tailwind-cli` 4.8.2 supports DaisyUI through `tailwind-cli-extra` (latest v2.10.35, which bundles Tailwind 4.3.4 and DaisyUI 5.7.50 and has a Windows x64 build).
  - The repo's `.gitignore` already ignores `.env`. `.env.example` stays committable because the rule matches only the exact name.
  - Search page settings: 20 results per page, a cap at page 50, and an Open Library credit in the Search page footer.
- **The search-endpoint lookup depends on the search API, which Open Library says is "not guaranteed to be stable".** Keeping all Open Library parsing in one service module with HTTP-level tests limits the impact if the response shape changes.
