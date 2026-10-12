"""ArtPrint step 1 test (bed rotates, never tilts).
Run from the repository root:  python tests/artprint/run_all.py
It slices 3 test parts with the current code, compares them to the original Fractal Cortex
output stored in tests/artprint/reference/, and saves a 3D picture of each result in tests/artprint/output/."""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.join(HERE, '..', '..', 'fractal-cortex')
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
CASES = {'flat': 0, 'tilt45': 45, 'tilt45_phi90': 45, 'ring': 0, 'far_half': 0}  # case name -> tilt angle of chunk 1 (deg)
LAYER_HEIGHT = '0.4'

failed = False
for case, tilt in CASES.items():
    print('\n========== ' + case + ' ==========')
    gcode = os.path.join(OUT, case + '.gcode')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'run_slice.py'), CODE, case, gcode], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:]); failed = True; continue
    r = subprocess.run([sys.executable, os.path.join(HERE, 'check_gcode.py'),
                        os.path.join(HERE, 'reference', 'original_' + case + '.gcode'), gcode, str(tilt), LAYER_HEIGHT])
    failed |= r.returncode != 0
    subprocess.run([sys.executable, os.path.join(HERE, 'plot_gcode.py'), gcode, os.path.join(OUT, case + '.png')])
print('\n' + ('SOME TESTS FAILED' if failed else 'ALL TESTS PASSED'))
sys.exit(1 if failed else 0)
