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