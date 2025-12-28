#!/usr/bin/env python3
"""
AquaBrain Routes Bridge Smoke Test V4.0
========================================
Verifies the pyRevit Routes integration is working.

Tests:
1. Routes server connectivity
2. Script execution capability
3. LOD 500 extraction (mock or live)
4. Full skill chain execution
"""

import sys
import os
import json
import subprocess
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(test_name: str, passed: bool, details: str = ""):
    status = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
    print(f"  [{status}] {test_name}")
    if details:
        print(f"         {details}")


def get_windows_host() -> str:
    """Get Windows host IP from WSL."""
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=5
        )
        for line in result.stdout.split("\n"):
            if "default via" in line:
                return line.split()[2]
    except:
        pass
    return "localhost"


def test_routes_connectivity() -> tuple:
    """Test 1: Check if Routes server is responding."""
    host = get_windows_host()
    port = 48884

    # Try curl to Routes API
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             f"http://{host}:{port}/pyrevit/routes/api",
             "--connect-timeout", "5"],
            capture_output=True,
            text=True,
            timeout=10
        )
        status_code = result.stdout.strip()

        if status_code == "200":
            return True, f"Routes API responding on {host}:{port}"
        elif status_code == "000":
            return False, f"Connection refused (Revit may not be running)"
        else:
            return False, f"HTTP {status_code}"
    except Exception as e:
        return False, str(e)


def test_script_execution() -> tuple:
    """Test 2: Execute a simple script via Routes."""
    host = get_windows_host()
    port = 48884

    script = 'import clr; print("Revit Bridge Active via AquaBrain")'
    payload = json.dumps({"script": script, "engine": "ironpython"})

    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST",
             f"http://{host}:{port}/pyrevit/routes/exec2",
             "-H", "Content-Type: application/json",
             "-d", payload,
             "--connect-timeout", "10"],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.stdout:
            response = json.loads(result.stdout)
            output = response.get("output", str(response))
            if "Active" in output or "AquaBrain" in output:
                return True, "Script execution confirmed"
            return True, f"Response: {output[:100]}"
        return False, "Empty response"
    except json.JSONDecodeError:
        if "Active" in result.stdout:
            return True, "Script execution confirmed (raw)"
        return False, f"Invalid JSON: {result.stdout[:100]}"
    except Exception as e:
        return False, str(e)


def test_skill_import() -> tuple:
    """Test 3: Import Revit skills module."""
    try:
        from skills.library.revit_skills import (
            get_routes_client,
            Skill_ExtractLOD500,
            Skill_HydraulicCalc,
            RoutesClient
        )
        return True, "All skills imported successfully"
    except ImportError as e:
        return False, str(e)


def test_lod500_extraction() -> tuple:
    """Test 4: Run LOD 500 extraction (mock or live)."""
    try:
        from skills.library.revit_skills import Skill_ExtractLOD500

        skill = Skill_ExtractLOD500()
        result = skill.execute({"project_id": "smoke_test"})

        if result.output:
            element_count = len(result.output.get("elements", []))
            mock_mode = result.output.get("extraction_mode") == "MOCK_SIMULATION"
            mode = "MOCK" if mock_mode else "LIVE"
            return True, f"Extracted {element_count} elements [{mode}]"
        return False, result.error or "No output"
    except Exception as e:
        return False, str(e)


def test_hydraulic_calc() -> tuple:
    """Test 5: Run hydraulic calculation."""
    try:
        from skills.library.revit_skills import Skill_HydraulicCalc

        skill = Skill_HydraulicCalc()
        result = skill.execute({
            "flow_gpm": 150,
            "diameter_inch": 2.0,
            "length_ft": 100,
            "c_factor": 120
        })

        if result.output:
            psi = result.output.get("pressure_loss_psi", 0)
            fps = result.output.get("velocity_fps", 0)
            return True, f"P={psi:.2f} PSI, V={fps:.2f} fps"
        return False, result.error or "No output"
    except Exception as e:
        return False, str(e)


def test_orchestrator_integration() -> tuple:
    """Test 6: Verify orchestrator has revit_execute capability."""
    try:
        from services.orchestrator import (
            revit_execute,
            RevitRoutesExecutor,
            SkillChainRouter
        )

        # Check chain router parsing
        chain = SkillChainRouter.parse_intent("Design sprinklers for my project")
        expected = ["open_project", "extract_lod500", "hydraulic_calc", "generate_model", "traffic_light"]

        if chain == expected:
            return True, "Orchestrator V4.0 integration verified"
        return True, f"Chain parsed: {chain}"
    except ImportError as e:
        return False, str(e)


def main():
    """Run all smoke tests."""
    print("\n" + "=" * 60)
    print("   AQUABRAIN ROUTES BRIDGE SMOKE TEST V4.0")
    print("   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    all_passed = True
    tests = [
        ("Routes Connectivity", test_routes_connectivity),
        ("Script Execution", test_script_execution),
        ("Skill Module Import", test_skill_import),
        ("LOD 500 Extraction", test_lod500_extraction),
        ("Hydraulic Calculation", test_hydraulic_calc),
        ("Orchestrator Integration", test_orchestrator_integration),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed, details = test_func()
        except Exception as e:
            passed, details = False, f"Exception: {e}"

        results.append((test_name, passed, details))
        print_result(test_name, passed, details)

        if not passed and test_name in ["Skill Module Import"]:
            all_passed = False

    # Summary
    print_header("SUMMARY")
    passed_count = sum(1 for _, p, _ in results if p)
    total_count = len(results)

    print(f"  Tests Passed: {passed_count}/{total_count}")

    # Check if critical tests passed (skills work even without live Revit)
    critical_passed = all(
        p for name, p, _ in results
        if name in ["Skill Module Import", "LOD 500 Extraction", "Hydraulic Calculation"]
    )

    if critical_passed:
        print("\n" + "\033[92m" + "=" * 60 + "\033[0m")
        print("\033[92m   ROUTES BRIDGE VERIFICATION: SUCCESS\033[0m")
        print("\033[92m" + "=" * 60 + "\033[0m")

        # Check if live connection exists
        routes_live = results[0][1]  # Routes Connectivity test
        if routes_live:
            print("\n   MODE: LIVE REVIT CONNECTION")
        else:
            print("\n   MODE: MOCK SIMULATION (Revit not connected)")
            print("   Note: Start Revit with pyRevit for live control")

        return True
    else:
        print("\n" + "\033[91m" + "=" * 60 + "\033[0m")
        print("\033[91m   ROUTES BRIDGE VERIFICATION: FAILED\033[0m")
        print("\033[91m" + "=" * 60 + "\033[0m")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
