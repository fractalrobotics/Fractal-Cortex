"""Checks for the ArtPrint step-1 G-code (bed rotates, never tilts).
Usage: python check_gcode.py <orig.gcode> <new.gcode> <tilt_deg> <layer_height>"""
import sys, re, math
import numpy as np

def parse(path):
    """Return list of extrusion points per chunk: chunk -> [(x, y, z, e)], plus the raw text."""
    x = y = z = e = 0.0; chunk = 0; pts = {0: []}; prevE = 0.0
    text = open(path).read()
    for line in text.splitlines():
        if line.startswith(';Chunk '):
            chunk = int(line.split()[1]); pts[chunk] = []
        code = line.split(';')[0].strip()
        if not code.startswith(('G0', 'G1')):
            continue
        vals = dict((m[0], float(m[1:])) for m in code.split()[1:])
        x, y, z = vals.get('X', x), vals.get('Y', y), vals.get('Z', z)
        if 'E' in vals:
            if vals['E'] > prevE and ('X' in vals or 'Y' in vals):  # a real extrusion move
                pts[chunk].append((x, y, z, vals['E']))
            prevE = vals['E']
    return pts, text

if __name__ == '__main__':
    orig, otext = parse(sys.argv[1]); new, ntext = parse(sys.argv[2])
    tilt = math.radians(float(sys.argv[3])); h = float(sys.argv[4])
    ok = [True]
    def check(name, cond, detail=''):
        ok[0] &= bool(cond)
        print(('PASS ' if cond else 'FAIL ') + name + (('  (' + detail + ')') if detail else ''))

    check('no bed tilt motor (stepper_b) in G-code', 'stepper_b' not in ntext)
    check('no "X0 Y-175" park move', 'Y-175' not in ntext)
    allz = [p[2] for c in new.values() for p in c]
    check('nozzle never goes below the bed (Z >= 0)', min(allz) >= 0, 'min Z = %.3f' % min(allz))
    check('same number of extrusion moves as the original', sum(map(len, new.values())) == sum(map(len, orig.values())),
          '%d vs %d' % (sum(map(len, new.values())), sum(map(len, orig.values()))))
    fe_o = max(p[3] for c in orig.values() for p in c); fe_n = max(p[3] for c in new.values() for p in c)
    check('same total filament (rotation does not change lengths)', abs(fe_o - fe_n) < 0.01 * fe_o, '%.2f vs %.2f mm' % (fe_n, fe_o))

    # Chunk 0 is flat: it must be exactly the same toolpath as the original
    d0 = max(abs(a[i] - b[i]) for a, b in zip(orig[0], new[0]) for i in range(3))
    check('chunk 0 (flat) identical to the original', d0 < 1e-3, 'max diff %.5f mm' % d0)

    for c in sorted(new):
        if c == 0: continue
        P = np.array([p[:3] for p in new[c]]); P[:, 2] -= 0.5 * h   # back to mid-layer (slice plane)
        # Re-applying the old bed tilt (rotation about X by the tilt angle) must give back the original flat layers
        QB = np.array([[1, 0, 0], [0, math.cos(tilt), -math.sin(tilt)], [0, math.sin(tilt), math.cos(tilt)]])
        back = P @ QB.T
        O = np.array([p[:3] for p in orig[c]])
        dxy = np.abs(back[:, :2] - O[:, :2]).max()
        dz = np.abs(back[:, 2] + 0.5 * h - O[:, 2]).max()
        check('chunk %d: same paths as the original once the old bed tilt is re-applied' % c, dxy < 1e-3 and dz < 1e-3,
              'max diff XY %.5f, Z %.5f mm' % (dxy, dz))
        zr = P[:, 2].max() - P[:, 2].min()
        check('chunk %d: Z now varies inside the tilted layers' % c, tilt == 0 or zr > h, 'Z range %.2f mm' % zr)
        # Every point of a layer lies on a plane tilted by the chunk angle: normal is (0, sin t, cos t) after bed rotation
        n = np.array([0, math.sin(tilt), math.cos(tilt)])
        levels = P @ n
        spacing = np.diff(np.unique(np.round(levels, 3)))
        check('chunk %d: points sit on parallel planes one layer apart' % c, np.allclose(spacing, h, atol=2e-3),
              'spacing %.3f to %.3f mm' % (spacing.min(), spacing.max()))
    print('\nRESULT:', 'ALL CHECKS PASSED' if ok[0] else 'SOME CHECKS FAILED')
    sys.exit(0 if ok[0] else 1)
