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
$Agent = Join-Path $Root "agents\guided.json"
$Steering = Join-Path $Root "steering\ponytail.md"

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
    if (Test-Path $Agent) { Copy-Item -Path $Agent -Destination $kiroAgents -Force }
    if (Test-Path $Steering) { Copy-Item -Path $Steering -Destination $kiroSteering -Force }

    Write-Host "OK  Kiro     -> $kiroSkills"
    Write-Host "    agent    -> $kiroAgents\guided.json"
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
    Write-Host "OK  OpenCode -> $dest"
}

function Install-Zed {
    # Agent Skills open standard (Zed + also read by OpenCode)
    $dest = Join-Path $HOME ".agents\skills"
    Copy-SkillsTo $dest
    Write-Host "OK  Zed      -> $dest  (Agent Skills standard)"
}

Write-Host "Installing guided skills (target: $Target)..."
Write-Host ""

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
Write-Host "Done. Restart your tool (or open a new chat), then run: /guided-coding"
