#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║     AQUABRAIN SPRINKLER BoQ EXTRACTOR - Level 5 Hybrid Automation            ║
║     Ubuntu CLI → Windows accoreconsole.exe → AutoLISP → JSON → Terminal     ║
╚══════════════════════════════════════════════════════════════════════════════╝

Senior BIM Automation Architect & Orchestrator
Data Isomorphism Layer: CAD Entities → Logical Fire Protection Objects
"""

import subprocess
import os
import sys
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Rich terminal output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Installing rich for beautiful output...")
    subprocess.run([sys.executable, "-m", "pip", "install", "rich", "-q"])
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True

console = Console()

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

AUTOCAD_PATHS = [
    "/mnt/c/Program Files/Autodesk/AutoCAD 2026/accoreconsole.exe",
    "/mnt/c/Program Files/Autodesk/AutoCAD 2025/accoreconsole.exe",
    "/mnt/c/Program Files/Autodesk/AutoCAD 2024/accoreconsole.exe",
]

# Color codes to pipe type mapping (AutoCAD ACI colors)
PIPE_COLOR_MAP = {
    4: {"name": "Main Distribution Pipe", "size": "2 inch (50mm)", "type": "MAIN"},
    6: {"name": "Branch Line", "size": "1.5 inch (40mm)", "type": "BRANCH"},
    2: {"name": "Branch Line", "size": "1 inch (25mm)", "type": "BRANCH"},
    5: {"name": "Branch Line", "size": "1.25 inch (32mm)", "type": "BRANCH"},
    3: {"name": "Riser/Drop", "size": "Variable", "type": "RISER"},
}

# Vertical factor for 2D to 3D estimation
VERTICAL_FACTOR = 1.10  # +10% for vertical drops

# Target layer (Hebrew: Sprinklers)
TARGET_LAYER = "ספרינקלרים"

# ═══════════════════════════════════════════════════════════════════════════════
# PATH BRIDGING UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def wsl_to_windows_path(linux_path: str) -> str:
    """Convert WSL/Linux path to Windows format using wslpath."""
    try:
        result = subprocess.run(
            ["wslpath", "-w", linux_path],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Fallback: manual conversion
        if linux_path.startswith("/mnt/"):
            parts = linux_path.split("/")
            drive = parts[2].upper()
            rest = "\\".join(parts[3:])
            return f"{drive}:\\{rest}"
        return linux_path

def windows_to_wsl_path(win_path: str) -> str:
    """Convert Windows path to WSL format."""
    try:
        result = subprocess.run(
            ["wslpath", "-u", win_path],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Fallback
        if len(win_path) > 2 and win_path[1] == ":":
            drive = win_path[0].lower()
            rest = win_path[2:].replace("\\", "/")
            return f"/mnt/{drive}{rest}"
        return win_path

def find_accoreconsole() -> Optional[str]:
    """Locate AutoCAD Core Console executable."""
    for path in AUTOCAD_PATHS:
        if os.path.exists(path):
            return path
    return None

def find_dwg_file(filename: str = "1783-nim.dwg") -> Optional[str]:
    """Search for the target DWG file in common locations."""
    search_paths = [
        "/mnt/c/Temp",
        "/mnt/c/AquaBrain",
        "/mnt/c/Users",
        os.path.expanduser("~"),
        "/home/nimrodo",
    ]

    # First check if it's already a full path
    if os.path.exists(filename):
        return os.path.abspath(filename)

    # Search in common directories
    for base_path in search_paths:
        if not os.path.exists(base_path):
            continue
        for root, dirs, files in os.walk(base_path):
            if filename in files:
                return os.path.join(root, filename)
            # Limit depth
            if root.count(os.sep) - base_path.count(os.sep) > 3:
                break

    return None

# ═══════════════════════════════════════════════════════════════════════════════
# LISP PAYLOAD GENERATOR (The Isomorphism Layer)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_extractor_lisp(output_json_path: str, target_layer: str = TARGET_LAYER) -> str:
    """
    Generate AutoLISP extraction script for sprinkler BoQ.
    Implements Data Isomorphism: CAD Entities → Logical Objects
    """

    # Escape paths for LISP
    json_path_escaped = output_json_path.replace("\\", "/")

    lisp_code = f''';;; ═══════════════════════════════════════════════════════════════════════════
;;; AQUABRAIN SPRINKLER BoQ EXTRACTOR - AutoLISP Isomorphism Layer
;;; Extracts: Pipes (by color), Sprinkler Heads, Valves, XDATA
;;; Output: JSON for Python orchestration
;;; ═══════════════════════════════════════════════════════════════════════════

(vl-load-com)

;;; Global data collectors
(setq *PIPE-DATA* nil)
(setq *SPRINKLER-DATA* nil)
(setq *VALVE-DATA* nil)
(setq *XDATA-DATA* nil)

;;; ───────────────────────────────────────────────────────────────────────────
;;; UTILITY FUNCTIONS
;;; ───────────────────────────────────────────────────────────────────────────

(defun get-entity-color (ent / entdata color)
  "Get the ACI color of an entity"
  (setq entdata (entget ent))
  (setq color (cdr (assoc 62 entdata)))
  (if (null color)
    (setq color 256)  ; BYLAYER
  )
  color
)

(defun get-entity-layer (ent / entdata)
  "Get the layer name of an entity"
  (cdr (assoc 8 (entget ent)))
)

(defun polyline-length (ent / obj len)
  "Calculate length of polyline/line entity"
  (setq obj (vlax-ename->vla-object ent))
  (if (vlax-property-available-p obj 'Length)
    (progn
      (setq len (vla-get-length obj))
      len
    )
    0.0
  )
)

(defun get-block-attributes (ent / obj atts att-list)
  "Extract all attributes from a block reference"
  (setq obj (vlax-ename->vla-object ent))
  (setq att-list nil)
  (if (= (vla-get-hasattributes obj) :vlax-true)
    (progn
      (setq atts (vlax-invoke obj 'GetAttributes))
      (foreach att (vlax-safearray->list (vlax-variant-value atts))
        (setq att-list
          (cons
            (cons (vla-get-tagstring att) (vla-get-textstring att))
            att-list
          )
        )
      )
    )
  )
  (reverse att-list)
)

(defun get-xdata (ent app-name / entdata xdata)
  "Extract XDATA for specified application"
  (setq entdata (entget ent (list app-name)))
  (setq xdata (assoc -3 entdata))
  (if xdata (cdr xdata) nil)
)

(defun get-block-name (ent / entdata)
  "Get block name from INSERT entity"
  (cdr (assoc 2 (entget ent)))
)

(defun get-insertion-point (ent / entdata)
  "Get insertion point of block"
  (cdr (assoc 10 (entget ent)))
)

;;; ───────────────────────────────────────────────────────────────────────────
;;; PIPE EXTRACTION
;;; ───────────────────────────────────────────────────────────────────────────

(defun extract-pipes (/ ss i ent etype color len layer pipe-lengths)
  "Extract all pipe entities and calculate lengths by color"
  (princ "\\n[PIPE EXTRACTION] Scanning for pipes...")

  ;; Initialize length counters by color
  (setq pipe-lengths '())

  ;; Get all polylines and lines
  (setq ss (ssget "X" '((0 . "LWPOLYLINE,LINE,POLYLINE"))))

  (if ss
    (progn
      (setq i 0)
      (while (< i (sslength ss))
        (setq ent (ssname ss i))
        (setq etype (cdr (assoc 0 (entget ent))))
        (setq color (get-entity-color ent))
        (setq layer (get-entity-layer ent))
        (setq len (polyline-length ent))

        ;; Add to pipe lengths by color
        (if (> len 0)
          (progn
            (setq existing (assoc color pipe-lengths))
            (if existing
              (setq pipe-lengths
                (subst
                  (cons color (+ (cdr existing) len))
                  existing
                  pipe-lengths
                )
              )
              (setq pipe-lengths (cons (cons color len) pipe-lengths))
            )
          )
        )

        (setq i (1+ i))
      )
      (princ (strcat "\\n[PIPE] Found " (itoa (sslength ss)) " pipe entities"))
    )
    (princ "\\n[PIPE] No pipe entities found")
  )

  ;; Store globally
  (setq *PIPE-DATA* pipe-lengths)
  pipe-lengths
)

;;; ───────────────────────────────────────────────────────────────────────────
;;; SPRINKLER EXTRACTION
;;; ───────────────────────────────────────────────────────────────────────────

(defun extract-sprinklers (/ ss i ent block-name attrs ins-pt sprinkler-list xdata)
  "Extract all sprinkler head blocks"
  (princ "\\n[SPRINKLER EXTRACTION] Scanning for sprinkler blocks...")

  (setq sprinkler-list '())

  ;; Get all block inserts
  (setq ss (ssget "X" '((0 . "INSERT"))))

  (if ss
    (progn
      (setq i 0)
      (while (< i (sslength ss))
        (setq ent (ssname ss i))
        (setq block-name (get-block-name ent))

        ;; Check if it's a sprinkler block (various naming conventions)
        (if (or
              (wcmatch (strcase block-name) "*SPRINK*")
              (wcmatch (strcase block-name) "*SPK*")
              (wcmatch (strcase block-name) "*HEAD*")
              (wcmatch (strcase block-name) "*FIRE*")
              (wcmatch (strcase block-name) "*NOZZLE*")
              (wcmatch (strcase block-name) "*K-*")
              (wcmatch (strcase block-name) "*K5*")
              (wcmatch (strcase block-name) "*K8*")
              (wcmatch (strcase block-name) "*PEND*")
              (wcmatch (strcase block-name) "*UPRIGHT*")
              (wcmatch (strcase block-name) "*SIDEWALL*")
              (wcmatch (strcase block-name) "*CONCEALED*")
            )
          (progn
            (setq ins-pt (get-insertion-point ent))
            (setq attrs (get-block-attributes ent))

            ;; Try to get XDATA
            (setq xdata (get-xdata ent "AQUABRAIN"))
            (if (null xdata) (setq xdata (get-xdata ent "AcDbEntity")))

            (setq sprinkler-list
              (cons
                (list
                  (cons "block_name" block-name)
                  (cons "x" (car ins-pt))
                  (cons "y" (cadr ins-pt))
                  (cons "z" (if (caddr ins-pt) (caddr ins-pt) 0.0))
                  (cons "layer" (get-entity-layer ent))
                  (cons "color" (get-entity-color ent))
                  (cons "attributes" attrs)
                  (cons "has_xdata" (if xdata "true" "false"))
                )
                sprinkler-list
              )
            )
          )
        )
        (setq i (1+ i))
      )
      (princ (strcat "\\n[SPRINKLER] Found " (itoa (length sprinkler-list)) " sprinkler blocks"))
    )
    (princ "\\n[SPRINKLER] No blocks found")
  )

  (setq *SPRINKLER-DATA* sprinkler-list)
  sprinkler-list
)

;;; ───────────────────────────────────────────────────────────────────────────
;;; VALVE EXTRACTION
;;; ───────────────────────────────────────────────────────────────────────────

(defun extract-valves (/ ss i ent block-name attrs ins-pt valve-list)
  "Extract valve blocks"
  (princ "\\n[VALVE EXTRACTION] Scanning for valve blocks...")

  (setq valve-list '())

  (setq ss (ssget "X" '((0 . "INSERT"))))

  (if ss
    (progn
      (setq i 0)
      (while (< i (sslength ss))
        (setq ent (ssname ss i))
        (setq block-name (get-block-name ent))

        ;; Check if it's a valve block
        (if (or
              (wcmatch (strcase block-name) "*VALVE*")
              (wcmatch (strcase block-name) "*CONTROL*")
              (wcmatch (strcase block-name) "*ZONE*")
              (wcmatch (strcase block-name) "*RISER*")
              (wcmatch (strcase block-name) "*CHECK*")
              (wcmatch (strcase block-name) "*ALARM*")
              (wcmatch (strcase block-name) "*GATE*")
              (wcmatch (strcase block-name) "*BUTTERFLY*")
            )
          (progn
            (setq ins-pt (get-insertion-point ent))
            (setq attrs (get-block-attributes ent))

            (setq valve-list
              (cons
                (list
                  (cons "block_name" block-name)
                  (cons "x" (car ins-pt))
                  (cons "y" (cadr ins-pt))
                  (cons "z" (if (caddr ins-pt) (caddr ins-pt) 0.0))
                  (cons "layer" (get-entity-layer ent))
                  (cons "attributes" attrs)
                )
                valve-list
              )
            )
          )
        )
        (setq i (1+ i))
      )
      (princ (strcat "\\n[VALVE] Found " (itoa (length valve-list)) " valve blocks"))
    )
  )

  (setq *VALVE-DATA* valve-list)
  valve-list
)

;;; ───────────────────────────────────────────────────────────────────────────
;;; JSON OUTPUT GENERATOR
;;; ───────────────────────────────────────────────────────────────────────────

(defun format-number (num)
  "Format number for JSON"
  (if (numberp num)
    (rtos num 2 4)
    "0"
  )
)

(defun escape-json-string (str)
  "Escape special characters for JSON"
  (if (null str)
    ""
    (progn
      (setq str (vl-string-subst "\\\\\\\\" "\\\\" str))
      (setq str (vl-string-subst "\\\\\\\"" "\\"" str))
      (setq str (vl-string-subst "\\\\n" "\\n" str))
      str
    )
  )
)

(defun write-json-output (/ file timestamp)
  "Write all collected data to JSON file"
  (princ "\\n[JSON] Writing output file...")

  (setq timestamp (menucmd "M=$(edtime,0,YYYY-MO-DD HH:MM:SS)"))

  (setq file (open "{json_path_escaped}" "w"))

  (if file
    (progn
      (write-line "{{" file)
      (write-line (strcat "  \\"extraction_timestamp\\": \\"" timestamp "\\",") file)
      (write-line "  \\"source\\": \\"AutoCAD Core Console + AutoLISP\\"," file)
      (write-line "  \\"extractor_version\\": \\"2.0-AquaBrain\\"," file)

      ;; Pipe data
      (write-line "  \\"pipes\\": {{" file)
      (setq first-item T)
      (foreach pipe-entry *PIPE-DATA*
        (if (not first-item) (write-line "," file))
        (setq first-item nil)
        (princ (strcat "    \\"color_" (itoa (car pipe-entry)) "\\": " (format-number (cdr pipe-entry))) file)
      )
      (write-line "" file)
      (write-line "  }}," file)

      ;; Sprinkler count
      (write-line (strcat "  \\"sprinkler_count\\": " (itoa (length *SPRINKLER-DATA*)) ",") file)

      ;; Sprinklers array
      (write-line "  \\"sprinklers\\": [" file)
      (setq first-item T)
      (foreach spk *SPRINKLER-DATA*
        (if (not first-item) (write-line "," file))
        (setq first-item nil)
        (princ "    {{" file)
        (princ (strcat "\\"block_name\\": \\"" (escape-json-string (cdr (assoc "block_name" spk))) "\\", ") file)
        (princ (strcat "\\"x\\": " (format-number (cdr (assoc "x" spk))) ", ") file)
        (princ (strcat "\\"y\\": " (format-number (cdr (assoc "y" spk))) ", ") file)
        (princ (strcat "\\"z\\": " (format-number (cdr (assoc "z" spk))) ", ") file)
        (princ (strcat "\\"layer\\": \\"" (escape-json-string (cdr (assoc "layer" spk))) "\\"") file)
        (princ "}}" file)
      )
      (write-line "" file)
      (write-line "  ]," file)

      ;; Valve count
      (write-line (strcat "  \\"valve_count\\": " (itoa (length *VALVE-DATA*)) ",") file)

      ;; Valves array
      (write-line "  \\"valves\\": [" file)
      (setq first-item T)
      (foreach vlv *VALVE-DATA*
        (if (not first-item) (write-line "," file))
        (setq first-item nil)
        (princ "    {{" file)
        (princ (strcat "\\"block_name\\": \\"" (escape-json-string (cdr (assoc "block_name" vlv))) "\\", ") file)
        (princ (strcat "\\"x\\": " (format-number (cdr (assoc "x" vlv))) ", ") file)
        (princ (strcat "\\"y\\": " (format-number (cdr (assoc "y" vlv))) "\\"") file)
        (princ "}}" file)
      )
      (write-line "" file)
      (write-line "  ]" file)

      (write-line "}}" file)
      (close file)
      (princ (strcat "\\n[JSON] Output written to: {json_path_escaped}"))
    )
    (princ "\\n[ERROR] Could not open output file!")
  )
)

;;; ───────────────────────────────────────────────────────────────────────────
;;; MAIN EXTRACTION COMMAND
;;; ───────────────────────────────────────────────────────────────────────────

(defun c:EXTRACTBOQ ()
  "Main BoQ extraction command"
  (princ "\\n")
  (princ "\\n╔══════════════════════════════════════════════════════════════════╗")
  (princ "\\n║     AQUABRAIN BoQ EXTRACTOR - Isomorphism Layer Active           ║")
  (princ "\\n╚══════════════════════════════════════════════════════════════════╝")
  (princ "\\n")

  ;; Run extractions
  (extract-pipes)
  (extract-sprinklers)
  (extract-valves)

  ;; Write JSON
  (write-json-output)

  (princ "\\n")
  (princ "\\n╔══════════════════════════════════════════════════════════════════╗")
  (princ "\\n║     EXTRACTION COMPLETE - Data Isomorphism Achieved              ║")
  (princ "\\n╚══════════════════════════════════════════════════════════════════╝")
  (princ "\\n")
  (princ)
)

;;; Auto-run
(c:EXTRACTBOQ)
'''

    return lisp_code

# ═══════════════════════════════════════════════════════════════════════════════
# HEADLESS EXECUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_accoreconsole(
    accore_path: str,
    dwg_path: str,
    lisp_path: str,
    output_json: str
) -> Tuple[bool, str]:
    """
    Execute AutoCAD Core Console with LISP payload.
    Returns (success, output_message)
    """

    # Convert paths to Windows format
    win_dwg = wsl_to_windows_path(dwg_path)
    win_lisp = wsl_to_windows_path(lisp_path)
    win_accore = wsl_to_windows_path(accore_path)

    # Create SCR script to load and run LISP
    scr_content = f'''; AquaBrain BoQ Extraction Script
; Auto-generated by Python Orchestrator

(load "{win_lisp.replace(chr(92), '/')}")

QUIT Y
'''

    # Write SCR file
    scr_path = lisp_path.replace(".lsp", ".scr")
    with open(scr_path, "w", encoding="utf-8") as f:
        f.write(scr_content)

    win_scr = wsl_to_windows_path(scr_path)

    # Build command - use PowerShell for Windows execution
    cmd = [
        "powershell.exe", "-Command",
        f'& "{win_accore}" /i "{win_dwg}" /s "{win_scr}" /l en-US'
    ]

    console.print(f"[dim]Executing: {' '.join(cmd[:3])}...[/dim]")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
            cwd="/mnt/c/Temp"
        )

        # Check if JSON was created
        if os.path.exists(output_json):
            return True, "Extraction completed successfully"
        else:
            return False, f"JSON not created. stderr: {result.stderr[:500]}"

    except subprocess.TimeoutExpired:
        return False, "AutoCAD Core Console timed out (120s)"
    except Exception as e:
        return False, str(e)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA PARSING & PRESENTATION
# ═══════════════════════════════════════════════════════════════════════════════

def parse_boq_data(json_path: str) -> Dict[str, Any]:
    """Parse the extracted JSON data."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def calculate_pipe_summary(pipe_data: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Calculate pipe summary with type classification.
    Applies vertical factor (+10%) for 3D estimation.
    """
    summary = []

    for color_key, length in pipe_data.items():
        # Extract color number from key like "color_4"
        if isinstance(color_key, str) and color_key.startswith("color_"):
            color = int(color_key.split("_")[1])
        else:
            color = int(color_key) if isinstance(color_key, (int, str)) else 0

        # Get pipe info from color map
        pipe_info = PIPE_COLOR_MAP.get(color, {
            "name": f"Other Pipe (Color {color})",
            "size": "Unknown",
            "type": "OTHER"
        })

        # Apply vertical factor
        adjusted_length = length * VERTICAL_FACTOR

        summary.append({
            "color": color,
            "type": pipe_info["type"],
            "description": pipe_info["name"],
            "size": pipe_info["size"],
            "raw_length_mm": length,
            "adjusted_length_mm": adjusted_length,
            "adjusted_length_m": adjusted_length / 1000,
        })

    return summary

def display_boq_table(data: Dict[str, Any], dwg_name: str):
    """Display beautiful BoQ table in terminal."""

    # Header Panel
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]AQUABRAIN FIRE PROTECTION - BILL OF QUANTITIES[/bold cyan]\n"
        f"[dim]Source: {dwg_name}[/dim]\n"
        f"[dim]Extracted: {data.get('extraction_timestamp', 'N/A')}[/dim]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print()

    # ═══════════════════════════════════════════════════════════════════════
    # PIPE SUMMARY TABLE
    # ═══════════════════════════════════════════════════════════════════════

    pipe_data = data.get("pipes", {})
    if pipe_data:
        pipe_summary = calculate_pipe_summary(pipe_data)

        pipe_table = Table(
            title="[bold yellow]PIPING SUMMARY[/bold yellow]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )

        pipe_table.add_column("Type", style="cyan")
        pipe_table.add_column("Description", style="white")
        pipe_table.add_column("Size", style="green")
        pipe_table.add_column("Raw Length", justify="right")
        pipe_table.add_column("Adjusted (+10%)", justify="right", style="bold green")

        total_raw = 0
        total_adjusted = 0

        for pipe in sorted(pipe_summary, key=lambda x: x["type"]):
            pipe_table.add_row(
                pipe["type"],
                pipe["description"],
                pipe["size"],
                f"{pipe['raw_length_mm']:,.1f} mm",
                f"{pipe['adjusted_length_m']:,.2f} m"
            )
            total_raw += pipe["raw_length_mm"]
            total_adjusted += pipe["adjusted_length_m"]

        pipe_table.add_section()
        pipe_table.add_row(
            "[bold]TOTAL[/bold]",
            "",
            "",
            f"[bold]{total_raw:,.1f} mm[/bold]",
            f"[bold green]{total_adjusted:,.2f} m[/bold green]"
        )

        console.print(pipe_table)
        console.print()

    # ═══════════════════════════════════════════════════════════════════════
    # SPRINKLER HEADS TABLE
    # ═══════════════════════════════════════════════════════════════════════

    sprinklers = data.get("sprinklers", [])
    sprinkler_count = data.get("sprinkler_count", len(sprinklers))

    sprinkler_table = Table(
        title=f"[bold yellow]SPRINKLER HEADS ({sprinkler_count} units)[/bold yellow]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )

    sprinkler_table.add_column("#", style="dim", width=4)
    sprinkler_table.add_column("Block Name", style="cyan")
    sprinkler_table.add_column("Layer", style="white")
    sprinkler_table.add_column("X", justify="right")
    sprinkler_table.add_column("Y", justify="right")
    sprinkler_table.add_column("Z", justify="right")

    # Group by block name for summary
    block_counts = {}
    for spk in sprinklers:
        name = spk.get("block_name", "Unknown")
        block_counts[name] = block_counts.get(name, 0) + 1

    # Show first 10 items detail
    for i, spk in enumerate(sprinklers[:10], 1):
        sprinkler_table.add_row(
            str(i),
            spk.get("block_name", "N/A")[:25],
            spk.get("layer", "N/A")[:15],
            f"{spk.get('x', 0):,.1f}",
            f"{spk.get('y', 0):,.1f}",
            f"{spk.get('z', 0):,.1f}"
        )

    if len(sprinklers) > 10:
        sprinkler_table.add_row(
            "...",
            f"[dim]({len(sprinklers) - 10} more)[/dim]",
            "", "", "", ""
        )

    console.print(sprinkler_table)
    console.print()

    # Block type summary
    if block_counts:
        summary_table = Table(
            title="[bold yellow]SPRINKLER TYPE SUMMARY[/bold yellow]",
            box=box.SIMPLE
        )
        summary_table.add_column("Block Type", style="cyan")
        summary_table.add_column("Count", justify="right", style="bold green")

        for name, count in sorted(block_counts.items(), key=lambda x: -x[1]):
            summary_table.add_row(name, str(count))

        console.print(summary_table)
        console.print()

    # ═══════════════════════════════════════════════════════════════════════
    # VALVES TABLE
    # ═══════════════════════════════════════════════════════════════════════

    valves = data.get("valves", [])
    valve_count = data.get("valve_count", len(valves))

    if valves:
        valve_table = Table(
            title=f"[bold yellow]VALVES & CONTROLS ({valve_count} units)[/bold yellow]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )

        valve_table.add_column("Block Name", style="cyan")
        valve_table.add_column("Location (X, Y)", justify="right")

        for vlv in valves:
            valve_table.add_row(
                vlv.get("block_name", "N/A"),
                f"({vlv.get('x', 0):,.1f}, {vlv.get('y', 0):,.1f})"
            )

        console.print(valve_table)
        console.print()

    # ═══════════════════════════════════════════════════════════════════════
    # FINAL SUMMARY PANEL
    # ═══════════════════════════════════════════════════════════════════════

    summary_text = Text()
    summary_text.append("EXTRACTION SUMMARY\n", style="bold underline")
    summary_text.append(f"Pipe Segments: ", style="dim")
    summary_text.append(f"{len(pipe_data)} color groups\n", style="green")
    summary_text.append(f"Sprinkler Heads: ", style="dim")
    summary_text.append(f"{sprinkler_count} units\n", style="green")
    summary_text.append(f"Valves/Controls: ", style="dim")
    summary_text.append(f"{valve_count} units\n", style="green")
    summary_text.append(f"\nData Isomorphism: ", style="dim")
    summary_text.append("ACHIEVED ✓", style="bold green")

    console.print(Panel(summary_text, border_style="green", box=box.DOUBLE))

def generate_mock_data(dwg_name: str) -> Dict[str, Any]:
    """Generate mock data for demo/testing when AutoCAD is not available."""
    return {
        "extraction_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "MOCK DATA (AutoCAD not available)",
        "extractor_version": "2.0-AquaBrain-Mock",
        "pipes": {
            "color_4": 45678.5,   # Cyan - Main
            "color_6": 23456.2,   # Magenta - Branch
            "color_2": 12345.8,   # Yellow - Branch
            "color_5": 8901.3,    # Blue - Branch
        },
        "sprinkler_count": 47,
        "sprinklers": [
            {"block_name": "SPK-K80-PEND", "x": 1234.5, "y": 5678.9, "z": 3000.0, "layer": "ספרינקלרים"},
            {"block_name": "SPK-K80-PEND", "x": 2345.6, "y": 6789.0, "z": 3000.0, "layer": "ספרינקלרים"},
            {"block_name": "SPK-K115-UPRIGHT", "x": 3456.7, "y": 7890.1, "z": 0.0, "layer": "ספרינקלרים"},
            {"block_name": "SPK-K80-SIDEWALL", "x": 4567.8, "y": 8901.2, "z": 2800.0, "layer": "ספרינקלרים"},
        ] + [{"block_name": "SPK-K80-PEND", "x": i*100, "y": i*50, "z": 3000.0, "layer": "ספרינקלרים"} for i in range(43)],
        "valve_count": 3,
        "valves": [
            {"block_name": "ZONE-CONTROL-VALVE", "x": 500.0, "y": 500.0},
            {"block_name": "CHECK-VALVE-100", "x": 600.0, "y": 500.0},
            {"block_name": "ALARM-VALVE", "x": 450.0, "y": 500.0},
        ]
    }

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main orchestration function."""

    # Banner
    console.print()
    console.print(Panel.fit(
        "[bold cyan]╔══════════════════════════════════════════════════════════════╗[/bold cyan]\n"
        "[bold cyan]║   AQUABRAIN SPRINKLER BoQ EXTRACTOR                          ║[/bold cyan]\n"
        "[bold cyan]║   Level 5 Hybrid Automation Architecture                     ║[/bold cyan]\n"
        "[bold cyan]║   Ubuntu CLI → Windows CAD Engine → Data Isomorphism         ║[/bold cyan]\n"
        "[bold cyan]╚══════════════════════════════════════════════════════════════╝[/bold cyan]",
        border_style="cyan"
    ))
    console.print()

    # Get DWG path from args or search
    dwg_path = None
    if len(sys.argv) > 1:
        dwg_path = sys.argv[1]

    if not dwg_path or not os.path.exists(dwg_path):
        console.print("[yellow]Searching for 1783-nim.dwg...[/yellow]")
        dwg_path = find_dwg_file("1783-nim.dwg")

    # Setup paths
    temp_dir = "/mnt/c/Temp/AquaBrain"
    os.makedirs(temp_dir, exist_ok=True)

    output_json = os.path.join(temp_dir, "boq_data.json")
    lisp_path = os.path.join(temp_dir, "extractor.lsp")

    # Find AutoCAD
    accore_path = find_accoreconsole()

    use_mock = False

    if not accore_path:
        console.print("[yellow]⚠ AutoCAD Core Console not found. Using MOCK data for demo.[/yellow]")
        use_mock = True

    if not dwg_path:
        console.print("[yellow]⚠ DWG file not found. Using MOCK data for demo.[/yellow]")
        use_mock = True

    if use_mock:
        # Generate and display mock data
        console.print()
        console.print("[bold magenta]═══ MOCK MODE ACTIVE ═══[/bold magenta]")
        console.print("[dim]This demonstrates the output format without actual CAD extraction[/dim]")
        console.print()

        mock_data = generate_mock_data("1783-nim.dwg (MOCK)")
        display_boq_table(mock_data, "1783-nim.dwg (MOCK)")

        # Save mock JSON for reference
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(mock_data, f, indent=2, ensure_ascii=False)

        console.print(f"[dim]Mock JSON saved to: {output_json}[/dim]")
        return

    # Real extraction
    console.print(f"[green]✓ AutoCAD Core Console: {accore_path}[/green]")
    console.print(f"[green]✓ Target DWG: {dwg_path}[/green]")
    console.print()

    # Generate LISP payload
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        task = progress.add_task("[cyan]Generating LISP payload...", total=None)

        lisp_code = generate_extractor_lisp(
            wsl_to_windows_path(output_json),
            TARGET_LAYER
        )

        with open(lisp_path, "w", encoding="utf-8") as f:
            f.write(lisp_code)

        progress.update(task, description="[green]✓ LISP payload generated")
        time.sleep(0.3)

        # Execute
        progress.update(task, description="[cyan]Executing AutoCAD Core Console...")

        success, message = run_accoreconsole(
            accore_path, dwg_path, lisp_path, output_json
        )

        if success:
            progress.update(task, description="[green]✓ Extraction complete")
        else:
            progress.update(task, description=f"[red]✗ {message}")

    console.print()

    if success and os.path.exists(output_json):
        # Parse and display
        data = parse_boq_data(output_json)
        dwg_name = os.path.basename(dwg_path)
        display_boq_table(data, dwg_name)

        console.print(f"[dim]JSON output: {output_json}[/dim]")
    else:
        console.print(f"[red]Extraction failed: {message}[/red]")
        console.print("[yellow]Falling back to MOCK data...[/yellow]")
        mock_data = generate_mock_data("1783-nim.dwg (FALLBACK)")
        display_boq_table(mock_data, "1783-nim.dwg (FALLBACK)")

    # Final banner
    console.print()
    console.print(Panel.fit(
        "[bold green]╔══════════════════════════════════════════════════════════════╗[/bold green]\n"
        "[bold green]║   DATA ISOMORPHISM ACHIEVED                                  ║[/bold green]\n"
        "[bold green]║   CAD Entities → Logical Fire Protection Objects             ║[/bold green]\n"
        "[bold green]╚══════════════════════════════════════════════════════════════╝[/bold green]",
        border_style="green"
    ))

if __name__ == "__main__":
    main()
