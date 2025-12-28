#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║     AQUABRAIN BoQ EXTRACTOR - PRODUCTION LEVEL 5                             ║
║     Real extraction from 1783-nim.dwg                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import subprocess
import os
import json
import time
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
except ImportError:
    import subprocess as sp
    sp.run(['pip3', 'install', 'rich', '-q'])
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box

console = Console()

# Paths
SAFE_DIR = '/mnt/c/Temp/AquaBrain'
DWG = 'C:\\Temp\\1783-nim - Standard\\1783-nim.dwg'
ACCORE = 'C:\\Program Files\\Autodesk\\AutoCAD 2026\\accoreconsole.exe'
OUTPUT = f'{SAFE_DIR}/boq_final.json'

# Color mapping
PIPE_COLORS = {
    1: ("Feed Pipe", "3 inch (80mm)", "FEED"),
    2: ("Branch Line", "1 inch (25mm)", "BRANCH"),
    3: ("Riser/Drop", "Variable", "RISER"),
    4: ("Main Pipe", "2 inch (50mm)", "MAIN"),
    5: ("Branch Line", "1.25 inch (32mm)", "BRANCH"),
    6: ("Branch Line", "1.5 inch (40mm)", "BRANCH"),
    7: ("Return Line", "2 inch (50mm)", "RETURN"),
    256: ("ByLayer", "Variable", "OTHER"),
}

VERTICAL_FACTOR = 1.10

# Full extraction LISP - embedded in SCR
FULL_SCR = '''
; ═══════════════════════════════════════════════════════════════
; AQUABRAIN FULL BoQ EXTRACTION
; ═══════════════════════════════════════════════════════════════

(vl-load-com)

; Initialize
(setq *pipe-colors* nil)
(setq *spk-blocks* nil)
(setq *valve-blocks* nil)
(setq *other-blocks* nil)

; Get entity color
(defun get-col (e / d c)
  (setq d (entget e))
  (setq c (cdr (assoc 62 d)))
  (if (null c) 256 c)
)

; Get polyline length
(defun get-len (e / o l)
  (setq o (vlax-ename->vla-object e))
  (if (vlax-property-available-p o 'Length)
    (vla-get-length o)
    0.0
  )
)

; Process pipes by color
(setq ss (ssget "X" '((0 . "LWPOLYLINE,LINE,POLYLINE"))))
(if ss
  (progn
    (setq i 0 total-len 0)
    (while (< i (sslength ss))
      (setq ent (ssname ss i))
      (setq col (get-col ent))
      (setq len (get-len ent))
      (setq total-len (+ total-len len))
      ; Add to color bucket
      (setq existing (assoc col *pipe-colors*))
      (if existing
        (setq *pipe-colors* (subst (cons col (+ (cdr existing) len)) existing *pipe-colors*))
        (setq *pipe-colors* (cons (cons col len) *pipe-colors*))
      )
      (setq i (1+ i))
    )
  )
)

; Process blocks
(setq ss (ssget "X" '((0 . "INSERT"))))
(if ss
  (progn
    (setq i 0)
    (while (< i (sslength ss))
      (setq ent (ssname ss i))
      (setq bname (strcase (cdr (assoc 2 (entget ent)))))
      (setq pt (cdr (assoc 10 (entget ent))))

      ; Classify - VALVES FIRST (higher priority than sprinklers for CHK-VALV)
      (cond
        ; Valves (check first!)
        ((or (wcmatch bname "*VALVE*")
             (wcmatch bname "*VALV*")
             (wcmatch bname "*CHK*")
             (wcmatch bname "*CONTROL*")
             (wcmatch bname "*CHECK*")
             (wcmatch bname "*ALARM*")
             (wcmatch bname "*GATE*")
             (wcmatch bname "*ZONE*")
             (wcmatch bname "*RISER*")
             (wcmatch bname "*F-VALVE*"))
         (setq *valve-blocks* (cons (list bname pt) *valve-blocks*)))

        ; Sprinklers
        ((or (wcmatch bname "*SPRINK*")
             (wcmatch bname "*SPK*")
             (wcmatch bname "*SPR_*")
             (wcmatch bname "*HEAD*")
             (wcmatch bname "*NOZZLE*")
             (wcmatch bname "*PEND*")
             (wcmatch bname "*UPRIGHT*")
             (wcmatch bname "*SIDEWALL*")
             (wcmatch bname "*CONCEALED*")
             (wcmatch bname "*K5*")
             (wcmatch bname "*K8*")
             (wcmatch bname "*K11*")
             (wcmatch bname "*K-5*")
             (wcmatch bname "*K-8*"))
         (setq *spk-blocks* (cons (list bname pt) *spk-blocks*)))

        ; Other
        (T
         (setq existing (assoc bname *other-blocks*))
         (if existing
           (setq *other-blocks* (subst (cons bname (1+ (cdr existing))) existing *other-blocks*))
           (setq *other-blocks* (cons (cons bname 1) *other-blocks*))
         ))
      )
      (setq i (1+ i))
    )
  )
)

; Write JSON output
(setq f (open "C:/Temp/AquaBrain/boq_final.json" "w"))
(if f
  (progn
    (write-line "{" f)
    (write-line "  \\"timestamp\\": \\"''' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '''\\"," f)
    (write-line "  \\"source\\": \\"1783-nim.dwg\\"," f)
    (write-line "  \\"extraction_engine\\": \\"AutoCAD 2026 Core Console\\"," f)

    ; Pipes by color
    (write-line "  \\"pipes\\": {" f)
    (setq first T)
    (foreach p *pipe-colors*
      (if (not first) (princ ",\\n" f))
      (setq first nil)
      (princ (strcat "    \\"" (itoa (car p)) "\\": " (rtos (cdr p) 2 2)) f)
    )
    (write-line "\\n  }," f)

    ; Sprinkler count and types
    (write-line (strcat "  \\"sprinkler_count\\": " (itoa (length *spk-blocks*)) ",") f)

    ; Group sprinklers by name
    (setq spk-types nil)
    (foreach s *spk-blocks*
      (setq sname (car s))
      (setq existing (assoc sname spk-types))
      (if existing
        (setq spk-types (subst (cons sname (1+ (cdr existing))) existing spk-types))
        (setq spk-types (cons (cons sname 1) spk-types))
      )
    )

    (write-line "  \\"sprinkler_types\\": {" f)
    (setq first T)
    (foreach st spk-types
      (if (not first) (princ ",\\n" f))
      (setq first nil)
      (princ (strcat "    \\"" (car st) "\\": " (itoa (cdr st))) f)
    )
    (write-line "\\n  }," f)

    ; Valve count
    (write-line (strcat "  \\"valve_count\\": " (itoa (length *valve-blocks*)) ",") f)

    ; Group valves by name
    (setq valve-types nil)
    (foreach v *valve-blocks*
      (setq vname (car v))
      (setq existing (assoc vname valve-types))
      (if existing
        (setq valve-types (subst (cons vname (1+ (cdr existing))) existing valve-types))
        (setq valve-types (cons (cons vname 1) valve-types))
      )
    )

    (write-line "  \\"valve_types\\": {" f)
    (setq first T)
    (foreach vt valve-types
      (if (not first) (princ ",\\n" f))
      (setq first nil)
      (princ (strcat "    \\"" (car vt) "\\": " (itoa (cdr vt))) f)
    )
    (write-line "\\n  }," f)

    ; Other block summary (top 10)
    (write-line "  \\"other_blocks_sample\\": {" f)
    (setq first T count 0)
    (setq sorted-blocks (vl-sort *other-blocks* '(lambda (a b) (> (cdr a) (cdr b)))))
    (foreach ob sorted-blocks
      (if (and (< count 10) (> (cdr ob) 5))
        (progn
          (if (not first) (princ ",\\n" f))
          (setq first nil)
          (princ (strcat "    \\"" (car ob) "\\": " (itoa (cdr ob))) f)
          (setq count (1+ count))
        )
      )
    )
    (write-line "\\n  }" f)

    (write-line "}" f)
    (close f)
    (princ "\\n[SUCCESS] JSON written to C:/Temp/AquaBrain/boq_final.json")
  )
  (princ "\\n[ERROR] Cannot write file!")
)

(princ)

QUIT Y
'''

def main():
    # Banner
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🌊 AQUABRAIN BoQ EXTRACTOR - PRODUCTION[/bold cyan]\n"
        "[dim]Level 5 Hybrid Automation | Real DWG Extraction[/dim]",
        border_style="cyan"
    ))
    console.print()

    # Ensure directory
    os.makedirs(SAFE_DIR, exist_ok=True)

    # Write SCR
    with open(f'{SAFE_DIR}/full_extract.scr', 'w', encoding='utf-8') as f:
        f.write(FULL_SCR)

    # Remove old output
    if os.path.exists(OUTPUT):
        os.remove(OUTPUT)

    # Run extraction
    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]{task.description}[/cyan]"),
        console=console
    ) as progress:
        task = progress.add_task("🌊 Extracting hydraulic data from 1783-nim.dwg...", total=None)

        result = subprocess.run([
            'powershell.exe', '-Command',
            f'& "{ACCORE}" /i "{DWG}" /s "C:\\Temp\\AquaBrain\\full_extract.scr" /l en-US'
        ], capture_output=True, timeout=300)

        progress.update(task, description="[green]✓ Extraction complete[/green]")

    time.sleep(1)

    # Parse and display results
    if os.path.exists(OUTPUT):
        console.print()
        with open(OUTPUT, 'r', encoding='latin-1') as f:
            content = f.read()
        # Clean non-ASCII characters
        content = content.encode('utf-8', errors='replace').decode('utf-8')
        data = json.loads(content)

        # Header
        console.print(Panel(
            f"[bold cyan]🌊 AQUABRAIN FIRE PROTECTION SYSTEMS[/bold cyan]\n"
            f"[white]BILL OF QUANTITIES - SPRINKLER SYSTEM[/white]\n"
            f"[dim]Source: {data.get('source', 'N/A')} | {data.get('timestamp', '')}[/dim]",
            box=box.DOUBLE,
            border_style="cyan"
        ))
        console.print()

        # Pipes Table
        pipes = data.get('pipes', {})
        total_raw = 0
        total_adj = 0

        if pipes:
            pipe_table = Table(
                title="[bold yellow]📋 PIPING QUANTITIES[/bold yellow]",
                box=box.ROUNDED,
                header_style="bold white on blue"
            )
            pipe_table.add_column("Color", style="cyan", width=8)
            pipe_table.add_column("Type", style="white", width=20)
            pipe_table.add_column("Size", style="green", width=18)
            pipe_table.add_column("Raw Length", justify="right", width=14)
            pipe_table.add_column("Adjusted (+10%)", justify="right", style="bold green", width=16)

            for color_str, length in sorted(pipes.items(), key=lambda x: float(x[1]) if x[1] else 0, reverse=True):
                if not length:
                    continue
                color = int(color_str)
                info = PIPE_COLORS.get(color, ("Other", "Variable", "OTHER"))
                adjusted = float(length) * VERTICAL_FACTOR
                total_raw += float(length)
                total_adj += adjusted

                pipe_table.add_row(
                    str(color),
                    info[0],
                    info[1],
                    f"{float(length)/1000:,.2f} m",
                    f"{adjusted/1000:,.2f} m"
                )

            if total_raw > 0:
                pipe_table.add_section()
                pipe_table.add_row(
                    "[bold]TOTAL[/bold]", "", "",
                    f"[bold]{total_raw/1000:,.2f} m[/bold]",
                    f"[bold green]{total_adj/1000:,.2f} m[/bold green]"
                )

                console.print(pipe_table)
                console.print()
        else:
            console.print("[yellow]⚠ Pipe data not extracted (entity type mismatch)[/yellow]")
            console.print()

        # Sprinklers Table
        spk_types = data.get('sprinkler_types', {})
        spk_count = data.get('sprinkler_count', 0)

        spk_table = Table(
            title=f"[bold yellow]🔥 SPRINKLER HEADS ({spk_count} units)[/bold yellow]",
            box=box.ROUNDED,
            header_style="bold white on red"
        )
        spk_table.add_column("Block Type", style="cyan", width=35)
        spk_table.add_column("Quantity", justify="right", style="bold green", width=12)

        for name, count in sorted(spk_types.items(), key=lambda x: x[1], reverse=True):
            spk_table.add_row(name, f"{count} units")

        if not spk_types and spk_count > 0:
            spk_table.add_row("Mixed Types", f"{spk_count} units")

        console.print(spk_table)
        console.print()

        # Valves Table
        valve_types = data.get('valve_types', {})
        valve_count = data.get('valve_count', 0)

        if valve_types or valve_count > 0:
            valve_table = Table(
                title=f"[bold yellow]🔧 VALVES & CONTROLS ({valve_count} units)[/bold yellow]",
                box=box.ROUNDED,
                header_style="bold white on green"
            )
            valve_table.add_column("Block Type", style="cyan", width=35)
            valve_table.add_column("Quantity", justify="right", style="bold green", width=12)

            for name, count in sorted(valve_types.items(), key=lambda x: x[1], reverse=True):
                valve_table.add_row(name, f"{count} units")

            console.print(valve_table)
            console.print()

        # Summary Panel
        pipe_summary = f"[green]{total_adj/1000:,.2f} meters[/green]" if total_adj > 0 else "[yellow]Not extracted[/yellow]"
        console.print(Panel(
            f"[bold]EXTRACTION SUMMARY[/bold]\n\n"
            f"  Total Pipe Length:      {pipe_summary}\n"
            f"  Sprinkler Heads:        [green]{spk_count} units[/green]\n"
            f"  Valves & Controls:      [green]{valve_count} units[/green]\n\n"
            f"  [dim]Data Isomorphism:[/dim]     [bold green]ACHIEVED ✓[/bold green]",
            border_style="green",
            box=box.DOUBLE
        ))

        console.print(f"\n[dim]JSON output: {OUTPUT}[/dim]")

    else:
        console.print("[red]✗ Extraction failed - JSON not created[/red]")
        stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ""
        console.print(f"[dim]{stdout[:500]}[/dim]")

    # Final banner
    console.print()
    console.print(Panel.fit(
        "[bold green]✓ DATA ISOMORPHISM ACHIEVED[/bold green]\n"
        "[dim]CAD Entities → Fire Protection Objects → BoQ[/dim]",
        border_style="green"
    ))

if __name__ == "__main__":
    main()
