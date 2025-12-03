"""
AquaBrain pyRevit Extension Deployer
====================================
Deploys the AquaBrain extension to Revit via pyRevit CLI.

This script:
1. Verifies the extension files exist on Windows filesystem
2. Calls pyRevit CLI to register the extension
3. Attaches pyRevit to Revit 2026

Usage:
    python deploy_extension.py [--attach-only] [--revit-version 2026]

Author: AquaBrain Team
"""

import subprocess
import os
import sys
import json
from pathlib import Path
from typing import Tuple, Optional

# Configuration
EXTENSION_PATH_WINDOWS = r"C:\AquaBrain\Extensions"
EXTENSION_PATH_WSL = "/mnt/c/AquaBrain/Extensions"
EXTENSION_NAME = "AquaBrain"
DEFAULT_REVIT_VERSION = "default"  # Attaches to ALL installed Revit versions

# Common pyRevit CLI paths
PYREVIT_CLI_PATHS = [
    r"C:\Program Files\pyRevit CLI\pyrevit.exe",
    r"C:\Program Files (x86)\pyRevit CLI\pyrevit.exe",
    r"C:\Users\{username}\AppData\Roaming\pyRevit CLI\pyrevit.exe",
    r"C:\pyrevit\pyrevit.exe",
]


def run_powershell(command: str, capture_output: bool = True) -> Tuple[bool, str]:
    """
    Execute a PowerShell command from WSL.

    Args:
        command: PowerShell command to execute
        capture_output: Whether to capture stdout/stderr

    Returns:
        Tuple of (success, output)
    """
    try:
        # Escape quotes for PowerShell
        ps_command = f'powershell.exe -Command "{command}"'

        result = subprocess.run(
            ps_command,
            shell=True,
            capture_output=capture_output,
            text=True,
            timeout=60
        )

        output = result.stdout + result.stderr if capture_output else ""
        success = result.returncode == 0

        return success, output.strip()

    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def find_pyrevit_cli() -> Optional[str]:
    """
    Find the pyRevit CLI executable on Windows.

    Returns:
        Path to pyrevit.exe or None if not found
    """
    print("Searching for pyRevit CLI...")

    # Try common paths
    for path in PYREVIT_CLI_PATHS:
        # Expand username placeholder
        if "{username}" in path:
            success, username = run_powershell("$env:USERNAME")
            if success:
                path = path.replace("{username}", username)

        # Check if file exists
        success, output = run_powershell(f'Test-Path "{path}"')
        if success and "True" in output:
            print(f"  Found: {path}")
            return path

    # Try to find via PATH
    success, output = run_powershell("Get-Command pyrevit -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source")
    if success and output:
        print(f"  Found in PATH: {output}")
        return output

    # Try via where command
    success, output = run_powershell("where.exe pyrevit 2>$null")
    if success and output:
        print(f"  Found via where: {output}")
        return output.split('\n')[0].strip()

    print("  pyRevit CLI not found!")
    return None


def verify_extension_files() -> bool:
    """
    Verify that extension files exist in the Windows filesystem.

    Returns:
        True if all required files exist
    """
    print("\nVerifying extension files...")

    required_files = [
        "AquaBrain.extension/extension.json",
        "AquaBrain.extension/AquaBrain.tab/Automator.panel/Start.pushbutton/script.py",
        "AquaBrain.extension/AquaBrain.tab/Automator.panel/Start.pushbutton/bundle.yaml",
    ]

    all_exist = True
    for file_path in required_files:
        full_path = os.path.join(EXTENSION_PATH_WSL, file_path)
        exists = os.path.exists(full_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path}")
        if not exists:
            all_exist = False

    return all_exist


def register_extension(pyrevit_path: str) -> bool:
    """
    Register the AquaBrain extension with pyRevit.

    Args:
        pyrevit_path: Path to pyrevit.exe

    Returns:
        True if registration successful
    """
    print("\nRegistering extension with pyRevit...")

    # First, check if already registered
    success, output = run_powershell(f'& "{pyrevit_path}" extensions paths')
    if EXTENSION_PATH_WINDOWS in output:
        print("  Extension path already registered.")
        return True

    # Add extension search path
    cmd = f'& "{pyrevit_path}" extensions paths add "{EXTENSION_PATH_WINDOWS}"'
    success, output = run_powershell(cmd)

    if success:
        print("  ✓ Extension path added successfully")
        print(f"    {output}")
        return True
    else:
        print(f"  ✗ Failed to add extension path: {output}")

        # Try alternative method - extend ui
        print("  Trying alternative method...")
        cmd = f'& "{pyrevit_path}" extend ui {EXTENSION_NAME} "{EXTENSION_PATH_WINDOWS}"'
        success, output = run_powershell(cmd)

        if success:
            print("  ✓ Extension registered via 'extend ui'")
            return True
        else:
            print(f"  ✗ Alternative method also failed: {output}")
            return False


def attach_to_revit(pyrevit_path: str, revit_version: str = DEFAULT_REVIT_VERSION) -> bool:
    """
    Attach pyRevit to a specific Revit version.

    Args:
        pyrevit_path: Path to pyrevit.exe
        revit_version: Revit version to attach to

    Returns:
        True if attachment successful
    """
    print(f"\nAttaching pyRevit to Revit {revit_version}...")

    # Check current attachments
    success, output = run_powershell(f'& "{pyrevit_path}" attached')
    print(f"  Current attachments:\n{output}")

    # Check if already attached
    if f"Revit {revit_version}" in output or f"{revit_version}" in output:
        print(f"  ✓ Already attached to Revit {revit_version}")
        return True

    # Attach to Revit
    cmd = f'& "{pyrevit_path}" attach master {revit_version} --installed'
    success, output = run_powershell(cmd)

    if success or "already attached" in output.lower():
        print(f"  ✓ Attached to Revit {revit_version}")
        return True
    else:
        print(f"  ✗ Failed to attach: {output}")

        # Try without --installed flag
        print("  Trying without --installed flag...")
        cmd = f'& "{pyrevit_path}" attach master {revit_version}'
        success, output = run_powershell(cmd)

        if success:
            print(f"  ✓ Attached to Revit {revit_version}")
            return True
        else:
            print(f"  ✗ Still failed: {output}")
            return False


def reload_pyrevit(pyrevit_path: str) -> bool:
    """
    Reload pyRevit in running Revit instances.

    Args:
        pyrevit_path: Path to pyrevit.exe

    Returns:
        True if reload command sent
    """
    print("\nReloading pyRevit...")

    cmd = f'& "{pyrevit_path}" extensions update --all'
    success, output = run_powershell(cmd)

    if success:
        print("  ✓ Extension update triggered")
        return True
    else:
        print(f"  Note: {output}")
        return False


def get_extension_info(pyrevit_path: str) -> None:
    """Print information about installed extensions."""
    print("\nInstalled extensions:")

    success, output = run_powershell(f'& "{pyrevit_path}" extensions')
    if success:
        print(output)
    else:
        print(f"  Could not retrieve extension list: {output}")


def main():
    """Main deployment function."""
    print("=" * 60)
    print("AquaBrain pyRevit Extension Deployer")
    print("=" * 60)

    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="Deploy AquaBrain extension to Revit")
    parser.add_argument("--attach-only", action="store_true", help="Only attach pyRevit, skip registration")
    parser.add_argument("--revit-version", default=DEFAULT_REVIT_VERSION, help="Revit version to attach to")
    parser.add_argument("--info", action="store_true", help="Show extension info and exit")
    args = parser.parse_args()

    # Find pyRevit CLI
    pyrevit_path = find_pyrevit_cli()

    if not pyrevit_path:
        print("\n" + "=" * 60)
        print("ERROR: pyRevit CLI not found!")
        print("=" * 60)
        print("\nPlease install pyRevit CLI from:")
        print("  https://github.com/eirannejad/pyRevit/releases")
        print("\nOr specify the path manually.")
        sys.exit(1)

    # Info only mode
    if args.info:
        get_extension_info(pyrevit_path)
        sys.exit(0)

    # Verify extension files
    if not verify_extension_files():
        print("\n" + "=" * 60)
        print("ERROR: Extension files missing!")
        print("=" * 60)
        print(f"\nExpected path: {EXTENSION_PATH_WSL}")
        sys.exit(1)

    # Register extension (unless attach-only)
    if not args.attach_only:
        if not register_extension(pyrevit_path):
            print("\nWarning: Extension registration had issues, but continuing...")

    # Attach to Revit
    attach_success = attach_to_revit(pyrevit_path, args.revit_version)

    # Reload
    reload_pyrevit(pyrevit_path)

    # Summary
    print("\n" + "=" * 60)
    print("Deployment Summary")
    print("=" * 60)
    print(f"  Extension Path: {EXTENSION_PATH_WINDOWS}")
    print(f"  Revit Version: {args.revit_version}")
    print(f"  Attachment: {'SUCCESS' if attach_success else 'NEEDS MANUAL CHECK'}")
    print("\nNext Steps:")
    print("  1. Open Revit 2026")
    print("  2. Look for 'AquaBrain' tab in the ribbon")
    print("  3. Click 'Auto-Pilot' button to launch")
    print("  4. Make sure AquaBrain backend is running (./start_aquabrain.sh)")
    print("=" * 60)


if __name__ == "__main__":
    main()
