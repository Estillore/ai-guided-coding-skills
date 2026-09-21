# Guided PHP MCPs — install + enable

Interactive channel for PHP auditing. MCP output is a **lead, never evidence**:
gates stay in the `php-audit` harness lane (receipts, blocking, baselines).

## Install the servers (once per machine, manual — never silent)

```sh
# 1. PHPStan MCP (vanilla + framework). Pure PHP, zero deps. Needs PHP 8.1+.
git clone https://github.com/larspohlmann/mcp-phpstan-server.git ~/.guided/mcp/mcp-phpstan-server

# 2. PHPCS MCP (vanilla + framework). Pure PHP, zero deps. Needs PHP 8.1+
#    plus phpcs/phpcbf (project vendor/bin or global).
git clone https://github.com/larspohlmann/mcp-phpcs-server.git ~/.guided/mcp/mcp-phpcs-server

# 3. Composer MCP (supply chain). Needs PHP >= 8.4 + Composer.
#    Download php-composer-mcp.phar from
#    https://github.com/baschny/php-composer-mcp/releases
#    to ~/.guided/mcp/php-composer-mcp.phar
#    (or clone the repo and use bin/mcp-server.php after composer install)

# 4. Laravel Boost (Laravel projects only, inside the project itself).
composer require laravel/boost --dev
php artisan boost:install
```

Replace `<GUIDED_MCP>` in the snippets with your absolute `~/.guided/mcp`
path, e.g. `C:/Users/you/.guided/mcp` (forward slashes work on Windows).
`guided_run.py mcp --print-snippet <opencode|kiro|zed|grok>` prints the
same blocks with paths already resolved.

Nothing here auto-registers: these files live under `~/.guided/mcp/` as
reference only, so every server is disabled until you paste + flip its flag.

## Enable per platform (one line each)

- **OpenCode** — merge `opencode.jsonc` under `"mcp"` in `opencode.json`,
  flip `"enabled"` to `true` per server. (OpenCode v2 nests under `"mcp.servers"`.)
- **Kiro** — merge `kiro-mcp.json` into `.kiro/settings/mcp.json`
  (workspace) or `~/.kiro/settings/mcp.json` (user), flip `"disabled"` to `false`.
- **Zed** — paste the `zed-settings.jsonc` block into Settings → Open Settings
  File. Absent = disabled; pasted = enabled.
- **Grok** — merge `grok-mcp.json` into Grok's MCP config per Grok docs
  (standard `mcpServers` shape; verify path for your Grok build).

`laravel-boost` needs `cwd` = the Laravel project root (most clients default
the server cwd to the workspace — open the Laravel project itself), or use an
absolute `artisan` path. Keep it disabled on non-Laravel projects.

## Trust note

These servers execute with your code access. Prefer the zero-dependency,
single-author-readable ones above; pin or re-review on update. Never register
an MCP server you have not read.
