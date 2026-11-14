# Plan: One More Chapter

> Source PRD: `prd/one-more-chapter.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Stack**: Python, Django, Django REST Framework, django-filter, SQLite, uv, Ruff, Pytest (pytest-django, `responses`), Tailwind + DaisyUI (Forest theme) built with `django-tailwind-cli` / `tailwind-cli-extra` (no Node.js), and HTMX vendored into static files at a pinned version.
- **Project**: Django project package `config`. The Python project is renamed from `book-tracker` to `one-more-chapter`.
- **Owning apps**:
  - `accounts`: custom `User`, signup/login/logout, Profile page (display name, share link controls, API token controls).
  - `shelf`: `Book`, `ShelfEntry`, `Note`, the Open Library service module, the shared FilterSet, website views (search, shelf, detail, shared shelf), and the DRF API.
- **Configuration**: environment variables `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `OPENLIBRARY_CONTACT_EMAIL`. These are loaded from a git-ignored `.env` via `uv run --env-file .env`, and a committed `.env.example` documents them. Debug is off by default, a labeled insecure key is used only in debug mode, and tests run without `.env`.
- **Website URLs** (app-namespaced, entries addressed by integer pk):
  - `/`: landing page (logged-in users are redirected to `/shelf/`)
  - `/accounts/signup/`, `/accounts/login/`, `/accounts/logout/` (POST), `/accounts/profile/` (plus POST-only action URLs under `/accounts/profile/` for display name, share link, and API token)
  - `/search/`: Open Library search (`?q=…&page=…`), plus a POST save endpoint
  - `/shelf/`: My Shelf (`?q=&status=&min_rating=&rated=&ordering=&page=`)
  - `/shelf/<pk>/`: book detail, with POST sub-routes for update, remove, add note, and delete note
  - `/shared/<share_token>/`: public read-only shared shelf (per-group "Show more" via a query parameter)
- **API URLs** (DRF, under `/api/`):
  - `/api/entries/` (GET list, POST create), `/api/entries/<pk>/` (GET, PUT, PATCH, DELETE)
  - `/api/entries/<pk>/notes/` (GET, POST), `/api/entries/<pk>/notes/<note_pk>/` (GET, DELETE; PUT/PATCH → 405)
  - `/api/shared/<share_token>/` (GET only, paginated flat list)
- **Models**:
  - `User(AbstractUser)` with `share_token` (nullable, unique, `secrets`-generated URL-safe) and `display_name` (blank default). It exists before the first migration. There is no Profile model.
  - `Book`: one per Open Library work. `ol_work_key` is unique and stored without the `/works/` prefix. Also `title`, `authors`, `first_publish_year` (nullable), `cover_id` (nullable). Rows are never user-edited and never deleted.
  - `ShelfEntry`: FK `user`, FK `book`, unique `(user, book)`. Also `status` (TextChoices: To Be Read / Currently Reading / Finished / Did Not Finish, default TBR), `rating` (nullable, 1–5), `finished_on` (nullable, not in the future), `added_at`, `updated_at`.
  - `Note`: FK `entry` (cascade), `text`, `created_at`. Add and delete only.
- **Auth/authorization**: Django session auth for the website, with every app page login-required except the landing, auth, and shared pages. For the API: DRF Session + Token authentication. Every owner query is scoped to `request.user`; another user's objects return **404, never 403**.
- **Open Library**: all outbound calls go through one service module that callers reach as a module attribute (so tests can monkeypatch it). Requests use a ~5s timeout and an identifying User-Agent. Errors are custom exceptions (unavailable → website message / API 503; bad response → website message / API 502; not found → field error / API 400). There are no retries. Search results are cached in the in-memory cache for ~10 minutes, and failures are never cached.
- **HTMX convention**: views return a partial for HTMX requests and a full page otherwise. Success toasts come from Django messages delivered by an out-of-band swap into a toast container. Errors appear inline. In-flight requests show a spinner and disable their trigger.

---

## Phase 1: Project foundation and landing page

**User stories**: 1, 7, 98, 99

### What to build

Set up the Django project (`config`) with the `accounts` and `shelf` apps, rename the Python project, and wire environment-based settings with a committed `.env.example`. Add the custom `User` model before the first migration. Set up the Tailwind/DaisyUI build with a project-owned CSS input that makes Forest the default theme, and vendor HTMX. Build the base layout: a navbar that collapses to a menu on phones, a toast container, and a themed 404 page. Add the logged-out landing page (hero, tagline, Sign up / Log in buttons, three feature cards). Set up Ruff and Pytest with a global fixture that blocks real network calls and a fixture that clears the cache between tests.

### Acceptance criteria

- [ ] `uv run --env-file .env python manage.py runserver` serves the landing page styled with the Forest theme.
- [ ] HTMX is served from static files, not a CDN.
- [ ] `AUTH_USER_MODEL` points to the custom `User`, and the initial migrations apply cleanly.
- [ ] Settings come from environment variables. Debug is off unless `DJANGO_DEBUG` enables it, and `.env.example` documents every variable.
- [ ] Unknown URLs render the themed 404 page (with debug off).
- [ ] The navbar collapses into a menu at phone width.
- [ ] `pytest` passes with no `.env` and no network, and a test that tries a real HTTP call fails loudly.
- [ ] `ruff check` and `ruff format --check` pass.

---

## Phase 2: Accounts and a protected empty shelf

**User stories**: 2, 3, 4, 5, 6, 8, 39

### What to build

Add signup (Django's user creation form), login, and logout as centered DaisyUI cards with inline field errors and links to each other. Signup logs the user in and redirects to My Shelf. The navbar shows Search, My Shelf, and a user dropdown (Profile, Log out) when logged in. A logged-in visit to `/` redirects to `/shelf/`. My Shelf and Search exist as login-required pages. My Shelf shows its empty-shelf state with a button to Search.

### Acceptance criteria

- [ ] A visitor can sign up and lands on My Shelf, logged in.
- [ ] Login and logout work. Logout is a POST.
- [ ] Invalid auth form input shows inline field errors.
- [ ] A logged-in user who visits `/` is redirected to `/shelf/`.
- [ ] Anonymous requests to `/shelf/`, `/search/`, and `/accounts/profile/` redirect to login with `next`.
- [ ] An empty shelf shows a message and a link to Search.
- [ ] Tests cover signup, auto-login, redirects, and login-required protection.

---

## Phase 3: Open Library search (read-only)

**User stories**: 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 24, 25, 26, 96

### What to build

Build the Open Library service module's search function: the search endpoint with a restricted `fields` list, 20 per page, the identifying User-Agent (contact email from configuration, with a fallback), a ~5s timeout, the custom unavailable/bad-response exceptions, and a ~10-minute cache keyed on the normalized query and page. Build the Search page: the form submits through HTMX, swaps only the results area, and pushes `?q=&page=`. Results use the list-row component (cover with a placeholder on missing or failed covers, title, authors, year), the total count, and a shortened pagination list capped at page 50. Cover every state: before searching, loading (spinner, disabled button), no matches, empty submit (a hint and no request), past the cap ("Try a more specific search", no request), and Open Library unavailable (a persistent alert with Try again and a link to My Shelf). Add the "Book data from Open Library" credit in the footer.

### Acceptance criteria

- [ ] Searching swaps the results without a full reload and updates the URL. Reloading or bookmarking that URL renders the same results as a full page.
- [ ] Results show cover (or placeholder), title, authors, year, and the total count.
- [ ] Pagination shows a shortened page list, and pages beyond 50 make no outbound call.
- [ ] An empty query shows a hint and makes no outbound call.
- [ ] Timeouts, connection errors, 5xx, and 429 show the persistent "unavailable" alert. Malformed JSON shows a friendly message. No page crashes.
- [ ] Service tests (using `responses`) cover parsing, the User-Agent, timeouts, connection errors, 5xx/429, malformed JSON, a cache hit on an identical second search, and failures not being cached.
- [ ] View tests monkeypatch the service and cover each page state.

---

## Phase 4: Save from search and list books on My Shelf

**User stories**: 19, 20, 21, 22, 23, 27, 41

### What to build

Add the `Book` and `ShelfEntry` models. Add the service lookup that queries `key:/works/<key>`, adding the prefix back and treating zero matches as not found. The save flow:
1. validate the `OL<digits>W` key format;
2. reject a duplicate for this user before any outbound call;
3. reuse an existing `Book` or create one from a single lookup;
4. create the entry.

Each search result row ends with a split button: Save (To Be Read) plus a menu for Currently Reading / Finished / Did Not Finish. Saving swaps the button to "✓ On your shelf" (linking to the entry) and shows a toast. A failure shows an inline error on that row. Books already on the shelf are marked with one query per results page. My Shelf lists the user's entries as list rows (cover, title, authors, year, status badge, stars, finished date, added date, notes count placeholder), ordered by date added. It never calls Open Library.

### Acceptance criteria

- [ ] One click saves a book as To Be Read, and the menu saves with the other statuses.
- [ ] After saving, the row shows "✓ On your shelf" in place and a toast appears.
- [ ] Results already on the shelf show "✓ On your shelf" when the page renders.
- [ ] Invalid keys and duplicates are rejected with no outbound call.
- [ ] Unknown keys (zero matches) show a not-found error on the row.
- [ ] Saving a book that already exists in `Book` works while Open Library is down.
- [ ] My Shelf renders saved books with Open Library unavailable.
- [ ] Service tests cover the `/works/` prefix and zero-match not found. View tests cover the save outcomes and ownership.

---

## Phase 5: Shelf browsing

**User stories**: 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 40

### What to build

Add one `django-filter` FilterSet for shelf entries:
- **Search**: case-insensitive contains on title and authors.
- **Filters**: status, minimum rating, rated / not rated.
- **Ordering**: a whitelist of title, author, rating, date added, date updated, and finished date, both directions, nulls last.
- **Pagination**: 12 per page.

My Shelf gains a sidebar with status filters and their counts, minimum rating, rated/unrated, and Clear all filters. The main column has a debounced live search box and a sort dropdown above the list, pagination with the current range, and a Currently Reading strip that hides while any filter or search is active. Every change swaps the results through HTMX and pushes a bookmarkable URL. On phones the sidebar sits behind a Filters button. When no books match, a Clear filters button appears.

### Acceptance criteria

- [ ] Typing in the search box filters the list after a short pause, and the URL updates.
- [ ] The status, minimum rating, and rated/unrated filters combine correctly, and status counts reflect the user's whole shelf.
- [ ] Every sort option works in both directions, and null ratings and finished dates sort last.
- [ ] The shelf pages at 12 per page and shows the range (for example "13–24 of 40").
- [ ] A bookmarked filtered URL renders the same view as a full page.
- [ ] The Currently Reading strip shows only when no filters or search are active.
- [ ] When no books match, the "no matches" state appears with a Clear filters button.
- [ ] Tests cover the FilterSet directly: each filter, each ordering, null ordering, and pagination size.

---

## Phase 6: Book detail and editing

**User stories**: 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53

### What to build

Add the `/shelf/<pk>/` detail page with two columns. The left column is sticky on desktop: large cover, title, authors, year, "on your shelf since", Open Library link, and Remove from shelf. The right column holds a "Your reading" card with one form: a status button group, a clickable 5-star rating with Clear, and a finished date input capped at today. It saves through HTMX with an inline "Saved ✓", and validation errors appear next to their fields. Rating and finished date are allowed at any status, and future dates are rejected. Remove opens a confirmation dialog that states how many notes will be deleted, then redirects to My Shelf with a toast. The layout stacks to one column on phones. Shelf rows link to the detail page.

### Acceptance criteria

- [ ] The detail page shows the book info and links to `https://openlibrary.org/works/<key>`.
- [ ] Status, rating, and finished date save together without a reload and show "Saved ✓".
- [ ] A rating can be set at any status (including DNF) and cleared.
- [ ] A future finished date is rejected with an inline error. The date input's `max` is today.
- [ ] Removing a book asks for confirmation, deletes the entry, redirects to My Shelf, and shows a toast.
- [ ] Another user's entry returns 404 for view, update, and remove.
- [ ] Tests cover validation rules, ownership 404s, and removal.

---

## Phase 7: Notes

**User stories**: 54, 55, 56, 57, 58, 59, 60

### What to build

Add the `Note` model, deleted together with its entry. Below the "Your reading" card on the detail page, add an add-note box at the top and notes listed newest first with timestamps, each with a delete button that asks for confirmation. Adding and deleting update the list in place through HTMX. Empty notes are rejected inline. A friendly empty state shows when there are no notes. My Shelf rows show the real notes count, and the Remove dialog's count is accurate.

### Acceptance criteria

- [ ] Adding a note puts it at the top of the list without a reload, with its timestamp.
- [ ] Empty or whitespace-only notes are rejected with an inline error.
- [ ] Deleting a note asks for confirmation and removes it in place.
- [ ] Notes are deleted when their entry is removed.
- [ ] Adding to or deleting from another user's entry or note returns 404.
- [ ] The shelf rows' notes count matches.

---

## Phase 8: Profile, sharing, and public shared shelf

**User stories**: 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 79

### What to build

Build the Profile page with stacked cards. The **Display name** card is an editable form. The **Share your bookshelf** card changes with state:
- **No link**: an explanation of what is shared (books, statuses, ratings, finished dates, never notes) and a Create button.
- **Link exists**: a read-only URL with Copy and Open, plus Regenerate and Disable, both confirmed.

Each action is an HTMX POST that swaps the card and shows a toast. Tokens come from `secrets`. The public `/shared/<share_token>/` page needs no login and is read-only:
- It is headed by the display name, or "A shared bookshelf".
- Groups appear in this order: Currently Reading, Finished (most recently finished first), To Be Read, Did Not Finish. Empty groups are hidden.
- Each group is a cover grid with title, authors, and stars, showing 12 books with an HTMX "Show more" that appends the next 12.
- It never shows notes, the username, or the user ID.
- Invalid, regenerated, or disabled tokens return 404.

### Acceptance criteria

- [ ] Creating a link shows a working URL. Copy and Open work.
- [ ] Regenerate (after confirming) makes the old URL return 404, and the new one works.
- [ ] Disable (after confirming) makes the URL return 404, and the card returns to its Create state.
- [ ] Display name saves in place with a toast and appears on the shared page. When it's blank, the page shows "A shared bookshelf".
- [ ] The shared page works logged out, groups and orders books correctly, hides empty groups, and "Show more" appends without a reload.
- [ ] Tests confirm that the shared page response contains no note text and no username.
- [ ] The shared page has no edit controls or forms.

---

## Phase 9: API read access with tokens

**User stories**: 77, 78, 80, 81, 86, 92

### What to build

Configure DRF with Session and Token authentication and add the API access card to the Profile page: the token masked except its last characters, Reveal, Copy, and a confirmed Regenerate that invalidates the old token (HTMX swap and toast). Add `/api/entries/` (list) and `/api/entries/<pk>/` (retrieve) for the requesting user only. The list uses the same FilterSet and 12-per-page pagination as My Shelf. The owner serializer nests read-only book info: work key, title, authors, first publish year, and a computed cover URL (null when there is no cover ID).

### Acceptance criteria

- [ ] The token is masked by default. Reveal and Copy work. Regenerate (after confirming) makes the old token return 401.
- [ ] `curl -H "Authorization: Token <t>" /api/entries/` lists only the caller's entries. A browser session also works.
- [ ] The list supports the same `q`, `status`, `min_rating`, `rated`, `ordering`, and `page` parameters as the website, with matching results (parity test).
- [ ] Retrieve includes the nested book with `cover_url`.
- [ ] Another user's entry returns 404. Unauthenticated requests return 401/403.

---

## Phase 10: API entry writes

**User stories**: 82, 83, 84, 85, 87, 88, 89

### What to build

Add create, update, partial update, and delete to `/api/entries/`. Create accepts only a work key plus optional status, rating, and finished date, and runs the same save flow as the website (format check → duplicate check → reuse or look up `Book` → create entry). Map errors this way:
- invalid, unknown, or duplicate key → 400;
- Open Library unavailable → 503;
- bad response → 502.

Sending a work key on update returns a strict 400. Rating and finished-date validation match the website form. Delete removes the entry and its notes.

### Acceptance criteria

- [ ] POST with a valid new key creates a `Book` and an entry. Book fields come from Open Library, never from the client.
- [ ] Bad-format, unknown, and duplicate keys return 400 with a field error. Bad-format keys and duplicates make no outbound call.
- [ ] A monkeypatched unavailable error returns 503, and a bad response returns 502.
- [ ] PUT and PATCH update status, rating, and finished date. Including the work key returns 400.
- [ ] Rating outside 1–5 and future finished dates return 400, matching the form tests.
- [ ] DELETE removes the entry and its notes. Another user's entry returns 404 for every method.

---

## Phase 11: API notes, public shared API, and throttling

**User stories**: 90, 91, 93, 94, 95, 97

### What to build

Add notes nested under entries: `/api/entries/<pk>/notes/` (list, create) and `/api/entries/<pk>/notes/<note_pk>/` (retrieve, delete). PUT and PATCH return 405. Entries the caller doesn't own return 404, including for note creation. Add the public `/api/shared/<share_token>/` endpoint: GET only, paginated flat list, using a separate public serializer with only book info, status, rating, and finished date (no notes key, user ID, or username). Configure DRF throttling with the in-memory cache: about 60 requests per minute per user, and stricter scoped limits (about 10 per minute) on entry creation and the shared endpoint. Exceeding a limit returns 429 with `Retry-After`.

### Acceptance criteria

- [ ] Notes can be listed, created, and deleted on the caller's own entries. Empty text returns 400.
- [ ] PUT and PATCH on a note return 405.
- [ ] Note requests on another user's entry return 404.
- [ ] `/api/shared/<token>/` works without auth and returns a paginated list. No item has a `notes` key or any user identifier.
- [ ] POST, PUT, PATCH, and DELETE on the shared endpoint are rejected (405).
- [ ] Regenerated or disabled tokens return 404.
- [ ] Exceeding the create or shared limits returns 429 with `Retry-After`. The cache-clearing fixture keeps throttle counters isolated between tests.
