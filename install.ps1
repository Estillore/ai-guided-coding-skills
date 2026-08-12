# Install AI Guided Coding Skills (Windows)
# Usage:
#   .\install.ps1              # both Kiro + Grok
#   .\install.ps1 -Target kiro
#   .\install.ps1 -Target grok
#   .\install.ps1 -Target both

param(
    [ValidateSet("kiro", "grok", "both")]
    [string]$Target = "both"
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

function Install-Kiro {
    $kiroSkills = Join-Path $HOME ".kiro\skills"
    $kiroAgents = Join-Path $HOME ".kiro\agents"
    $kiroSteering = Join-Path $HOME ".kiro\steering"

    New-Item -ItemType Directory -Force -Path $kiroSkills, $kiroAgents, $kiroSteering | Out-Null
    Copy-Item -Path (Join-Path $Skills "*") -Destination $kiroSkills -Recurse -Force
    if (Test-Path $Agent) { Copy-Item -Path $Agent -Destination $kiroAgents -Force }
    if (Test-Path $Steering) { Copy-Item -Path $Steering -Destination $kiroSteering -Force }

    Write-Host "OK  Kiro  -> $kiroSkills"
    Write-Host "    agent -> $kiroAgents\guided.json"
    Write-Host "    steer -> $kiroSteering\ponytail.md"
}

function Install-Grok {
    $grokSkills = Join-Path $HOME ".grok\skills"
    New-Item -ItemType Directory -Force -Path $grokSkills | Out-Null
    Copy-Item -Path (Join-Path $Skills "*") -Destination $grokSkills -Recurse -Force
    Write-Host "OK  Grok  -> $grokSkills"
}

Write-Host "Installing guided skills (target: $Target)..."
Write-Host ""

switch ($Target) {
    "kiro" { Install-Kiro }
    "grok" { Install-Grok }
    "both" { Install-Kiro; Install-Grok }
}

Write-Host ""
Write-Host "Done. Restart Kiro/Grok (or open a new chat), then run: /guided-coding"
