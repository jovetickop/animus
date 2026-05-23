# Format edited C/C++ files after Claude Code write operations.

$inputJson = $input | Out-String

if ($inputJson -notmatch '"file_path"\s*:\s*"([^"]+)"') { exit 0 }
$filePath = $matches[1] -replace '\\\\', '\'

if ($filePath -notmatch '\.(cpp|cc|cxx|c|h|hpp|hxx)$') { exit 0 }

if (Get-Command clang-format -ErrorAction SilentlyContinue) {
    clang-format -i $filePath
    Write-Host "[clang-format] formatted: $filePath"
}
