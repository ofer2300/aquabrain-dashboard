# AquaBrain Software Controller - AutoCAD 2026
# Usage: .\autocad2026.ps1 -Action <open|close|status>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("open", "close", "status")]
    [string]$Action,

    [string]$FilePath = ""
)

$SOFTWARE_NAME = "AutoCAD 2026"
$PROCESS_NAME = "acad"
$EXE_PATH = "C:\Program Files\Autodesk\AutoCAD 2026\acad.exe"

function Get-AutoCADProcess {
    Get-Process -Name $PROCESS_NAME -ErrorAction SilentlyContinue
}

function Get-Status {
    $process = Get-AutoCADProcess
    if ($process) {
        @{
            running = $true
            pid = $process.Id
            window = $process.MainWindowTitle
            software = $SOFTWARE_NAME
        } | ConvertTo-Json
    } else {
        @{
            running = $false
            software = $SOFTWARE_NAME
        } | ConvertTo-Json
    }
}

function Open-Software {
    if (-not (Test-Path $EXE_PATH)) {
        @{ success = $false; error = "$SOFTWARE_NAME not installed at $EXE_PATH" } | ConvertTo-Json
        return
    }

    $existing = Get-AutoCADProcess
    if ($existing) {
        @{ success = $true; message = "$SOFTWARE_NAME already running"; pid = $existing.Id } | ConvertTo-Json
        return
    }

    if ($FilePath -and (Test-Path $FilePath)) {
        $proc = Start-Process -FilePath $EXE_PATH -ArgumentList "/open `"$FilePath`"" -PassThru
    } else {
        $proc = Start-Process -FilePath $EXE_PATH -PassThru
    }

    @{
        success = $true
        message = "$SOFTWARE_NAME started"
        pid = $proc.Id
        file = $FilePath
    } | ConvertTo-Json
}

function Close-Software {
    $process = Get-AutoCADProcess
    if (-not $process) {
        @{ success = $true; message = "$SOFTWARE_NAME not running" } | ConvertTo-Json
        return
    }

    # Try graceful close first
    $process.CloseMainWindow() | Out-Null
    Start-Sleep -Seconds 3

    # Check if still running
    $stillRunning = Get-AutoCADProcess
    if ($stillRunning) {
        $stillRunning | Stop-Process -Force
    }

    @{ success = $true; message = "$SOFTWARE_NAME closed" } | ConvertTo-Json
}

# Execute action
switch ($Action) {
    "open" { Open-Software }
    "close" { Close-Software }
    "status" { Get-Status }
}
