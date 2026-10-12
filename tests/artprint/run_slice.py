"""Slice a test part with Fractal Cortex without the GUI, and write the G-code.
Usage: python run_slice.py <repo_code_dir> <case> <out.gcode>"""
import sys
sys.path.insert(0, sys.argv[1])
import trimesh
import slicing_functions as sf

def make_part():
    # A 30x30x20 block with a 25 mm arm sticking out sideways (an overhang) at the top
    base = trimesh.creation.box(extents=[30, 30, 20]); base.apply_translation([0, 0, 10])
    arm = trimesh.creation.box(extents=[25, 10, 10]); arm.apply_translation([27, 0, 15])
    return trimesh.boolean.union([base, arm])

CASES = {
    # one flat direction only: must behave like a normal printer
    "flat": [1, [[0.0, 0.0, 0.0]], [[0.0, 0.0]]],
    # second chunk: the arm, sliced along a plane tilted 45 deg (theta) facing +X (phi = 0)
    "tilt45": [2, [[0.0, 0.0, 0.0], [15.0, 0.0, 10.0]], [[0.0, 0.0], [45.0, 0.0]]],
    # same but facing +Y (phi = 90) to check the bed rotation
    "tilt45_phi90": [2, [[0.0, 0.0, 0.0], [0.0, 15.0, 10.0]], [[0.0, 0.0], [45.0, 90.0]]],
    # a thin ring of 200 mm around the bed centre: the bed has to turn while each loop is printed
    "ring": [1, [[0.0, 0.0, 0.0]], [[0.0, 0.0]]],
    # a block on the far half of the bed (Y < 0), which the nozzle cannot reach without turning the bed
    "far_half": [1, [[0.0, 0.0, 0.0]], [[0.0, 0.0]]],
}

if __name__ == "__main__":
    case, out = sys.argv[2], sys.argv[3]
    mesh = make_part()
    if case == "ring":
        outer = trimesh.creation.cylinder(radius=100, height=2.0, sections=128)
        inner = trimesh.creation.cylinder(radius=95, height=4.0, sections=128)
        mesh = trimesh.boolean.difference([outer, inner]); mesh.apply_translation([0, 0, 1.0])
    if case == "far_half":
        mesh = trimesh.creation.box(extents=[40, 30, 4]); mesh.apply_translation([20, -90, 2])
    if case == "tilt45_phi90":
        mesh.apply_transform(trimesh.transformations.rotation_matrix(1.5707963267948966, [0, 0, 1]))
    meshData = [[0], {0: mesh}]
    # nozzleT, initNozzleT, bedT, initBedT, infill%, shells, layerH, speed, initSpeed, travel, initTravel, zhop, retraction, retractDist, retractSpeed, supports, brim
    printSettings = [200, 205, 60, 65, 20, 2, 0.4, 50, 20, 120, 60, True, True, 1.0, 30, False, False]
    dirs = CASES[case]
    res = sf.slice_in_5_axes(printSettings, meshData, dirs)
    if sf.stopSlicing:
        print("STOPPED: collision detected"); sys.exit(2)
    sf.write_5_axis_gcode(out, case, printSettings, dirs[1], dirs[2], *res)
    print("written", out)
