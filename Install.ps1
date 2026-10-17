param([Parameter(Mandatory=$true)][string]$ProjectRoot)
$ErrorActionPreference = 'Stop'
$destination = (Resolve-Path -LiteralPath $ProjectRoot).Path
if (-not (Test-Path -LiteralPath (Join-Path $destination 'agent\langgraph'))) {
    throw 'Select the existing Python project root containing agent\langgraph.'
}
$files = @(
    'agent\langgraph\langgraph_agent.py',
    'agent\langgraph\jira_workflow_node.py',
    'integrations\jira\test_case_agent.py',
    'integrations\jira\qa_workflow.py',
    'outputs\jira_drafts\skill_selection_recovery.json'
)
foreach ($relative in $files) {
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $relative))) {
        throw "Package file missing: $relative"
    }
}
$backup = Join-Path $destination ('outputs\update_backups\prompt-agent-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
foreach ($relative in $files) {
    $target = Join-Path $destination $relative
    if (Test-Path -LiteralPath $target) {
        $copy = Join-Path $backup $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $copy) | Out-Null
        Copy-Item -LiteralPath $target -Destination $copy
    }
}
foreach ($relative in $files) {
    $target = Join-Path $destination $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $relative) -Destination $target -Force
}
Write-Host "Installed four Python files and one recovery draft. Backup: $backup"
Write-Host 'Start with: .\.venv\Scripts\python.exe -m agent.langgraph.langgraph_agent'
