"""Draw the extrusion paths of a G-code file in 3D and save a PNG (one color per chunk).
Usage: python plot_gcode.py <file.gcode> <out.png>"""
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from matplotlib.lines import Line2D

def extrusion_segments(path):
    """Return chunk -> list of ((x0, y0, z0), (x1, y1, z1)) for every move that extrudes."""
    x = y = z = e = 0.0; chunk = 0; segs = {0: []}
    for line in open(path):
        if line.startswith(';Chunk '):
            chunk = int(line.split()[1]); segs[chunk] = []
        code = line.split(';')[0].strip()
        if not code.startswith(('G0', 'G1')):
            continue
        v = dict((m[0], float(m[1:])) for m in code.split()[1:])
        nx, ny, nz = v.get('X', x), v.get('Y', y), v.get('Z', z)
        if v.get('E', e) > e and ('X' in v or 'Y' in v):
            segs[chunk].append(((x, y, z), (nx, ny, nz)))
        x, y, z, e = nx, ny, nz, v.get('E', e)
    return segs

segs = extrusion_segments(sys.argv[1])
fig = plt.figure(figsize=(8, 7)); ax = fig.add_subplot(projection='3d')
colors = ['0.55', 'tab:orange', 'tab:blue', 'tab:green']
for c, s in segs.items():
    if s:
        ax.add_collection3d(Line3DCollection(s, colors=colors[c % 4], linewidths=0.4))
allp = [p for s in segs.values() for seg in s for p in seg]
for i, setlim in enumerate((ax.set_xlim, ax.set_ylim, ax.set_zlim)):
    setlim(min(p[i] for p in allp), max(p[i] for p in allp))
ax.set_xlabel('X (mm)'); ax.set_ylabel('Y (mm)'); ax.set_zlabel('Z (mm)')
ax.set_aspect('equal'); ax.legend(handles=[Line2D([], [], color=colors[c % 4], label='Chunk %d' % c) for c in segs if segs[c]]); ax.view_init(25, -60)
plt.title(sys.argv[1].replace('\\', '/').split('/')[-1]); plt.tight_layout(); plt.savefig(sys.argv[2], dpi=110)
print('saved', sys.argv[2])
