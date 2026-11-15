# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-11-14 — Implemented Phase 6: Book detail and editing

### Prompts
1. `/implement @prd/one-more-chapter.md @plans/one-more-chapter.md Implement Phase 6`
2. yes, go with all three *(TDD behaviors: status, rating, and finished
   date save together with rating allowed at any status and clearable; a
   future finished date is rejected inline and nothing is saved; another
   user's entry is 404 for view, update, and remove)*
3. make it pass *(RED test for behavior 1)*
4. yes, move on to behavior 2
5. make it pass *(RED test for behavior 2)*
6. yes, move on to behavior 3
7. make it pass *(RED test for behavior 3)*
8. yes, continue with the rest of the phase
9. When navigating to /shelf/1 as a different user - a 404 page is
   displayed but it is not the styled version
10. The Remove from shelf button and the clear button for the star ratings
    need outlines
11. The spacing between the Back to My Shelf link and the cover art is
    very small - can we increase that a bit?
12. It is still pretty tight - lets go to 32px
13. The manual checks pass, finish the phase

### Summary
- **Outcome:** Built Phase 6 of the plan:
  - `/shelf/<pk>/` detail page in two columns (stacks on phones). The
    left column is sticky on wide screens: large cover, title, authors,
    first published year, "On your shelf since", an Open Library link,
    and Remove from shelf.
  - `shelf/forms.py`: `ShelfEntryForm`, a ModelForm over status, rating,
    and finished date. The rules stay on the model (rating 1–5, no future
    date), so the Phase 10 API can share them. The date picker's `max` is
    today. The "Your reading" card renders it as a status button group
    (TBR / Reading / Finished / DNF), clickable DaisyUI stars with Clear,
    and the date input.
  - `entry_update` saves all three together through HTMX and shows
    "Saved ✓" inline. Errors appear under their fields (new shared
    `templates/partials/field_errors.html`) and nothing is saved. Without
    JavaScript it redirects with a toast, or shows the full page with
    errors.
  - `entry_remove` deletes the entry (the shared `Book` row is kept),
    then goes to My Shelf with a toast. A `<dialog>` confirms first
    (`data-confirm-dialog` in `app.js`); without JavaScript the form just
    submits. The exact notes count waits for Phase 7.
  - `_get_own_entry()` scopes every detail route to the logged-in user,
    so other users' entries are 404.
  - Shelf row titles, Currently Reading strip cards, and Search's
    "✓ On your shelf" now link to the detail page; My Shelf stays
    highlighted in the navbar there.
  - TDD for all three chosen behaviors, then normal tests for page
    content, the date cap, invalid status and rating, non-HTMX saves,
    removal, POST-only routes, login redirects, the themed 404, and the
    links: 216 tests passing, Ruff clean.
- **Deviations:**
  - All three proposed TDD behaviors were accepted as proposed.
  - The Remove from shelf and Clear (rating) buttons were restyled with
    outlines, and the gap under "Back to My Shelf" was raised from 16px
    to 24px, then to 32px, at the user's request.
- **Sideways:**
  - The unstyled 404 the user saw was Django's debug page (`.env` has
    `DJANGO_DEBUG=true`), not a bug. The themed page only shows with
    debug off, as planned in Phase 1. A test was added to check the
    themed 404 for another user's entry with debug off, and the user was
    shown how to check it with `runserver --insecure`.
  - Linking row titles broke the Phase 5 `listed_titles()` test helper,
    and three Search/save tests still expected the Phase 4 placeholder
    link (`/shelf/#entry-N`). Both were fixed mechanically; what they
    assert did not change.
  - Two new form-state assertions first depended on template whitespace;
    they were rewritten as a small regex helper before finishing.

## 2026-11-14 — Implemented Phase 5: Shelf browsing

### Prompts
1. `/implement @prd/one-more-chapter.md @plans/one-more-chapter.md Implement Phase 5`
2. 1 and 2 *(TDD behaviors: nulls sort last in both directions; filters
   combine while status counts cover the whole shelf. The third proposed
   behavior, the Currently Reading strip hiding while filtering, was not
   chosen)*
3. make it pass *(RED test for behavior 1)*
4. yes, move on to behavior 2
5. make it pass *(RED test for behavior 2)*
6. yes, continue with the rest of the phase
7. When using the back button, the page displays the correct books, but
   the status, radios, and drop down show their default states
8. The clear all filters button on the sidebar and the clear filters
   button when no items are shown need outlines to make it clear that
   they are buttons
9. The currently reading banner at the top can be displayed regardless of
   filter or search - it is weird that it disappears and the page jumps
   when you apply a filter
10. The manual checks pass, finish the phase

### Summary
- **Outcome:** Built Phase 5 of the plan:
  - Added `django-filter`. `shelf/filters.py` holds `ShelfEntryFilter`,
    shared with the API in Phase 9: `q` (title or authors, ignoring
    case), `status`, `min_rating` (1–5), `rated` (yes/no), and `ordering`
    over title, author, rating, added, updated, and finished in both
    directions. A `NullsLastOrderingFilter` puts empty ratings and
    finished dates last, and every sort ends with newest-added then ID
    so pagination is stable. Invalid values are reported by the
    FilterSet; the website ignores them (the API will return 400).
    `status_counts()` counts the whole shelf in one query.
  - My Shelf: a sidebar with status (radio rows with whole-shelf counts),
    minimum rating, rated/not rated, and Clear all filters; a live
    search box (300ms debounce) and sort dropdown; "Showing 13–24 of 40"
    with 12 per page and the shared pagination partial; a "no matches"
    state with Clear filters. One GET form drives everything: HTMX swaps
    only `#shelf-results`, pushes the URL, and cancels stale requests
    (`hx-sync`). It also works as a plain form without JavaScript.
  - `app.js`: blank fields are dropped from HTMX filter URLs, Clear
    filters resets the form (keeping the sort) and re-runs it, and the
    phone Filters button shows or hides the sidebar.
  - TDD for both chosen behaviors, then normal tests for each filter,
    every sort, invalid values, pagination and range, the strip, HTMX
    partials, bookmarked URLs, empty states, and ownership: 193 tests
    passing, Ruff clean.
- **Deviations:**
  - Picked 2 of the 3 proposed TDD behaviors (the strip rule was left
    out, which turned out well since that rule was later dropped).
  - The user changed user story 29: the Currently Reading strip now
    always shows instead of hiding while filtering, because it made the
    page jump. The PRD (story 29 and the My Shelf section) and Phase 5 of
    the plan were updated to match, and the out-of-band strip swap was
    removed.
  - Both Clear filters buttons were restyled with outlines at the user's
    request.
- **Sideways:**
  - The first version of the null-ordering filter overrode django-filter's
    `get_ordering_value()` with a different signature; it was caught
    before running and changed to use the built-in method.
  - Two sort-by-updated test cases had wrong expectations (the test's
    never-edited book has the oldest `updated_at`); the test, not the
    code, was fixed.
  - A Bash heredoc failed on quoting while adding tests; the tests were
    added with the Edit tool instead.
  - Manual testing found that the Back button showed the right books but
    default filter controls: HTMX's history snapshot records the controls
    as first loaded. Fixed with `hx-history="false"` so Back re-requests
    the page from the server. The Search page had the same bug (an older
    query in the search box) and got the same fix. Stale snapshots
    already in the browser had to be cleared from `localStorage` once.

## 2026-11-14 — Implemented Phase 4: Save from search and list books on My Shelf

### Prompts
1. `/implement @prd/one-more-chapter.md @plans/one-more-chapter.md Implement Phase 4`
2. Go ahead with all 3 *(TDD behaviors: the work-key lookup adds the
   `/works/` prefix and treats zero matches as not found; bad keys and
   duplicates are rejected before any outbound call; a book already in
   the `Book` table saves while Open Library is down)*
3. Approved, go ahead and implement it *(RED test for behavior 1)*
4. Yes, move on to behavior 2
5. Approved, go ahead and implement it *(RED test for behavior 2)*
6. Yes, move on to behavior 3
7. Approved, go ahead and implement it *(RED test for behavior 3)*
8. Yes, continue with the rest of Phase 4
9. The right side of the save button (where the drop down bar is) has a
   white square background that is visible behind the save button
10. When a book has a long title, the save button moves places when using
    a phone display - is it possible to wrap the title text earlier and
    keep the save button in the same place for all entries?
11. Can we put some kind of message somewhere that explains that the
    default Save button will save the book as "To Be Read" - it is
    currently unclear
12. It would be nice to make the hint below the search bar stand out a
    bit more - it currently blends in with the other text below the
    search bar
13. That looks better - the other manual checks pass

### Summary
- **Outcome:** Built Phase 4 of the plan:
  - `Book` and `ShelfEntry` models (first `shelf` migration), with
    `Book.authors` stored as one comma-separated string so Phase 5 can
    search and sort by author as plain text. Rating (1–5) and finished
    date (not in the future) validators are on the model already.
  - `openlibrary.get_work()`: a `key:/works/<key>` lookup through the
    search endpoint that adds the prefix back, checks the returned key,
    and raises the new `OpenLibraryNotFound` on zero matches. Not cached.
  - `shelf/saving.py`: `save_to_shelf()`, shared by the website now and
    the API in Phase 10. Checks status and key format, then duplicates
    (`AlreadyOnShelf` carries the existing entry), reuses an existing
    `Book` or looks it up once, and turns a double-click race into
    `AlreadyOnShelf`. Outages pass through as Open Library exceptions.
  - Search rows end with a split Save button (Save = To Be Read, ▾ menu
    for the other statuses) that swaps to "✓ On your shelf" in place
    with a toast (out-of-band swap), or shows an inline error. Works
    without JavaScript via a safe `next` redirect. Saved results are
    marked with one query per results page. "On your shelf" links to the
    row on My Shelf until the detail page exists (Phase 6).
  - My Shelf lists entries newest first as rows with status badge, stars
    or "Not rated", finished and added dates, and a "0 notes"
    placeholder (Phase 7). Admin pages for both models.
  - TDD for all three behaviors, then normal tests for the service,
    save flow, save view, search marking, and My Shelf: 137 tests
    passing, Ruff clean.
- **Deviations:** No recommendations were overridden. Manual testing led
  to three UI follow-ups: a visual bug (below), keeping the Save button
  top-right on phones by letting long titles wrap instead of the row,
  and a "Save adds a book as To Be Read" hint above the results (plus a
  button tooltip), restyled as a soft info alert to stand out.
- **Sideways:**
  - Behavior 2's first RED was an `IntegrityError` from the stub, not an
    assertion; the stub was fixed and the test re-run to a real RED.
  - Behavior 3's RED was the `OpenLibraryUnavailable` exception itself
    rather than an assertion; this was flagged and approved as-is
    because the exception *is* the missing behavior.
  - Two no-JavaScript save tests followed the redirect into a real
    search and were stopped by the network-blocking fixture; they now
    fake `openlibrary.search`.
  - The split button showed a light box behind ▾ because `join-item`
    (which adds a border) was on the dropdown wrapper as well as the
    button; removed from the wrapper.

## 2026-11-13 — Implemented Phase 3: Open Library search (read-only)

### Prompts
1. `/implement @prd/one-more-chapter.md @plans/one-more-chapter.md Implement Phase 3`
2. Go ahead with all 3 *(TDD behaviors: failures sorted into
   "unavailable" vs "bad response"; only successful searches cached;
   the search view skips Open Library for blank queries and pages past 50)*
3. Approved, go ahead and implement it *(RED test for behavior 1)*
4. Yes, move on to behavior 2
5. Approved, go ahead and implement it *(RED test for behavior 2)*
6. Yes, move on to behavior 3
7. Approved, go ahead and implement it *(RED test for behavior 3)*
8. Yes, continue with the rest of Phase 3
9. The manual checks pass
10. Before we update PROMPTS.md - evaluate our current CLAUDE.md file and
    suggest any needed additions to keep it up to date with the current
    codebase *(interrupted my PROMPTS.md edit to ask this)*
11. Apply 1-4, but be as succint as possible, and move the fixture
12. Yes, update PROMPTS.md, then commit and push

### Summary
- **Outcome:** Built Phase 3 of the plan:
  - `shelf/openlibrary.py`, the single Open Library service module:
    search with a restricted `fields` list, 20 per page, a page cap of
    50, a 5-second timeout, and a User-Agent with the app name, version,
    and configured contact email (app name only without one). Failures
    raise `OpenLibraryUnavailable` (timeouts, connection errors, 5xx,
    429) or `OpenLibraryBadResponse` (other 4xx, invalid JSON, unexpected
    shape). Successful searches are cached for 10 minutes, keyed on the
    hashed, normalized (trimmed, lowercased) query plus the page.
  - The Search page: an HTMX form that swaps only the results area and
    pushes `?q=&page=`, with a spinner and disabled button while loading.
    States: before searching, empty submit, past page 50, past the last
    page, no matches, results (with total count), and a persistent
    "unavailable" / "couldn't read" alert with Try again and Go to My
    Shelf. Footer credit to Open Library.
  - Reusable pieces for later phases: `shelf/htmx.py` (partial vs. full
    page, `Vary: HX-Request`, full page on HTMX history-restore), a
    list-row and a cover partial (placeholder for missing or failed
    covers, via `?default=false` and a small script in `app.js`), a
    shortened pagination partial built on Django's
    `get_elided_page_range` and `{% querystring %}`, and a `cover_url`
    template filter. Added `django.contrib.humanize` for the "1,234"
    count.
  - TDD for all three proposed behaviors, then normal tests for parsing,
    request parameters, the User-Agent, per-page caching, and every view
    state: 90 tests passing, Ruff clean.
  - CLAUDE.md gained short Commands, Shared building blocks, and
    Conventions sections. The duplicated `logged_in_client` test fixture
    moved into `conftest.py`.
- **Deviations:** The user took all three proposed TDD behaviors and
  approved every RED test without changes; the manual checks passed on
  the first run. Before the wrap-up, the user asked for a CLAUDE.md
  review. I suggested five additions; the user took 1–4 (commands,
  shared building blocks, testing conventions, HTMX/UI conventions),
  skipped the optional workflow line, asked for them as succinct as
  possible, and accepted my side suggestion to move the duplicated
  fixture.
- **Sideways:** The first RED run for behavior 1 failed with
  `KeyError`/`TypeError` crashes in the two bad-structure cases instead
  of on the assertion; I treated that as missing scaffolding and wrapped
  parsing errors in the generic base error until all 8 cases failed on
  the assertion. The behavior 3 scaffold view called `int()` on the raw
  `page` parameter (it would crash on `?page=abc`); that was replaced
  with safe page parsing and a test in the normal implementation step.
  Ruff's formatter fixed two over-long test lines and, after the fixture
  move, a leftover blank line.

## 2026-11-13 — Implemented Phase 2: accounts and a protected empty shelf

### Prompts
1. `/implement @prd/one-more-chapter.md @plans/one-more-chapter.md Implement Phase 2`
2. 1 and 3 *(TDD behaviors: signup logs in and redirects to My Shelf;
   private pages require login)*
3. Approved, go ahead and implement it *(RED test for behavior 1)*
4. Yes, move on to behavior 3
5. Approved, go ahead and implement it *(RED test for behavior 3)*
6. Yes, continue with the rest of Phase 2
7. On the desktop view - the current page is not highlighted in the navbar
8. The manual checks pass, but I have one question before we finish the
   phase. If someone clones my repo from GitHub, is the user I just
   created available to them to log in with?
9. I would like to add a 'seed' command that creates two sample users with
   populated reading lists - this can either be its own new phase or it
   can be added into one of the smaller remaining phases
   - Answered one multiple-choice question, taking the recommendation:
     add it to Phase 7.

### Summary
- **Outcome:** Built Phase 2 of the plan:
  - Signup (Django's `UserCreationForm` subclassed for `accounts.User`)
    that logs the new user in and redirects to My Shelf; login and
    POST-only logout using Django's built-in views. Logged-in users who
    open `/`, signup, or login go straight to My Shelf.
  - Auth pages as centered DaisyUI cards with inline field errors (red
    text and a red input border via `DaisyFormMixin`) and cross-links.
  - A logged-in navbar with Search, My Shelf, and a user dropdown
    (Profile, Log out), collapsing into the phone menu.
  - Login-required My Shelf (empty state with a "Find a book" button),
    plus placeholder Search and Profile pages.
  - TDD for two behaviors (signup auto-login + redirect; login-required
    pages with `next`), then normal tests for the rest: 47 tests passing,
    Ruff clean.
  - Updated the plan: Phase 7 now also includes a `seed` management
    command for two demo users with populated reading lists.
- **Deviations:** I proposed three TDD behaviors; the user chose 1 and 3
  and dropped behavior 2 (the `/` redirect), which got a normal test
  instead. Both RED tests were approved without changes. Follow-up
  question: whether a locally created user ships with the repo (no:
  `db.sqlite3` is git-ignored, and a fresh clone migrates an empty
  database). The user then asked for a seed command; I recommended adding
  it to Phase 7 over a new Phase 12 or growing it phase by phase, and the
  user agreed.
- **Sideways:** On desktop, the current page wasn't highlighted in the
  navbar: DaisyUI's `btn-active` fills with `base-200`, the same color as
  the navbar, so it was invisible. Caught by the user during manual
  checks; fixed by using `btn-neutral` (matching the phone menu's
  highlight) plus `aria-current="page"`, with a new test. My first fix
  put the `aria-current` attribute inside the class string; I rewrote it
  as a plain `if/else` for readability before running anything.

## 2026-11-13 — Implemented Phase 1: project foundation and landing page

### Prompts
1. `/implement @prd/one-more-chapter.md @plans/one-more-chapter.md Implement Phase 1`
2. Approved, go ahead with all three *(TDD behaviors: env-based debug and
   secret key rules, blocking real network calls in tests, themed 404)*
3. Approved, go ahead and implement it *(RED test for behavior 1)*
4. Approved, go ahead and implement it *(RED test for behavior 2)*
5. Yes, move on to behavior 3
6. Approved, go ahead and implement it *(RED test for behavior 3)*
7. Yes, continue with the rest of Phase 1
8. In the navbar on the desktop site, the Log In button blends in with the
   background - it is not obvious that it is a button. The same applies to
   both the Log In and Sign Up buttons nested inside the hamburger menu on
   the phone display.
9. The text on the Log In buttons for both desktop and mobile should not be
   green - they should match the color of the landing page's hero.
10. In both desktop and mobile versions, the ordering of the Sign Up and Log
    In buttons is reversed between the nav bar and the hero - please make
    them appear in the same order on both layouts
11. The manual checks pass, go ahead and finish the phase

### Summary
- **Outcome:** Built Phase 1 of the plan:
  - Django 6.1 project `config` with the `accounts` and `shelf` apps; the
    Python project renamed to `one-more-chapter`.
  - Environment-based settings through `config/env.py`, a committed
    `.env.example`, and a local git-ignored `.env`. Debug is off unless
    `DJANGO_DEBUG` is yes-like; without a secret key and with debug off,
    startup fails loudly. Tests use `config/settings_test.py`, so they need
    no `.env`.
  - Custom `accounts.User` (`share_token`, `display_name`) before the first
    migration.
  - Tailwind + DaisyUI via `django-tailwind-cli` with `tailwind-cli-extra`
    pinned to v2.10.35 and a project-owned `tailwind/source.css` making
    Forest the only theme. HTMX 2.0.7 vendored in `assets/js/`.
  - Base layout (navbar collapsing to a menu on phones, toast container),
    themed 404 page, and the landing page (hero plus three feature cards).
  - Root `conftest.py` with fixtures that block real network calls and
    clear the cache. Ruff configured; README rewritten with setup, run,
    test, and configuration instructions.
  - TDD for three behaviors (settings rules, network blocking, themed 404),
    then normal tests for the rest: 24 tests passing, Ruff clean.
- **Deviations:** All three proposed TDD behaviors were approved as
  written, and each RED test was approved without changes. The user
  requested three navbar styling fixes during manual verification (see
  Sideways). Choices I made and flagged rather than asked about:
  - compiled CSS is git-ignored, so a fresh clone runs `tailwind build`;
  - `scripts/` is excluded from Ruff instead of rewriting the research
    script;
  - Ruff targets Python 3.13 formatting to keep `except (A, B):`;
  - test functions use descriptive names rather than docstrings;
  - for the button order, I kept the hero's order (Sign up first) and
    changed the navbar, offering to flip it.
- **Sideways:**
  - Behavior 1 was covered by two small test functions (debug flag and
    secret key) rather than one; this was disclosed with the RED test.
  - `django-tailwind-cli` warned that the source CSS sat inside the static
    folder; it was moved to `tailwind/source.css`.
  - The first CSS build ran before any templates existed, so it had to be
    rebuilt to pick up their classes.
  - The first Ruff run failed on Django's generated stub files and the
    research script; stubs were cleaned up and `scripts/` excluded.
  - The navbar's Log in button first used `btn-ghost`, which blended into
    the background. The fix used `btn-outline btn-primary` (green), which
    the user also rejected; the final version is plain `btn-outline`,
    matching the hero. The user also caught that the navbar and hero listed
    the two buttons in opposite orders.

## 2026-11-13 — Wrote the initial CLAUDE.md

### Prompts
1. Create the initial CLAUDE.md for this project. Keep it to about 20-30
   lines. Include only: a one-line project description; the approved
   technology stack and package manager; durable, project-wide architecture
   decisions already established in the PRD; short pointers to the PRD,
   plan, and prototypes instead of repeating their details. Do not add
   commands yet because the project tooling has not been installed or
   verified. Do not predict project structure, paths, template conventions,
   URL conventions, or testing commands that do not exist yet. Do not copy
   business requirements, user stories, implementation phases, rejected
   alternatives, or detailed feature rules into CLAUDE.md. Do not invent
   new architectural conventions.
2. *(Correction, after rejecting the first write of the file)* Please add
   the following: "docstrings and type hints on every public function" - I
   am a beginner and this will help me understand the code that is being
   written
3. Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways.

### Summary
- **Outcome:** Read the PRD, the start of the plan, and the repo layout,
  then wrote `CLAUDE.md` (about 30 lines, counting blank lines). It has a
  one-line description, the stack with uv as the package manager, a Code
  style section with the docstring and type-hint rule, nine architecture
  decisions taken from the PRD, and pointers to the PRD, plan, prototypes,
  and Open Library research doc. It has no commands, URL paths, user
  stories, or phases. I also saved a memory note that the user is a
  beginner. Nothing was committed.
- **Deviations:** No recommendations were offered, so none were
  overridden, and no follow-up questions were asked. The user added a
  coding convention (docstrings and type hints on every public function)
  that wasn't in the original instructions.
- **Sideways:** The user rejected the first write of `CLAUDE.md` to add
  the docstring and type-hint rule. The second write included it. The
  "Code style" heading and the pointer to the research doc were my
  additions; the user didn't ask for either.

## 2026-11-13 — Broke the One More Chapter PRD into an 11-phase implementation plan

### Prompts
1. `/prd-to-plan @prd/one-more-chapter.md`
2. Merge 8 and 9, merge 12 and 13
3. Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways.

### Summary
- **Outcome:** Looked through the repo. It has no Django code yet: only
  `pyproject.toml` (still named `book-tracker`), `scripts/search_books.py`,
  the docs, and the prototypes. So the first phase also sets up the
  project. I proposed 13 vertical-slice phases mapped to the PRD's 99 user
  stories. After the merges, wrote `plans/one-more-chapter.md` with 11
  phases:
  1. Project foundation and landing page
  2. Accounts and a protected empty shelf
  3. Open Library search (read-only)
  4. Save from search and list books on My Shelf
  5. Shelf browsing
  6. Book detail and editing
  7. Notes
  8. Profile, sharing, and public shared shelf
  9. API read access with tokens
  10. API entry writes
  11. API notes, public shared API, and throttling

  The plan's header records the durable decisions: stack, apps, config
  variables, models, auth and 404 scoping, Open Library error mapping, the
  HTMX convention, and the URL paths. The PRD didn't fix the paths, so I
  chose them and flagged them for review. Nothing was committed.
- **Deviations:** The user merged two pairs of the 13 proposed phases:
  - share link + public page with share management + display name (old
    8 and 9);
  - API notes with the public shared API + throttling (old 12 and 13).

  I had offered these merges as an option. I also offered two other
  changes that were not taken: splitting the Tailwind/HTMX build tooling
  out of Phase 1, and adding base API throttling earlier. No follow-up
  questions were asked.
- **Sideways:** Nothing went wrong.

## 2026-11-12 — Grilled the One More Chapter design, prototyped two pages, wrote the PRD

### Prompts
1. `/grill-me @docs/project-idea.md`
2. Would fetching extra detail in Option C cause issues with the 1 request
   per second limit from the Open Library API? *(Q1, data model)*
3. Let's go with Option A - no description field *(Q1: shared `Book` +
   per-user `ShelfEntry`)*
4. Option A *(Q2: key on the Open Library work)*
5. Option A, and yes, rating at any status *(Q3: nullable 1–5 rating)*
6. Option B, but without started-on - finished-on is optional *(Q4: dates)*
7. Option B *(Q5: `finished_on` cannot be in the future, allowed at any
   status)*
8. Option B - notes are private to the owner *(Q6: separate `Note`
   model)*
9. Option C - notes are add/delete only *(Q7: full nested notes API)*
10. Option B *(Q8: Session + Token auth)*
11. Option B *(Q9: unguessable, revocable share token)*
12. Option B, field list sounds right *(Q10: shared website page + read-only
    API; no notes)*
13. Is genre included in the fields that we have access to? If so - we
    should add it to the filter by list *(during Q11, browsing)*
14. Option D *(Q11a: no genre)*
15. Option B *(Q11: `django-filter`, one FilterSet shared by the website and
    the API)*
16. Option C - test that the query works *(Q12: server-side save lookup via
    `search.json?q=key:`)*
17. Option B *(Q13: custom exceptions, 503/502/400 mapping)*
18. Option B *(Q14: 10-minute in-memory search cache)*
19. Option B, and yes show "On your shelf" *(Q15: submit-to-search with
    HTMX)*
20. Option B *(Q16: live shelf browsing + HTMX detail page)*
21. Option B and drop Profile *(Q17: custom `User` from day one)*
22. A + C *(Q18: keep orphaned books; duplicates return 400)*
23. Option A, endpoint table looks right *(Q19: `ol_work_key`
    create-only)*
24. What is monkeypatch? *(Q20, testing)*
25. B + C *(Q20: `responses` for the service module, `monkeypatch` for
    views/API)*
26. Option B, and yes vendor HTMX *(Q21: `django-tailwind-cli`)*
27. Option A, yes to the rename and config *(Q22: `accounts` + `shelf`
    apps)*
28. Option B *(Q23: environment variables from `.env` via uv)*
29. Option B *(Q24: DRF throttling on the API)*
30. Option B *(Q25: optional `display_name` on shared shelves)*
31. We still need to discuss the UI of the finished app
32. Option A *(Q26: landing page when logged out, redirect to My Shelf)*
33. `/prototype The most recent question` *(Q27, My Shelf layout)*
34. Option C with A's Currently Reading stip
35. `/prototype Question 28` *(book detail layout)*
36. Option A
37. Option B, reuse the list-row layout *(Q29: split Save button on search
    results)*
38. Option B *(Q30: toasts for success, inline errors)*
39. Option B *(Q31: shared page grouped by status as cover grids)*
40. Option B with the share-link card *(Q32: masked API token)*
41. What does the Search page look like?
42. `/to-prd`
43. Let's confirm the three unconfirmed issues
    - Answered three multiple-choice questions, taking the recommendation
      each time: 20 results per page, cap at page 50, Open Library credit in
      the Search page footer.
44. Append a session log to PROMPTS.md at the repo root, under today's
    date, newest entry at the top. Record every prompt I gave you this
    session, in order, including any corrections. End the entry with a
    short summary: the outcome, any places where I deviated from a
    recommended answer or asked follow-up questions, and anything that went
    sideways.

### Summary
- **Outcome:** A grill-me interview settled 32 design questions plus the
  Search page details, covering:
  - the data model (custom `User` with `share_token`/`display_name`, `Book`,
    `ShelfEntry`, `Note`);
  - the Open Library integration and error handling;
  - API design, auth, and throttling;
  - sharing rules, testing strategy, and tooling;
  - every page's UI.

  Two throwaway UI prototypes (three variants each, DaisyUI Forest, real
  Open Library data) were built in `prototypes/`:
  - `my-shelf-layout.html`, with chosen variant C plus A's Currently
    Reading strip;
  - `book-detail-layout.html`, with chosen variant A.

  The decision is recorded at the top of each file.

  Wrote `prd/one-more-chapter.md` with 99 user stories, implementation
  decisions, out-of-scope items, and notes. Then confirmed the three open
  items and updated the PRD:
  - `django-tailwind-cli` 4.8.2 supports DaisyUI 5 via `tailwind-cli-extra`;
  - `.env` is already git-ignored;
  - the Search page settings.

  Nothing was committed.
- **Deviations:** These answers departed from my recommendation:
  - **Q4:** recommended timestamps only; the user added an optional
    `finished_on` but no `started_on`.
  - **Q6:** recommended a single notes field; the user chose a separate
    `Note` model.
  - **Q7:** recommended no notes API; the user chose a full nested notes
    API (add/delete only).
  - **Q11a:** recommended auto-suggested genre; the user dropped genre
    entirely.
  - **Q27:** recommended the cover grid; after prototyping, the user chose
    the sidebar + list layout with the grid's Currently Reading strip.
  - **Q1:** took the recommendation but declined the optional description
    field.

  All other answers took the recommendation. Follow-up questions:
  - Open Library rate limits under on-demand detail fetching.
  - Whether genre is available. A live request showed the `subject` field
    is too messy to use.
  - What `monkeypatch` is.
  - What the Search page looks like.
  - Prototypes were requested for Q27 and Q28.
- **Sideways:**
  - I declared the interview complete and proposed `/to-prd` before any UI
    had been discussed. The user caught it ("We still need to discuss the
    UI"), and seven UI questions followed.
  - The Search page was never asked about directly, so its details were
    filled in as defaults. The PRD flagged them as unconfirmed until the
    final prompt confirmed them.
  - During the Q12 live test, my first Dune lookup used a wrong work key
    (`OL893415W`) and returned 0 results. A re-test with the real key
    (`OL893414W`) confirmed the query works.
  - The pinned `@tailwindcss/browser@4.0.0` CDN file returned 404, so the
    prototypes use 4.1.11.
  - Node isn't installed, so the prototypes' JavaScript couldn't be
    syntax-checked. Two bugs (cover fallback, mobile filter toggle) were
    fixed by review before handoff. The user was told to report any blank
    variants.
  - The Q27 prototype's variant C (sidebar + list) replaced the grid/list
    toggle originally offered as Option C. This was disclosed when the
    prototype was handed over.
  - Verification turned up a gotcha: DaisyUI 5 ships only light and dark
    themes by default, so Forest needs a project-owned Tailwind source CSS
    file. Added to the PRD.

## 2026-11-11 — Researched book/music APIs, chose Open Library, built a search test script

### Prompts
1. `/research` Find free external APIs for a Django application where users
   search for items, save them, and add their own notes, ratings, or
   progress. Explore the following topics: books and music. Compare
   promising providers using official documentation, including available
   data, free limits, signup requirements, etc.
2. What kind of information is available through the Open Library API that
   my application could display to users?
3. Explain the pros and cons of the Open Library API versus the Google
   Books API
4. `/grill-me` Write a short script to test requests to the Open Library
   API. The script should accept user input, make a meaningful request to
   the Open Library API, clearly display selected results in the console,
   and handle unsuccessful requests and empty results with useful
   messages. This script belongs to a future Django project that will use
   uv.
   - Answered 10 design questions, choosing the recommended option each
     time: `uv init` now; `requests`; keyword search via `/search.json`;
     `input()` prompt; core fields + IDs + cover URL; numbered blocks, top
     5; specific error messages per failure type; `scripts/` with split
     functions; User-Agent contact from an `OPEN_LIBRARY_CONTACT` env var;
     one search per run.
5. yes, build it
6. Please delete the rel.json file - it is left over from the research
   agent
7. Walk me through the process of an API request from start to finish in
   the code - how the request gets made, retrieved, and displayed in the
   console
8. Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways.

### Summary
- **Outcome:** A background agent wrote
  `docs/research/book-and-music-apis.md`, comparing book and music APIs
  with citations to official sources. Picks: Open Library (books) and
  MusicBrainz + Cover Art Archive (music); Spotify, Discogs, and Last.fm
  ruled out over terms and limits. Initialized the uv project
  (`pyproject.toml`, `uv.lock`, `requests` 2.34.2) and built
  `scripts/search_books.py`. It was tested live for success, no results,
  blank input, and cancel. Connection, timeout, 404/429/503, and invalid
  JSON were tested with temporary overrides (fake host, tiny timeout,
  httpbin.org). All behaved as designed. Nothing committed yet.
- **Deviations:** No recommended answers were overridden; all 10
  grill-me answers took the recommendation. Follow-up questions asked:
  what data Open Library offers for display (answered with live requests
  for The Hobbit), Open Library vs Google Books pros and cons, and a
  start-to-finish walkthrough of the request code.
- **Sideways:** The research agent left a stray `rel.json` (a saved
  Discogs API response) at the repo root. It was noticed during the build,
  flagged instead of deleted, and removed once the user confirmed. During
  research, Google Books returned 429 without an API key, and the Discogs
  developer docs and ISBNdb pages blocked the agent, so those findings are
  only partly verified (marked in the research note). Research took about
  21 minutes.