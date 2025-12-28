#!/usr/bin/env python3
"""Direct extraction - embed LISP in SCR"""

import subprocess
import os
import json
import time

# Ensure dir
os.makedirs('/mnt/c/Temp/AquaBrain', exist_ok=True)

# Simple SCR with embedded LISP - just count entities
SCR = '''
; Count entities in drawing
(setq pipe-count 0 block-count 0)
(setq ss1 (ssget "X" '((0 . "LWPOLYLINE,LINE,POLYLINE"))))
(if ss1 (setq pipe-count (sslength ss1)))
(setq ss2 (ssget "X" '((0 . "INSERT"))))
(if ss2 (setq block-count (sslength ss2)))
(setq f (open "C:/Temp/AquaBrain/count.txt" "w"))
(if f (progn (write-line (strcat "PIPES: " (itoa pipe-count)) f) (write-line (strcat "BLOCKS: " (itoa block-count)) f) (close f)))
(princ (strcat "\\nFound " (itoa pipe-count) " pipes and " (itoa block-count) " blocks"))
(princ)

QUIT Y
'''

with open('/mnt/c/Temp/AquaBrain/count.scr', 'w') as f:
    f.write(SCR)

# Remove old output
for fname in ['count.txt', 'boq_results.json']:
    path = f'/mnt/c/Temp/AquaBrain/{fname}'
    if os.path.exists(path):
        os.remove(path)

print("Running accoreconsole with embedded LISP...")
DWG = 'C:\\Temp\\1783-nim - Standard\\1783-nim.dwg'
SCR_PATH = 'C:\\Temp\\AquaBrain\\count.scr'
ACCORE = 'C:\\Program Files\\Autodesk\\AutoCAD 2026\\accoreconsole.exe'

# Run with simpler command
result = subprocess.run([
    'powershell.exe', '-Command',
    f'& "{ACCORE}" /i "{DWG}" /s "{SCR_PATH}" /l en-US'
], capture_output=True, timeout=180)

print(f"Exit: {result.returncode}")

time.sleep(2)

# Check results
if os.path.exists('/mnt/c/Temp/AquaBrain/count.txt'):
    print("\n✓ Count file created!")
    with open('/mnt/c/Temp/AquaBrain/count.txt') as f:
        print(f.read())
else:
    print("\n✗ Count file not created")
    stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ""
    print("Output snippet:", stdout[:1000])
