# Install AI Guided Coding Skills (Windows)
# Usage:
#   .\install.ps1                 # all tools (kiro + grok + opencode + zed)
#   .\install.ps1 -Target all
#   .\install.ps1 -Target kiro
#   .\install.ps1 -Target grok
#   .\install.ps1 -Target opencode
#   .\install.ps1 -Target zed
#   .\install.ps1 -Target both    # kiro + grok only (legacy)

param(
    [ValidateSet("kiro", "grok", "opencode", "zed", "both", "all")]
    [string]$Target = "all"
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
if (-not $Root) { $Root = Get-Location }

$Skills = Join-Path $Root "skills"
$Scripts = Join-Path $Root "scripts"
$AgentsDir = Join-Path $Root "agents"
$Steering = Join-Path $Root "steering\ponytail.md"
$ZedProfiles = Join-Path $Root "agents\zed\profiles.snippet.jsonc"

if (-not (Test-Path $Skills)) {
    Write-Error "skills/ not found. Run this script from the ai-guided-coding-skills repo."
}

function Copy-SkillsTo {
    param([string]$Dest)
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    Copy-Item -Path (Join-Path $Skills "*") -Destination $Dest -Recurse -Force
}

function Install-Kiro {
    $kiroSkills = Join-Path $HOME ".kiro\skills"
    $kiroAgents = Join-Path $HOME ".kiro\agents"
    $kiroSteering = Join-Path $HOME ".kiro\steering"

    New-Item -ItemType Directory -Force -Path $kiroSkills, $kiroAgents, $kiroSteering | Out-Null
    Copy-SkillsTo $kiroSkills
    if (Test-Path $AgentsDir) { Copy-Item -Path (Join-Path $AgentsDir "*.json") -Destination $kiroAgents -Force }
    if (Test-Path $Steering) { Copy-Item -Path $Steering -Destination $kiroSteering -Force }

    Write-Host "OK  Kiro     -> $kiroSkills"
    Write-Host "    agents   -> $kiroAgents\guided*.json"
    Write-Host "    steering -> $kiroSteering\ponytail.md"
}

function Install-Grok {
    $dest = Join-Path $HOME ".grok\skills"
    Copy-SkillsTo $dest
    Write-Host "OK  Grok     -> $dest"
}

function Install-OpenCode {
    # Native OpenCode global path (Windows uses ~/.config/opencode)
    $dest = Join-Path $HOME ".config\opencode\skills"
    Copy-SkillsTo $dest
    $srcAgents = Join-Path $Root "agents\opencode"
    $destAgents = Join-Path $HOME ".config\opencode\agent"
    if (Test-Path $srcAgents) {
        New-Item -ItemType Directory -Force -Path $destAgents | Out-Null
        Copy-Item -Path (Join-Path $srcAgents "*.md") -Destination $destAgents -Force
        $retired = Join-Path $destAgents "guided-tdd.md"
        if (Test-Path $retired) { Remove-Item -Force $retired }
    }
    Write-Host "OK  OpenCode -> $dest"
    Write-Host "    agents   -> $destAgents\guided-*.md"
}

function Install-Zed {
    # Agent Skills open standard (Zed + also read by OpenCode)
    $dest = Join-Path $HOME ".agents\skills"
    Copy-SkillsTo $dest
    Write-Host "OK  Zed      -> $dest  (Agent Skills standard)"
    if (Test-Path $ZedProfiles) {
        Write-Host "    profiles -> $ZedProfiles"
        Write-Host "               paste into Zed settings (agent.profiles), then restart Zed"
    }
}

Write-Host "Installing guided skills (target: $Target)..."
Write-Host ""

$GuidedHome = Join-Path $HOME ".guided\scripts"
if (Test-Path $Scripts) {
    New-Item -ItemType Directory -Force -Path $GuidedHome | Out-Null
    Copy-Item -Path (Join-Path $Scripts "*") -Destination $GuidedHome -Recurse -Force
    Write-Host "OK  Harness  -> $GuidedHome (guided_run.py)"
    Write-Host ""
}

$Mcp = Join-Path $Root "mcp"
$GuidedMcp = Join-Path $HOME ".guided\mcp"
if (Test-Path $Mcp) {
    New-Item -ItemType Directory -Force -Path $GuidedMcp | Out-Null
    Copy-Item -Path (Join-Path $Mcp "*") -Destination $GuidedMcp -Recurse -Force
    Write-Host "OK  MCP refs -> $GuidedMcp (snippets disabled-by-default; paste to enable)"
    Write-Host ""
}

switch ($Target) {
    "kiro"     { Install-Kiro }
    "grok"     { Install-Grok }
    "opencode" { Install-OpenCode }
    "zed"      { Install-Zed }
    "both"     { Install-Kiro; Install-Grok }
    "all"      {
        Install-Kiro
        Install-Grok
        Install-OpenCode
        Install-Zed
    }
}

Write-Host ""
Write-Host "Verifying installed skills against skills\ ..."
$Verify = Join-Path $GuidedHome "guided_run.py"
$Drift = $false
if (-not (Test-Path $Verify)) {
    Write-Host "SKIP  harness missing at $Verify. Run: python ~/.guided/scripts/guided_run.py sync --check"
} elseif (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "SKIP  python not on PATH. Run: python ~/.guided/scripts/guided_run.py sync --check"
} else {
    # Capture then echo: native stdout and Write-Host interleave out of order,
    # which would print "Done" before its own evidence.
    $out = & python $Verify record-install --repo $Root 2>&1
    $rc = $LASTEXITCODE
    $out | ForEach-Object { Write-Host $_ }
    if ($rc -ne 0) { $Drift = $true }
    $out = & python $Verify sync --check --repo $Root 2>&1
    $rc = $LASTEXITCODE
    $out | ForEach-Object { Write-Host $_ }
    if ($rc -ne 0) { $Drift = $true }
}

Write-Host ""
if ($Drift) {
    Write-Host "Done, but the sync check FAILED. Fix the cause above (stale skills, or a broken python) and re-run." -ForegroundColor Yellow
    exit 1
}
Write-Host "Done. Restart your tool (or open a new chat), then run: /guided-coding"
