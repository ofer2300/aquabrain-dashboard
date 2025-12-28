#!/usr/bin/env python3
"""Quick extraction test - run accoreconsole directly."""

import subprocess
import os
import json
import time

# Paths
DWG = 'C:\\Temp\\1783-nim - Standard\\1783-nim.dwg'
LISP = 'C:\\Temp\\AquaBrain\\extractor.lsp'
SCR = 'C:\\Temp\\AquaBrain\\extractor.scr'
OUTPUT = 'C:\\Temp\\AquaBrain\\boq_results.json'
ACCORE = 'C:\\Program Files\\Autodesk\\AutoCAD 2026\\accoreconsole.exe'

# Create SCR that loads LISP
SCR_CONTENT = f'''; Quick extraction
(load "{LISP.replace(chr(92), '/')}")
QUIT Y
'''

# Create simplified LISP
LISP_CONTENT = ''';;; Quick Sprinkler BoQ Extractor
(vl-load-com)

(defun c:QUICKEXTRACT (/ ss i ent etype col len pipe-lengths spk-count valve-count f)
  (princ "\\n[EXTRACT] Starting...")

  ;; Count pipes by color
  (setq pipe-lengths nil)
  (setq ss (ssget "X" '((0 . "LWPOLYLINE,LINE,POLYLINE"))))
  (if ss
    (progn
      (setq i 0)
      (while (< i (sslength ss))
        (setq ent (ssname ss i))
        (setq col (cdr (assoc 62 (entget ent))))
        (if (null col) (setq col 256))
        ;; Get length
        (setq obj (vlax-ename->vla-object ent))
        (if (vlax-property-available-p obj 'Length)
          (progn
            (setq len (vla-get-length obj))
            (setq existing (assoc col pipe-lengths))
            (if existing
              (setq pipe-lengths (subst (cons col (+ (cdr existing) len)) existing pipe-lengths))
              (setq pipe-lengths (cons (cons col len) pipe-lengths))
            )
          )
        )
        (setq i (1+ i))
      )
      (princ (strcat "\\n[PIPES] Found " (itoa (sslength ss)) " entities"))
    )
  )

  ;; Count blocks
  (setq spk-count 0 valve-count 0)
  (setq ss (ssget "X" '((0 . "INSERT"))))
  (if ss
    (progn
      (setq i 0)
      (while (< i (sslength ss))
        (setq ent (ssname ss i))
        (setq bname (strcase (cdr (assoc 2 (entget ent)))))
        (cond
          ((or (wcmatch bname "*SPRINK*") (wcmatch bname "*SPK*") (wcmatch bname "*HEAD*") (wcmatch bname "*NOZZLE*"))
           (setq spk-count (1+ spk-count)))
          ((or (wcmatch bname "*VALVE*") (wcmatch bname "*CONTROL*") (wcmatch bname "*CHECK*"))
           (setq valve-count (1+ valve-count)))
        )
        (setq i (1+ i))
      )
      (princ (strcat "\\n[BLOCKS] Total: " (itoa (sslength ss)) ", Sprinklers: " (itoa spk-count) ", Valves: " (itoa valve-count)))
    )
  )

  ;; Write JSON
  (setq f (open "C:/Temp/AquaBrain/boq_results.json" "w"))
  (if f
    (progn
      (write-line "{" f)
      (write-line "  \\"source\\": \\"AutoCAD 2026\\"," f)
      (write-line "  \\"pipes\\": {" f)
      (setq first T)
      (foreach p pipe-lengths
        (if (not first) (princ ",\\n" f))
        (setq first nil)
        (princ (strcat "    \\"" (itoa (car p)) "\\": " (rtos (cdr p) 2 2)) f)
      )
      (write-line "\\n  }," f)
      (write-line (strcat "  \\"sprinkler_count\\": " (itoa spk-count) ",") f)
      (write-line (strcat "  \\"valve_count\\": " (itoa valve-count)) f)
      (write-line "}" f)
      (close f)
      (princ "\\n[JSON] Written to C:/Temp/AquaBrain/boq_results.json")
    )
    (princ "\\n[ERROR] Cannot write file!")
  )
  (princ)
)

(c:QUICKEXTRACT)
'''

# Ensure directory
os.makedirs('/mnt/c/Temp/AquaBrain', exist_ok=True)

# Write files
with open('/mnt/c/Temp/AquaBrain/extractor.lsp', 'w') as f:
    f.write(LISP_CONTENT)
with open('/mnt/c/Temp/AquaBrain/extractor.scr', 'w') as f:
    f.write(SCR_CONTENT)

# Remove old output
if os.path.exists('/mnt/c/Temp/AquaBrain/boq_results.json'):
    os.remove('/mnt/c/Temp/AquaBrain/boq_results.json')

print("Running accoreconsole...")
cmd = f'powershell.exe -Command \'& "{ACCORE}" /i "{DWG}" /s "{SCR}" /l en-US\''
result = subprocess.run(cmd, shell=True, capture_output=True, timeout=180)
# Decode with error handling
stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ""
stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""

print(f"Exit code: {result.returncode}")

# Check output
time.sleep(2)
if os.path.exists('/mnt/c/Temp/AquaBrain/boq_results.json'):
    print("\n✓ JSON created!")
    with open('/mnt/c/Temp/AquaBrain/boq_results.json') as f:
        data = json.load(f)
        print(json.dumps(data, indent=2))
else:
    print("\n✗ JSON not created")
    print("stdout:", stdout[:500] if stdout else "empty")
    print("stderr:", stderr[:500] if stderr else "empty")
