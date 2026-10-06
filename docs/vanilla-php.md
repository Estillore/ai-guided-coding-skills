# Vanilla PHP navigation and bug path

Use this when the repo is plain PHP: page scripts, `include` / `require`, mixed HTML, and no Laravel/Symfony front controller. Vibe-coded PHP fails when the agent assumes a framework and edits one file it found by name.

## Detect

Treat it as vanilla PHP when most of these are true:

- Many `.php` files render HTML directly.
- Pages call `include` or `require` for config, header, db, and auth.
- There is no `artisan`, `bin/console`, or framework `public/index.php` router.
- `composer.json` is missing, or it only pulls libraries.

Record `framework.name = "vanilla-php"` in the repo-map. Do not invent an MVC layout.

## Navigate by connection, not by file

Reading a whole `.php` file is not a map. A page script is a router made of includes. Follow the call, then read only the lines that call takes.

1. Name the entry: the script the URL, form, or cron actually hits. A file that is only included is not an entry.
2. From that entry, list `include` / `require` in order. That is the chain. Do not open those files yet.
3. From the entry, find the call that matches the symptom (function name, query, `header`, session write). Jump to that definition. Read that function, not the file.
4. One hop only: if that function calls another function or runs SQL, record the callee and the file:line. Stop. The rest of the tree is a directory index.
5. Record the connection, in order: URL or form → entry script → include → function → SQL or redirect.

A search hit on a filename is not a connection. A full-file read that does not name the callee is a failed map.

Write this into `docs/repo-map.json` under `php`:

- `entries`: script paths that are requested
- `shared_includes`: includes used by more than one entry
- `symptom_chain`: ordered includes for the page under repair
- `call`: `entry:line -> include:function:line -> sql-or-redirect`
- `state`: session keys, globals, and request keys that call uses
- `repro`: the exact URL, form, or `php` command that shows the bug


## Interaction is the request

These apps have no JavaScript layer. A form post, a link, or a redirect is the interaction. PHP renders the next page. Do not look for a click handler, a client component, or an API fetch.

- The result is PHP: the SQL, the session write, the `header()` redirect, or the HTML the script prints.
- Evidence is the request and the response page, not a browser bundle.
- Oxlint, React mode, and a frontend file map do not apply. Skip them. A missing `.js` file is not a gap.

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


## Standard for a router app

A `public/index.php` that switches on `?r=` is still vanilla PHP. It is not a license to mix layers.

- Router: one case, include the service, return JSON or require one view. No SQL in the case.
- Service: `src/Modules/<name>/service.php` owns the query and the rule. HTML does not live here.
- View: `views/<name>/*.php` owns markup. No query, no `header()`, no session write.
- A new feature is those three hops, or fewer. Do not add a case that contains the function.
- Do not reread the router. `php-trace --entry public/index.php` and jump to the case. A 30-minute feature is the skill reading the whole switch again.

`AGENTS.md` keeps the trace only. Do not write a new plan JSON for a one-case change.

## Refuse

- Rewriting the app into Laravel or a router as the bugfix.
- Editing every copy of a pasted query. Fix the shared include, or one page if there is no shared owner.
- Claiming the codebase was read because a search hit one filename.
- Reading an entire page or include as the way to understand it. Read the call and the callee.
