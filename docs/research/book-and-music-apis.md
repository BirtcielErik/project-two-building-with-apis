# Books and Music APIs for a Search, Save, Annotate Django App

Researched 2026-11-11 for CIDM 3312 Project Two. Sources are official docs, terms, and source repos. Anything I could not confirm from a primary source is marked **(unverified)**.

## Summary and recommendation

The app flow is: a user searches an external API, saves an item (we store its stable ID plus a few display fields in our own model), then adds their own notes, rating, or progress in our database. That means we need four things from a provider: a keyless or easy-key search endpoint, a stable ID, a lookup-by-ID endpoint, and terms that allow storing that ID and some metadata.

| Topic | Top pick | Why | Runner-up |
|---|---|---|---|
| Books | **Open Library** (Search + Works/Editions + Covers) | No key or signup. Stable work IDs (`OL27482W`) and edition IDs. Cover URLs built from an ID. The docs *encourage* caching. Tested live and it works. | **Google Books**. Rich metadata, but it needs a Google Cloud API key, and the keyless shared quota returned 429 when I tested. |
| Music | **MusicBrainz + Cover Art Archive** | No key for read-only access. Stable MBIDs. Core data is CC0. Cover art URLs built from an MBID. Tested live and it works. | **iTunes Search API** for fast search and artwork with no key, but Apple restricts artwork use to promoting store content. **Deezer** is keyless and has good covers, but its terms are strictly non-commercial. |

**Avoid for this project:** Spotify. Since Feb 2026, Development Mode requires a Premium account, caps an app at 5 users, and cut several endpoints. Spotify's terms also forbid building databases of its content. Also avoid ISBNdb (paid, unverified), Hardcover (beta, and the token must stay server-side and can delete the owner's account), and Genius (OAuth token required).

**Django gotchas worth designing for now:**
- Send a descriptive `User-Agent` with contact info on every outbound request (Open Library, MusicBrainz, Discogs, Last.fm).
- Keep MusicBrainz at 1 request per second or slower.
- Use Django's cache framework around search calls.
- Store only the external ID and a small display snapshot (title, creator, year, cover URL). User-owned fields (notes, rating, progress) live in your own model.

---

## Books: comparison

| Provider | Data | Auth / signup | Free limits | Caching / storage / attribution | Python client |
|---|---|---|---|---|---|
| **Open Library** | Works, editions, authors, subjects, covers, ISBN lookup | None | 1 req/s anonymous, 3 req/s with an identifying User-Agent ([1]). Covers: 100 req per IP per 5 min for ISBN/OCLC/LCCN keys; cover ID and OLID keys are exempt ([2]) | "Cache responses whenever possible" ([1]). No bulk downloads through the API. Courtesy link back requested for covers ([2]) | None official; use `requests` |
| **Google Books** | Volumes (title, authors, description, pageCount, categories, `imageLinks`, ISBNs), user bookshelves | API key (Google Cloud) for public data; OAuth for user shelves ([4]) | Quota tied to your project; number not stated on the docs pages I read ([4], [5]). Keyless calls hit a shared exhausted quota (live test) | You "may not charge users any fee" without Google's permission; must remove allegedly infringing content on request ([3]) | `google-api-python-client`, or plain `requests` |
| **Hardcover** | Books, editions, authors, series; GraphQL | Account plus personal API token ([6]) | Daily, per-minute, and burst limits shown on your account page ([6]) | Beta: "Anything you build using it could break". Token must not run in the browser. Public sites may not use user-owned data (reviews, ratings, lists) ([6]) | None; GraphQL over `requests` |
| **Gutendex** (third-party, Project Gutenberg metadata) | Public-domain ebooks, authors, subjects, download links | None | None stated; site recommends self-hosting for long-term use ([7]) | PG catalog data is public domain ([8]) | None |
| **NYT Books API** | Bestseller lists, reviews (no general catalog search) | API key (signup) ([9]) | 1,000 req/day per the official spec repo, which may be out of date ([9]) | Terms not read (portal unreachable) **(unverified)** | None |
| **ISBNdb** | ISBN metadata | Paid key | **Unverified.** All isbndb.com pages returned 403 to me | — | — |

## Music: comparison

| Provider | Data | Auth / signup | Free limits | Caching / storage / attribution | Python client |
|---|---|---|---|---|---|
| **MusicBrainz** | Artists, release groups (albums), releases, recordings, labels, works | None for reads. OAuth only for submissions and user data ([10]) | **1 req/s per IP**, otherwise HTTP 503. Meaningful User-Agent required ([11]) | Core data CC0. Supplementary data CC BY-NC-SA 3.0 ([12]). "Non-commercial use of this web service is free" ([10]) | `musicbrainzngs` 0.7.1 (last release Jan 2020) ([13]) |
| **Cover Art Archive** | Front/back cover images for releases and release groups | None ([14]) | "No rate limiting rules in place", though endpoints list a 503 for rate limits ([14]) | License not stated on the API page **(unverified)** | via `musicbrainzngs` |
| **iTunes Search API** | Albums, tracks, artists, artwork, prices, preview URLs | None ([15]) | ~20 calls/min ([15]) | Large sites should cache. Artwork may be used "only to promote store content", next to a store badge ([15]) | None; `requests` |
| **Deezer** | Albums, artists, tracks, covers up to 1000px, UPC | None for public endpoints (live test) | Not stated on the pages I read **(unverified)** | Terms: use is "strictly limited for a non-commercial purpose" ([16]) | None official |
| **Discogs** | Releases, masters, artists, labels, tracklists, credits, barcodes | Key/secret or token. Search worked without auth in my test (see verified list) | Observed `X-Discogs-Ratelimit: 25` per minute unauthenticated. 60/min authenticated is **unverified** (docs page 403) | Content must be no more than 6 h older than Discogs's own data. No caching or storage "longer than is necessary". Required notices ([17]) | `python3-discogs-client` 2.10 (Sep 2026) |
| **Last.fm** | Albums, artists, tracks, tags, play counts, images | API key (account signup) ([18], [19]) | Unspecified. "Several calls per second" continuously risks suspension ([19]) | Non-commercial only. Cache per HTTP headers. 100 MB usage cap. Must credit and link Last.fm ([20]) | `pylast` 7.2.0 (Sep 2026) |
| **ListenBrainz** | Listening stats and history, keyed by MBIDs | User token only for user data ([21]) | Rate-limit headers on every response ([21]) | — | `liblistenbrainz` (not checked) |
| **TheAudioDB** | Artist/album bios, artwork, genres, moods | Shared free key `123` ([22]) | Free: 30 req/min ([22]) | — | None |
| **Spotify Web API** | Search, albums, tracks, artists | OAuth client credentials. Owner needs Premium (dev mode) ([24]) | Quota per developer account ([25]) | No databases of Spotify content. No indefinite storage ([26]) | `spotipy` 2.26.0 |
| **Genius** | Song/annotation metadata | Access token required (live 401) | **Unverified** (docs unreachable) | — | — |

---

## Per-provider notes

### Open Library (books top pick)

- **Search:** `GET https://openlibrary.org/search.json?q=...`, with `title=`/`author=`, `fields=`, `limit`, `page`, `sort`. Use `fields=` to keep responses small; `fields=*` is "expensive" ([23]).
- **Stable IDs:** work key (`/works/OL27482W`), edition key (`/books/OL...M`), author key (`/authors/OL...A`). Get JSON for any of them by adding `.json` ([1]). Note: the search schema "is not guaranteed to be stable" ([23]).
- **Detail:** `GET https://openlibrary.org/works/{OLID}.json` returns description, subjects, covers, and authors (live test).
- **Covers:** `https://covers.openlibrary.org/b/{id|olid|isbn}/{value}-{S|M|L}.jpg`. Add `?default=false` to get a 404 instead of a blank image. Use cover IDs or OLIDs; ISBN lookups are rate limited (100 per IP per 5 min) ([2]).
- **Rules:** identify yourself in the User-Agent with app name and email. Do not bulk download (use the monthly dumps). The service is not meant as "high-traffic commercial infrastructure" ([1]). The Internet Archive "does not assert any new copyright" over the data ([27]).
- **Django model fit:** `Book(ol_work_key unique, title, author_names, first_publish_year, cover_id)` plus a `UserBook(user, book, status, rating, notes, progress)`.

### Google Books (books runner-up)

- `GET https://www.googleapis.com/books/v1/volumes?q=...&key=...`. `maxResults` defaults to 10, maximum 40. The volume `id` (e.g. `_LettPDhwR0C`) is stable. `volumeInfo.imageLinks` has thumbnails ([4]).
- Public data requires an API key or an OAuth token. "My Library" shelves need OAuth with scope `https://www.googleapis.com/auth/books` ([4]).
- Terms: you may not charge users a fee for the app, and you must take down infringing content on request ([3]). The page also defers to the general Google APIs ToS, which I did not read.

### Hardcover

- GraphQL at `api.hardcover.app/v1/graphql`. You create a token in account settings. Calling it with no token returned 400 (live).
- The API is in beta, and "we may reset tokens without notice". Queries "are not allowed to run in the browser". Search queries time out at 2 s. The 2026 roadmap lists OAuth support and a query depth limit of 3 ([6]).
- Public or commercial sites "may not use data owned by users" such as ratings and reviews. You need a DMCA policy if you show their user-uploaded images ([6]).
- Verdict: too unstable for a graded project.

### Gutendex / Project Gutenberg

- `GET https://gutendex.com/books/?search=...` and `/books/{id}`. Returns title, authors, subjects, summaries, `formats` (download URLs), and `download_count` ([7]).
- It is a third-party project (github.com/garethbjohnson/gutendex), not run by Project Gutenberg. It asks long-term users to self-host ([7]).
- gutenberg.org itself is "intended for human users only". Use the public-domain catalog feed instead of scraping ([8]).
- Good if the app is scoped to public-domain reading with progress tracking.

### NYT Books API

- Bestseller lists and reviews by ISBN, title, or author. It has no catalog search, so it is not a primary source for this app. It is a nice add-on ("on the NYT list" badge). Key required, 1,000 req/day ([9]).

### MusicBrainz + Cover Art Archive (music top pick)

- **Root:** `https://musicbrainz.org/ws/2/`. Search with `/{entity}?query=...&fmt=json`. Look up with `/{entity}/{MBID}?inc=...`. Browse is also available ([10]).
- **Entity to save:** use the `release-group` as the "album" (a release is one specific pressing). For songs, use `recording`.
- **Rate limit:** about 1 req/s per IP. Going over gets every request declined with 503 until you slow down ([11]). The User-Agent format is `AppName/version ( contact-email )`. Generic agents like `python-urllib` are throttled ([11]). In Django, put a throttle or sleep in a service module and cache search results.
- **License:** core data CC0. Supplementary data (e.g. tags, ratings) CC BY-NC-SA 3.0 ([12]).
- **Cover Art Archive:** `https://coverartarchive.org/release-group/{mbid}/front-250` (also 500 and 1200). No key. Store the MBID and build the URL; there is no need to store the image ([14]).
- **Python:** `musicbrainzngs` 0.7.1 is old (2020) but still the listed binding ([10], [13]). Plain `requests` is fine.

### iTunes Search API

- `https://itunes.apple.com/search?term=...&entity=album` and `/lookup?id=...` (also `upc`, `isbn`). `limit` goes up to 200. About 20 calls/min ([15]).
- Returns `collectionId` (stable ID), `artworkUrl100` (you can rewrite it to a larger size), and genre and release date (live).
- Restriction: album art may be used only to promote store content, beside a "Download on iTunes" badge, and Apple can demand removal ([15]). That is a poor fit for a personal-notes app, so treat it as secondary.

### Deezer

- `https://api.deezer.com/search/album?q=...` and `/album/{id}` work without a key (live). They return `cover_small` through `cover_xl` (1000px) and `upc`.
- Terms: "strictly limited for a non-commercial purpose", plus trademark guidelines ([16]). Fine for coursework. Rate limits not confirmed.

### Discogs

- Very detailed release data (credits, pressings, barcodes). Required notices are "This application uses Discogs' API but is not affiliated with..." and "Data provided by Discogs." with a link next to the data ([17]).
- Storage rule: you may not display content "more than six (6) hours older" than Discogs, nor "cache or store the Content longer than is necessary" ([17]). This conflicts with saving item snapshots. Store only the ID and refetch.
- Images are "Restricted Data" ([17]). The image URL auth requirement is **(unverified)** because the developer docs were blocked (403).

### Last.fm

- `album.search`, `track.search`, and `artist.search` need only `api_key`, with no user auth ([19]). Calling without a key returned "missing a required parameter" (live).
- Terms: non-commercial use only (§3.1). Cache according to HTTP headers. 100 MB usage cap (§4.3.4). "Powered by AudioScrobbler" credit and link required (§2.7) ([20]).

### ListenBrainz, TheAudioDB, Genius

- **ListenBrainz:** listening stats keyed by MBIDs. It returns rate-limit headers ([21]). Public stats worked without a token (live). Useful only as a "popular now" add-on to MusicBrainz.
- **TheAudioDB:** free key `123`, 30 req/min. Many methods are limited on the free tier ([22]). Artist search worked (live). Possibly useful for artist bios and fan art.
- **Genius:** search returned 401 "requires an access_token" (live). Docs were unreachable, so it is excluded.

### Spotify Web API: restricted, not recommended

- **Nov 27, 2024:** new apps lost access to recommendations, related artists, audio features and analysis, featured and category playlists, preview URLs in multi-get responses, and algorithmic and editorial playlists ([28]).
- **Apr 15, 2025:** Spotify changed the criteria for extended (production) access ([29]). I did not read the post; the details are **(unverified)**.
- **Feb 11, 2026 (new apps) / Mar 9, 2026 (existing apps):** Development Mode requires the owner to have Premium, allows 1 Client ID, and caps each app at 5 users ([24]).
  - Batch `GET /albums` and `GET /tracks` were removed; use single lookups.
  - Search `limit` maximum dropped from 50 to 10 (default from 20 to 5).
  - The `popularity`, `label`, and `available_markets` fields were removed.
  - Spotify's own search summary says the endpoint cut for existing apps was later postponed **(unverified, not read in the post)**.
- **Jul 23, 2026:** limit raised to 25 Client IDs. Quota is now pooled per developer account. 429 responses include `"reason": "QUOTA_EXCEEDED"` ([25]).
- **Terms:** "you may not store, aggregate or create compilations or databases of Spotify Content". "Do not store Spotify Content indefinitely". No ML training ([26]).
- **Conclusion:** the 5-user cap, the Premium requirement, and the storage terms make Spotify a poor fit.

---

## Verified by live request (2026-11-11, no keys, from this machine)

| Request | Result |
|---|---|
| `openlibrary.org/search.json?q=the+hobbit&fields=...` | 200. 462 hits. First doc: key, title, author_name, `cover_i: 14627509`, `edition_count: 482`, ISBN list |
| `openlibrary.org/works/OL27482W.json` | 200. The Hobbit work record with description |
| `covers.openlibrary.org/b/id/14627509-M.jpg` | 200 `image/jpeg` |
| `googleapis.com/books/v1/volumes?q=the+hobbit` (no key) | **429 RESOURCE_EXHAUSTED**, "Queries per day" on a shared project, so plan on getting a key |
| `gutendex.com/books/?search=pride prejudice` | 200. 6 results, id 1342 with authors and summaries |
| `musicbrainz.org/ws/2/release-group/?query=...OK Computer...&fmt=json` (custom UA) | 200. MBID `b1392450-e666-3926-a536-22c65f834433`, primary-type Album, artist-credit |
| `coverartarchive.org/release-group/b1392450-.../front-250` | 200 `image/jpeg` (after redirect) |
| `itunes.apple.com/search?term=radiohead+ok+computer&entity=album` | 200. `collectionId 1097861387`, artwork URLs, genre, release date |
| `api.deezer.com/search/album?q=ok computer` and `/album/14879699` | 200. Id, cover_small through cover_xl, UPC |
| `api.discogs.com/database/search?q=ok+computer` (no auth) | **200 with results**, despite search usually being documented as needing auth (docs unreachable to confirm) |
| `api.discogs.com/releases/249504` | 200. Header `x-discogs-ratelimit: 25` |
| `ws.audioscrobbler.com/2.0/?method=album.search` (no key) | Error 6, "missing a required parameter" (api_key) |
| `api.listenbrainz.org/1/stats/sitewide/artists?count=1` | 200. Top artist with `artist_mbid` |
| `theaudiodb.com/api/v1/json/123/search.php?s=coldplay` | 200. Artist record with genre, mood, label |
| `api.hardcover.app/v1/graphql` (no token) | 400 |
| `api.nytimes.com/.../hardcover-fiction.json` (no key) | Fault: API key required |
| `api.isbndb.com/book/...` (no key) | 401 |
| `api.genius.com/search` (no token) | 401, access_token required |

## Open questions / unverified

- **Discogs** developer docs (`discogs.com/developers`) returned 403. Unverified: the authenticated rate limit (60/min is secondhand), whether search officially needs auth, and image URL auth rules. The ToS text above was read directly ([17]).
- **ISBNdb**: free tier or trial status unverified (all pages 403). Treated as paid.
- **NYT**: developer portal unreachable. The 1,000/day figure comes from NYT's own GitHub spec, which shows 2011-era examples and may be stale ([9]).
- **Google Books** default daily quota for a new key: not stated on the pages read.
- **Deezer** rate limit and whether new developer app registration is open: not confirmed.
- **Cover Art Archive** image licensing: not stated on the API page.
- **Spotify**: whether the endpoint cut for existing apps was postponed; the April 2025 extended-access criteria details.
- **Open Library** Terms of Service on archive.org: not read; only the licensing page was read.

## Sources

1. Open Library Developers / API index: https://openlibrary.org/developers/api
2. Open Library Covers API: https://openlibrary.org/dev/docs/api/covers
3. Google Books API Terms: https://developers.google.com/books/terms
4. Google Books, Using the API: https://developers.google.com/books/docs/v1/using
5. Google Books, Getting Started: https://developers.google.com/books/docs/v1/getting_started
6. Hardcover API, Getting Started: https://docs.hardcover.app/api/getting-started/
7. Gutendex: https://gutendex.com/
8. Project Gutenberg robot access policy: https://www.gutenberg.org/policy/robot_access.html
9. NYT public API specs, Books API: https://github.com/nytimes/public_api_specs/blob/master/books_api/books_api.md
10. MusicBrainz API: https://musicbrainz.org/doc/MusicBrainz_API
11. MusicBrainz Rate Limiting: https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting
12. MusicBrainz Data License: https://musicbrainz.org/doc/About/Data_License
13. musicbrainzngs on PyPI: https://pypi.org/project/musicbrainzngs/ (docs: https://python-musicbrainzngs.readthedocs.io/)
14. Cover Art Archive API: https://musicbrainz.org/doc/Cover_Art_Archive/API
15. Apple iTunes Search API: https://performance-partners.apple.com/search-api
16. Deezer for Developers, Terms of use: https://developers.deezer.com/termsofuse (API index: https://developers.deezer.com/api)
17. Discogs API Terms of Use: https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use
18. Last.fm album.search: https://www.last.fm/api/show/album.search
19. Last.fm API intro: https://www.last.fm/api/intro
20. Last.fm API Terms of Service: https://www.last.fm/api/tos
21. ListenBrainz API docs: https://listenbrainz.readthedocs.io/en/latest/users/api/index.html
22. TheAudioDB Free Music API: https://www.theaudiodb.com/free_music_api
23. Open Library Search API: https://openlibrary.org/dev/docs/api/search
24. Spotify February 2026 migration guide: https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide
25. Spotify, Web API quota updates (2026-07-23): https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates
26. Spotify Developer Terms: https://developer.spotify.com/terms
27. Open Library licensing: https://openlibrary.org/developers/licensing
28. Spotify, Changes to the Web API (2024-11-27): https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api
29. Spotify, Updating the Criteria for Web API Extended Access (2025-04-15): https://developer.spotify.com/blog/2025-04-15-updating-the-criteria-for-web-api-extended-access

Python client versions are from the PyPI JSON API on 2026-11-11: pylast 7.2.0, python3-discogs-client 2.10, spotipy 2.26.0.
