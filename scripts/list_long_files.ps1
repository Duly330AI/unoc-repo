param(
    [int]$Threshold = 400,
    [string[]]$Paths = @(),
    [string[]]$Extensions = @('.py', '.ts', '.vue'),
    [string]$AllowListFile = ''
)

if (-not $Paths -or $Paths.Count -eq 0) {
    $backendPath = Join-Path (Join-Path $PSScriptRoot '..') 'backend'
    $frontendPath = Join-Path (Join-Path $PSScriptRoot '..') 'unoc-frontend-v2'
    $frontendPath = Join-Path $frontendPath 'src'
    $Paths = @($backendPath, $frontendPath)
}

# Default allowlist file path if not provided
if (-not $AllowListFile -or $AllowListFile.Trim() -eq '') {
    $AllowListFile = Join-Path $PSScriptRoot 'oversized_allowlist.txt'
}

$all = @()
foreach ($p in $Paths) {
    if (-not (Test-Path $p)) { continue }
    Get-ChildItem -Path $p -Recurse -File | Where-Object { $Extensions -contains ($_.Extension.ToLower()) } | ForEach-Object {
        try {
            $lines = 0
            # Faster line count than loading whole file into memory
            $reader = [System.IO.File]::OpenText($_.FullName)
            while ($null -ne ($reader.ReadLine())) { $lines++ }
            $reader.Close()
            if ($lines -gt $Threshold) {
                $rel = Resolve-Path $_.FullName | ForEach-Object { $_.Path }
                $root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
                # Normalize to repo-root relative with backslashes for consistency
                $rel = $rel.Replace($root + [System.IO.Path]::DirectorySeparatorChar, '')
                $rel = $rel -replace '/', '\\'
                $all += [PSCustomObject]@{ Lines = $lines; Path = $rel }
            }
        }
        catch {
            Write-Warning ("Failed to read {0}: {1}" -f $_.FullName, $_.Exception.Message)
        }
    }
}

if ($all.Count -gt 0) {
    # Load allowlist if present
    $allowed = @()
    if (Test-Path $AllowListFile) {
        try {
            $allowed = Get-Content -Path $AllowListFile |
                ForEach-Object { ($_.Trim() -replace '/', '\\') } |
                Where-Object { $_ -and -not $_.StartsWith('#') }
        } catch {
            Write-Warning ("Failed to read allowlist file {0}: {1}" -f $AllowListFile, $_.Exception.Message)
        }
    }

    # Filter out allowed paths (case-insensitive and normalized)
    $violations = @()
    $allowedListed = @()
    foreach ($item in $all) {
        $p = $item.Path.ToLower()
        $isAllowed = $false
        foreach ($a in $allowed) {
            if ($p -eq $a.ToLower()) { $isAllowed = $true; break }
        }
        if ($isAllowed) { $allowedListed += $item } else { $violations += $item }
    }

    if ($allowedListed.Count -gt 0) {
        Write-Host "Allowed oversized files (allowlist):" -ForegroundColor DarkGray
        foreach ($item in ($allowedListed | Sort-Object Lines -Descending)) {
            $count = ($item.Lines).ToString().PadLeft(5, ' ')
            Write-Host "$count  $($item.Path)" -ForegroundColor DarkGray
        }
        Write-Host ""  # blank line
    }

    if ($violations.Count -gt 0) {
        $violations = $violations | Sort-Object Lines -Descending
        Write-Host "Files over $Threshold lines:`n" -ForegroundColor Yellow
        foreach ($item in $violations) {
            # Right-align line count in 5 chars.
            $count = ($item.Lines).ToString().PadLeft(5, ' ')
            Write-Host "$count  $($item.Path)"
        }
        Write-Host "`nTotal oversized files: $($violations.Count)" -ForegroundColor Yellow
        # Non-zero exit to signal violation in CI/task runners
        exit 1
    } else {
        Write-Host "No files exceed $Threshold lines (after allowlist)." -ForegroundColor Green
        exit 0
    }
}
else {
    Write-Host "No files exceed $Threshold lines." -ForegroundColor Green
    exit 0
}
