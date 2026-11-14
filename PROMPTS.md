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