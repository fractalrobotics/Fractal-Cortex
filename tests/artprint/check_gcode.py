"""Checks for the ArtPrint G-code: the bed rotates (axis A) and moves in X, the nozzle moves in Y and Z, the bed never tilts.
Usage: python check_gcode.py <original.gcode> <new.gcode> <tilt_deg> <layer_height>"""
import sys, math
import numpy as np

X_HALF_TRAVEL = 150.0   # Must match slicing_functions.py
Y_TRAVEL = 150.0
MAX_A_STEP_DEG = 0.5


def parse(path):
    """Read a G-code file. Returns (moves, text): moves is chunk -> list of dicts, one per G0/G1 move,
    with the position before (x0, y0, z0, a0) and after (x, y, z, a), the feedrate F and whether it extrudes."""
    x = y = z = a = 0.0; e = 0.0; f = 0.0; chunk = 0; moves = {0: []}
    text = open(path).read()
    for line in text.splitlines():
        if line.startswith(';Chunk '):
            chunk = int(line.split()[1]); moves[chunk] = []
        code = line.split(';')[0].strip()
        if not code.startswith(('G0', 'G1')):
            continue
        v = dict((m[0], float(m[1:])) for m in code.split()[1:])
        nx, ny, nz, na = v.get('X', x), v.get('Y', y), v.get('Z', z), v.get('A', a)
        f = v.get('F', f)
        extrudes = 'E' in v and v['E'] > e and (nx, ny, nz, na) != (x, y, z, a)
        moves[chunk].append(dict(x0=x, y0=y, z0=z, a0=a, x=nx, y=ny, z=nz, a=na, f=f, extrudes=extrudes))
        x, y, z, a, e = nx, ny, nz, na, v.get('E', e)
    return moves, text


def to_bed(x, y, a_deg):
    """Point under the nozzle, expressed in the bed's own frame (undo the bed rotation)."""
    c, s = math.cos(math.radians(a_deg)), math.sin(math.radians(a_deg))
    return np.array([c * x + s * y, -s * x + c * y])


def distance_to_segment(p, a, b):
    ab = b - a; t = 0.0 if not ab.any() else np.clip(np.dot(p - a, ab) / np.dot(ab, ab), 0, 1)
    return float(np.linalg.norm(p - (a + t * ab)))


if __name__ == '__main__':
    orig, otext = parse(sys.argv[1]); new, ntext = parse(sys.argv[2])
    tilt = math.radians(float(sys.argv[3])); h = float(sys.argv[4])
    ok = [True]

    def check(name, cond, detail=''):
        ok[0] &= bool(cond)
        print(('PASS ' if cond else 'FAIL ') + name + (('  (' + detail + ')') if detail else ''))

    allmoves = [m for c in new.values() for m in c]
    check('no bed tilt motor (stepper_b) in G-code', 'stepper_b' not in ntext)
    check('no "X0 Y-175" park move', 'Y-175' not in ntext)
    check('bed rotation declared as G-code axis A', 'GCODE_AXIS=A' in ntext)
    check('nozzle never goes below the bed (Z >= 0)', min(m['z'] for m in allmoves) >= 0,
          'min Z = %.3f' % min(m['z'] for m in allmoves))
    worstX = max(abs(m['x']) for m in allmoves); minY = min(m['y'] for m in allmoves); maxY = max(m['y'] for m in allmoves)
    check('every move is within reach (|X| <= %g, 0 <= Y <= %g)' % (X_HALF_TRAVEL, Y_TRAVEL),
          worstX <= X_HALF_TRAVEL + 1e-3 and minY >= -1e-3 and maxY <= Y_TRAVEL + 1e-3,
          'max |X| %.1f, Y from %.1f to %.1f' % (worstX, minY, maxY))
    origMinY = min(m['y'] for c in orig.values() for m in c if m['extrudes'])
    if origMinY < -1e-3:
        print('     (the original G-code needed Y down to %.1f mm: out of reach on ArtPrint)' % origMinY)

    # Real speed on the part: Klipper times a move by its X/Y/Z length, so time = machine length / F
    origSpeeds = sorted(set(m['f'] for c in orig.values() for m in c if m['extrudes']))
    worst = 0.0; totalBed = 0.0
    for c, ms in new.items():
        for m in ms:
            if not m['extrudes']:
                continue
            p0 = np.append(to_bed(m['x0'], m['y0'], m['a0']), m['z0']); p1 = np.append(to_bed(m['x'], m['y'], m['a']), m['z'])
            real = float(np.linalg.norm(p1 - p0)); totalBed += real
            machine = math.dist((m['x0'], m['y0'], m['z0']), (m['x'], m['y'], m['z']))
            if real > 0.05 and machine > 1e-6:
                speed = real / (machine / m['f'])
                worst = max(worst, min(abs(speed - s) / s for s in origSpeeds))
    check('real printing speed on the part matches the settings', worst < 0.02, 'worst error %.2f %%' % (100 * worst))
    totalOrig = sum(math.dist((m['x0'], m['y0'], m['z0']), (m['x'], m['y'], m['z'])) for c in orig.values() for m in c if m['extrudes'])
    check('same total length of printed lines', abs(totalBed - totalOrig) < 0.002 * totalOrig, '%.1f vs %.1f mm' % (totalBed, totalOrig))
    stepA = max([abs(m['a'] - m['a0']) for m in allmoves if m['extrudes']] + [0])
    check('bed never turns more than %.1f deg on one printing line' % MAX_A_STEP_DEG, stepA <= MAX_A_STEP_DEG + 1e-3, 'max %.3f deg' % stepA)

    QB = np.array([[1, 0, 0], [0, math.cos(tilt), -math.sin(tilt)], [0, math.sin(tilt), math.cos(tilt)]])
    for c in sorted(new):
        tiltedChunk = c > 0 and tilt != 0
        # Original points: where the nozzle lays filament, in the original slicer's frame
        O = [np.array([m['x'], m['y'], m['z']]) for m in orig[c] if m['extrudes']]
        O0 = [np.array([m['x0'], m['y0'], m['z0']]) for m in orig[c] if m['extrudes']]
        # New points brought into the same frame
        N = []
        for m in new[c]:
            if not m['extrudes']:
                continue
            for (x, y, z, a) in ((m['x0'], m['y0'], m['z0'], m['a0']), (m['x'], m['y'], m['z'], m['a'])):
                if tiltedChunk:  # bed held still, re-apply the old bed tilt: must give the original flat layers back
                    q = QB @ np.array([x, y, z - 0.5 * h]); N.append(q + [0, 0, 0.5 * h])
                else:            # bed free to turn: undo its rotation to get back to the original bed frame
                    N.append(np.append(to_bed(x, y, a), z))
        # Every new point must lie on one of the original printed lines, and every original line must be covered
        segs = list(zip(O0, O))
        # Walk both in order: each new line is a piece of the current original line; when it reaches its end, move on
        j = 0; far = 0.0
        for k in range(0, len(N), 2):
            a_, b_ = N[k], N[k + 1]
            if j == len(segs):
                far = float('inf'); break
            far = max(far, distance_to_segment(a_, *segs[j]), distance_to_segment(b_, *segs[j]))
            if far > 2e-3:
                break
            if np.linalg.norm(b_ - segs[j][1]) < 2e-3:
                j += 1
        check('chunk %d: exactly the same lines as the original, once the bed %s' % (c, 'tilt is re-applied' if tiltedChunk else 'rotation is undone'),
              far <= 2e-3 and j == len(segs), 'covered %d of %d original lines, max gap %.4f mm' % (j, len(segs), far))
        A = [m['a'] for m in new[c] if m['extrudes']]
        if tiltedChunk:
            check('chunk %d: bed held at one angle while the tilted layers print' % c, max(A) - min(A) < 1e-6, 'A = %.1f deg' % A[0])
        else:
            print('     chunk %d: bed angle used while printing from %.1f to %.1f deg' % (c, min(A), max(A)))
    print('\nRESULT:', 'ALL CHECKS PASSED' if ok[0] else 'SOME CHECKS FAILED')
    sys.exit(0 if ok[0] else 1)
