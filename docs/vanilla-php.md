# Vanilla PHP navigation and bug path

Use this when the repo is plain PHP: page scripts, `include` / `require`, mixed HTML, and no Laravel/Symfony front controller. Vibe-coded PHP fails when the agent assumes a framework and edits one file it found by name.

## Detect

Treat it as vanilla PHP when most of these are true:

- Many `.php` files render HTML directly.
- Pages call `include` or `require` for config, header, db, and auth.
- There is no `artisan`, `bin/console`, or framework `public/index.php` router.
- `composer.json` is missing, or it only pulls libraries.

Record `framework.name = "vanilla-php"` in the repo-map. Do not invent an MVC layout.

## Navigate the whole codebase without reading every file

Build a page map, not a tour.

1. Entry scripts: `.php` files that are requested (pages, `ajax/`, `admin/`, cron, CLI). A file that is only included is not an entry.
2. Shared includes: files required by many entries (`config.php`, `db.php`, `auth.php`, `header.php`, `functions.php`).
3. For the symptom page only, list the include chain in order, one hop into each shared include.
4. Record request keys (`$_GET`, `$_POST`, `$_SESSION`), the query that writes, and the redirect or HTML that answers.

Stop the map there. The rest of the tree is a directory index, not required reading.

Write this into `docs/repo-map.json` under `php`:

- `entries`: script paths
- `shared_includes`: paths included from more than one entry
- `symptom_chain`: ordered includes for the page under repair
- `state`: session keys, globals, and config constants the chain uses
- `repro`: the exact URL, form, or `php` command that shows the bug

## Bug path

1. Reproduce on the entry script. A white screen is still a result: check `php -l` on the chain, then the last include that ran.
2. Walk the chain in include order. The bug is usually in the shared include, not the page that rendered the symptom.
3. Prefer the smallest fix in the file that owns the behavior. Do not move the page to a framework.
4. Common owners, check before rewriting:
   - wrong relative `include` after a directory change
   - `session_start()` missing or called after output
   - headers already sent
   - undefined index / missing `$_POST` key
   - SQL built by concatenation in the page
   - a function declared again because a file is included twice
   - `display_errors` off, so the failure is a blank page
5. Evidence is `php -l` on each touched file plus the repro command. If the repo has no PHPUnit suite, a small `php` assertion script under `tests/` is enough. Do not block on a new framework test harness.

## Refuse

- Rewriting the app into Laravel or a router as the bugfix.
- Editing every copy of a pasted query. Fix the shared include, or one page if there is no shared owner.
- Claiming the codebase was read because a search hit one filename.
