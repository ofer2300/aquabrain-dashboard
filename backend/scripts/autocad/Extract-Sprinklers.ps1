<#
.SYNOPSIS
    AquaBrain AutoCAD Sprinkler Extractor - PowerShell Bridge

.DESCRIPTION
    Bridge script for extracting sprinkler data from DWG files via AutoCAD Core Console.
    Designed to work from WSL/Linux environment calling Windows AutoCAD.

.PARAMETER DwgPath
    Full Windows path to the DWG file

.PARAMETER OutputFormat
    Output format: JSON (default), CSV, or CONSOLE

.PARAMETER OutputDir
    Directory for output files (default: same as DWG)

.EXAMPLE
    .\Extract-Sprinklers.ps1 -DwgPath "C:\Projects\building.dwg" -OutputFormat JSON

.NOTES
    Version: 2.0
    Author: AquaBrain / Claude
    Requires: AutoCAD 2024-2026 with accoreconsole.exe
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$DwgPath,

    [Parameter(Mandatory=$false)]
    [ValidateSet("JSON", "CSV", "CONSOLE")]
    [string]$OutputFormat = "JSON",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "",

    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# ============================================================================
# CONFIGURATION
# ============================================================================

$AUTOCAD_PATHS = @(
    "C:\Program Files\Autodesk\AutoCAD 2026\accoreconsole.exe",
    "C:\Program Files\Autodesk\AutoCAD 2025\accoreconsole.exe",
    "C:\Program Files\Autodesk\AutoCAD 2024\accoreconsole.exe"
)

$SCRIPT_DIR = $PSScriptRoot
$LISP_FILE = Join-Path $SCRIPT_DIR "sprinkler_extractor.lsp"
$TEMP_DIR = "C:\AquaBrain\temp"

# ============================================================================
# FUNCTIONS
# ============================================================================

function Find-AutoCAD {
    foreach ($path in $AUTOCAD_PATHS) {
        if (Test-Path $path) {
            return $path
        }
    }
    throw "AutoCAD Core Console not found. Checked: $($AUTOCAD_PATHS -join ', ')"
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Create-TempScript {
    param(
        [string]$LispPath,
        [string]$OutputPath
    )

    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $scrPath = Join-Path $TEMP_DIR "extract_$timestamp.scr"

    # Escape paths for LISP
    $lispPathEscaped = $LispPath.Replace("\", "/")
    $outputPathEscaped = $OutputPath.Replace("\", "/")

    $scrContent = @"
; AquaBrain Sprinkler Extraction Script
; Generated: $(Get-Date)

; Set output path
(setq *OUTPUT-FILE* "$outputPathEscaped")

; Load extractor
(load "$lispPathEscaped")

; Run extraction
EXTRACTSPRINKLERS

; Exit
QUIT Y
"@

    Set-Content -Path $scrPath -Value $scrContent -Encoding UTF8
    return $scrPath
}

function Run-Extraction {
    param(
        [string]$AcCorePath,
        [string]$DwgPath,
        [string]$ScrPath
    )

    $arguments = @(
        "/i", "`"$DwgPath`"",
        "/s", "`"$ScrPath`"",
        "/l", "en-US"
    )

    Write-Host "Running AutoCAD Core Console..." -ForegroundColor Cyan
    Write-Host "  DWG: $DwgPath" -ForegroundColor Gray
    Write-Host "  Script: $ScrPath" -ForegroundColor Gray

    $process = Start-Process -FilePath $AcCorePath `
                             -ArgumentList $arguments `
                             -Wait `
                             -NoNewWindow `
                             -PassThru `
                             -RedirectStandardOutput "$TEMP_DIR\stdout.txt" `
                             -RedirectStandardError "$TEMP_DIR\stderr.txt"

    return $process.ExitCode
}

function Parse-JsonOutput {
    param([string]$JsonPath)

    if (-not (Test-Path $JsonPath)) {
        throw "Output file not found: $JsonPath"
    }

    $content = Get-Content -Path $JsonPath -Raw -Encoding UTF8
    return $content
}

# ============================================================================
# MAIN
# ============================================================================

try {
    # Banner
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║     AQUABRAIN SPRINKLER EXTRACTOR - PowerShell Bridge        ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""

    # Validate input file
    if (-not (Test-Path $DwgPath)) {
        throw "DWG file not found: $DwgPath"
    }

    # Find AutoCAD
    $acCorePath = Find-AutoCAD
    Write-Host "Found AutoCAD: $acCorePath" -ForegroundColor Green

    # Setup directories
    Ensure-Directory -Path $TEMP_DIR

    # Determine output directory
    if ([string]::IsNullOrEmpty($OutputDir)) {
        $OutputDir = Split-Path $DwgPath -Parent
    }
    Ensure-Directory -Path $OutputDir

    # Determine output file path
    $dwgBaseName = [System.IO.Path]::GetFileNameWithoutExtension($DwgPath)
    $outputJsonPath = Join-Path $OutputDir "$($dwgBaseName)_sprinklers.json"

    # Ensure LISP file exists
    if (-not (Test-Path $LISP_FILE)) {
        throw "LISP extractor not found: $LISP_FILE"
    }

    # Create temp script
    $scrPath = Create-TempScript -LispPath $LISP_FILE -OutputPath $outputJsonPath
    Write-Host "Created temp script: $scrPath" -ForegroundColor Gray

    # Run extraction
    $exitCode = Run-Extraction -AcCorePath $acCorePath -DwgPath $DwgPath -ScrPath $scrPath

    if ($exitCode -ne 0) {
        $stderr = Get-Content "$TEMP_DIR\stderr.txt" -Raw -ErrorAction SilentlyContinue
        Write-Host "AutoCAD exited with code: $exitCode" -ForegroundColor Yellow
        if ($stderr) {
            Write-Host "STDERR: $stderr" -ForegroundColor Red
        }
    }

    # Check for output in DWG directory (LISP writes there)
    $dwgDir = Split-Path $DwgPath -Parent
    $defaultOutput = Join-Path $dwgDir "sprinkler_data.json"

    if (Test-Path $defaultOutput) {
        # Move to expected location if different
        if ($defaultOutput -ne $outputJsonPath) {
            Move-Item -Path $defaultOutput -Destination $outputJsonPath -Force
        }
    }

    # Read and output results
    if (Test-Path $outputJsonPath) {
        $jsonContent = Parse-JsonOutput -JsonPath $outputJsonPath

        switch ($OutputFormat) {
            "JSON" {
                Write-Host ""
                Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
                Write-Host "EXTRACTION RESULTS (JSON):" -ForegroundColor Green
                Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
                Write-Output $jsonContent
            }
            "CSV" {
                $data = $jsonContent | ConvertFrom-Json
                $data | Export-Csv -Path ($outputJsonPath -replace '\.json$', '.csv') -NoTypeInformation
                Write-Host "CSV exported to: $($outputJsonPath -replace '\.json$', '.csv')" -ForegroundColor Green
            }
            "CONSOLE" {
                $data = $jsonContent | ConvertFrom-Json
                Write-Host ""
                Write-Host "Found $($data.Count) sprinklers:" -ForegroundColor Green
                foreach ($spk in $data) {
                    Write-Host "  - $($spk.BlockName) at ($($spk.X), $($spk.Y), $($spk.Z)) K=$($spk.KFactor)" -ForegroundColor Gray
                }
            }
        }

        Write-Host ""
        Write-Host "Output saved to: $outputJsonPath" -ForegroundColor Green

    } else {
        Write-Host "No sprinkler data extracted. Check if DWG contains sprinkler blocks." -ForegroundColor Yellow

        # Output empty array for JSON format
        if ($OutputFormat -eq "JSON") {
            Write-Output "[]"
        }
    }

    # Cleanup temp files
    if (Test-Path $scrPath) { Remove-Item $scrPath -Force }

    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║     EXTRACTION COMPLETE                                       ║" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green

    exit 0

} catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""

    # Output error in JSON format for parsing
    if ($OutputFormat -eq "JSON") {
        $errorJson = @{
            error = $true
            message = $_.Exception.Message
            timestamp = (Get-Date).ToString("o")
        } | ConvertTo-Json
        Write-Output $errorJson
    }

    exit 1
}
