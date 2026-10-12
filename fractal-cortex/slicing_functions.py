"""
slicing_functions.py

Copyright (C) 2025 Daniel Brogan

This file is part of the Fractal Cortex project.
Fractal Cortex is a Multidirectional 5-Axis FDM Slicer.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import trimesh
from trimesh import load_path
import numpy as np
from shapely.geometry import (
    LineString,
    MultiLineString,
    Point,
    Polygon,
    MultiPolygon,
    LinearRing,
    GeometryCollection
)
from shapely.geometry.polygon import orient
from shapely.validation import make_valid
from shapely.plotting import plot_polygon, plot_line
from shapely import affinity
from shapely.prepared import prep
from shapely.ops import unary_union
import time
import concurrent.futures
from operator import add
import os
import warnings
import sys

"""
Contains all calculations related to 3-axis and 5-axis slicing operations.
"""

# Example Inputs
infillType = "Triangular"
buildRadius = 150.0  # mm

# ArtPrint machine settings
ROTARY_STEPPER = "stepper_a"   # Klipper manual_stepper that rotates the bed about Z
ROTATION_SPEED = 25.0          # deg/s
ROTATION_CLEARANCE_Z = 10.0    # mm the head is lifted above the highest printed point before the bed rotates
X_HALF_TRAVEL = 150.0          # mm the bed can move forward or back from the centred position (to confirm)
Y_TRAVEL = 150.0               # mm useful nozzle travel, from the bed's rotation centre to its edge
MAX_SWEEP_DEG = 180.0          # Largest angle a path may wrap around the centre before the bed has to turn while printing it (the nozzle covers half the bed)
MAX_A_STEP_DEG = 0.5           # Largest bed rotation on one G-Code line while the bed turns during a path


# DEFINE FUNCTIONS
def slicing_function(mesh, z):
    """Obtains Trimesh section at a single layer.
        Since this function is only used in 3-axis mode, the slicing direction will always be normal to the build plate.
        The only input that changes is the z-height, which is where each cross section of the STL is taken."""
    output = mesh.section_multiplane(plane_normal=[0, 0, 1], plane_origin=[0, 0, z], heights=[0])
    return output[0]

def slicing_function_5_axis(mesh, normal, start, z):
    """Obtains Trimesh section at a single layer"""
    output = mesh.section_multiplane(plane_normal=normal, plane_origin=start, heights=[z])
    return output[0]

def apply_slicing_function(args):
    """Unpacks list of input arguments and returns an executed function. This is a required step for parallel processing functions with multiple arguments"""
    mesh, z = args
    return slicing_function(mesh, z)

def apply_slicing_function_5_axis(args):
    """Unpacks list of input arguments and returns an executed function. This is a required step for parallel processing functions with multiple arguments"""
    mesh, normal, start, z = args
    return slicing_function_5_axis(mesh, normal, start, z)


def get_initial_shells_for_one_layer(shapely_polygons, lineWidth):
    """Obtains shapely outer shell polygons, taking into account insetting the shell by half the lineWidth"""
    initialShellPolygons = []
    shellPolyList = []
    for poly in shapely_polygons:  # Start with polygons from the mesh that have no offset
        bufferedPoly = poly.buffer(-lineWidth / 2.0, join_style=2)  # Offset (buffer) the polygons inward by a distance of half the lineWidth. This makes it so that when printing, the outer edge of the bead of extruded filament aligns to the outer dimension of the STL. Mitred corners are used.
        initialShellPolygons.append(make_valid(bufferedPoly))       # Make the buffered polygons valid if they aren't already, then add them to a list
        del bufferedPoly                                            # Delete bufferedPoly to save on memory
    shellPolyList.append(initialShellPolygons)                      # List of all buffered polygons for one layer
    return shellPolyList


def get_remaining_shells_for_one_layer(shellPolyList, lineWidth, shellThickness):
    """Obtains any remaining inner shells and also returns innerMostPolygons"""
    volatilePolyList = []
    if shellThickness > 1:
        for shell in range(shellThickness - 1):                                     # For the remaining shells that need to be defined:
            for geometry in shellPolyList[shell]:
                if geometry.geom_type == "Polygon":
                    newBufferedPoly = geometry.buffer(-lineWidth, join_style=2)     # Mitred corners (Changing this may impact infill calculation speed. Need to test this)
                    volatilePolyList.append(make_valid(newBufferedPoly))
                    del newBufferedPoly
                elif geometry.geom_type == "MultiPolygon":                          # If a shell has multiple polygons, process each one individually
                    for poly in geometry.geoms:
                        newBufferedPoly = geometry.buffer(-lineWidth, join_style=2)
                        volatilePolyList.append(make_valid(newBufferedPoly))
                        del newBufferedPoly
            shellPolyList.append(volatilePolyList.copy())                           # Append new buffered polygons to the list after every shell is created
            del volatilePolyList
            volatilePolyList = []
    innerMostPolygons = shellPolyList[-1]                                           # innerMostPolygons are the most inwardly offset shell and therefore defines perimeter of the area where infill will be incorporated
    return shellPolyList, innerMostPolygons


def get_shell_rings_for_one_layer(shellPolyList):
    """Extracts the linearRings that form the outlines of the shell polygons"""
    shellRingsList = []
    for shell in shellPolyList:                                         # Need to get LinearRings from polygons. All rings for each polygon should be adjacent in the final list
        for geometry in shell:
            if geometry.geom_type == "Polygon":
                if len(geometry.exterior.coords) >= 4:                  # Check that the ring contains at least 4 points. To be a ring, there must be at least 3 points to make a closed shape (simplest shape is a triangle). THe 4th point is a repeat of the 1st point so the loop closes.
                    shellRingsList.append(geometry.exterior)            # Extract the exterior rings
                for ring in range(len(geometry.interiors)):
                    if len(geometry.interiors[ring].coords) >= 4:
                        shellRingsList.append(geometry.interiors[ring]) # Extract the interior rings (holes)
            elif geometry.geom_type == "MultiPolygon":
                for poly in geometry.geoms:
                    if poly.geom_type == "Polygon":
                        if len(poly.exterior.coords) >= 4:
                            shellRingsList.append(poly.exterior)
                        for ring in range(len(poly.interiors)):
                            if len(poly.interiors[ring].coords) >= 4:
                                shellRingsList.append(poly.interiors[ring])
    return shellRingsList


def get_shells_for_one_layer(shapely_polygons, lineWidth, shellThickness):
    """Obtains innerMostPolygons and shellRingsList."""
    shellPolyList = get_initial_shells_for_one_layer(shapely_polygons, lineWidth)                                   # Obtain the outer wall shells of the part, taking into account the lineWidth
    shellPolyList, innerMostPolygons = get_remaining_shells_for_one_layer(shellPolyList, lineWidth, shellThickness) # Obtain any remaining inner shells of the part as well as defining the innerMostPolygons, which will be used for infill calculations later
    shellRingsList = get_shell_rings_for_one_layer(shellPolyList)                                                   # Converts the shell polygons list into a list of linearrings, the coordinates of which can be translated easily into GCode later
    return innerMostPolygons, shellRingsList

def apply_get_shells_for_one_layer(args):
    """Unpacks list of input arguments and returns an executed function. This is a required step for parallel processing functions with multiple arguments"""
    shapely_polygons, lineWidth, shellThickness = args
    return get_shells_for_one_layer(shapely_polygons, lineWidth, shellThickness)

def create_brim(shapely_polygons, lineWidth, brim_lines):
    """Creates a brim around the initial layer by offsetting outward multiple times."""
    
    if not isinstance(shapely_polygons, list):  # Check that the input polygons are of the correct datatype
        shapely_polygons = [shapely_polygons]
    
    flattened_polygons = []
    for poly in shapely_polygons:               # Handle multipolygons by extracting individual polygons
        if isinstance(poly, MultiPolygon):
            flattened_polygons.extend(list(poly.geoms))
        else:
            flattened_polygons.append(poly)
    
    brim_ring_list = []
    current_polygons = flattened_polygons
    
    for i in range(brim_lines):                                     # For each offset of the brim:
        brim_layer_rings = []
        brim_layer_polygons = []
        
        for poly in current_polygons:                               # For each polygon in the list of polygons of the initial layer:
            buffered_poly = poly.buffer(lineWidth, join_style=2)    # Offset the polygon by one lineWidth
            
            buffered_poly = make_valid(buffered_poly)               # Make the offset polygon valid if it isn't already
            
            # Collect the exterior ring
            if isinstance(buffered_poly, MultiPolygon):             # If the offset creates a multipolygon:
                for geom in buffered_poly.geoms:                    # Extract the exteriors of the multipolygon
                    brim_layer_rings.append(geom.exterior)
                    brim_layer_polygons.append(geom)
            else:
                brim_layer_rings.append(buffered_poly.exterior)
                brim_layer_polygons.append(buffered_poly)
        
        brim_ring_list.append(brim_layer_rings)                     # Add these brim lines to the overall brim ring list
        current_polygons = brim_layer_polygons                      # Set the current polygons equal to the offset polygons so that the next iteration offsets the polygons that have already been offset
    return brim_ring_list

def fix_polygon_or_multipolygon_ring_orientation(geometry):
    """Fixes the orientation (ccw VS cw) of rings in a polygon or multipolygon"""
    
    if geometry.geom_type == "Polygon":
        returnedGeometry = orient(geometry, sign=1.0)
    elif geometry.geom_type == "MultiPolygon":
        multiPolys = []
        for poly in geometry.geoms:
            multiPolys.append(orient(poly))
        returnedGeometry = MultiPolygon(multiPolys)

    elif geometry.geom_type == "GeometryCollection":
        if geometry.is_empty == False:
            for g in geometry.geoms:
                if g.geom_type == "Polygon":
                    returnedGeometry = orient(geometry, sign=1.0)
                elif geometry.geom_type == "MultiPolygon":
                    multiPolys = []
                    for poly in geometry.geoms:
                        multiPolys.append(orient(poly))
                    returnedGeometry = MultiPolygon(multiPolys)
        else:
            returnedGeometry = geometry
    else:
        returnedGeometry = geometry
    return returnedGeometry

def safe_unary_union(geometries, buffer_value=0.00001):
    """Safely perform unary_union with error handling."""
    if not geometries:
        return Polygon([])
    try:                            # First try a normal unary_union, since in most cases it won't throw an error
        return unary_union(geometries).buffer(buffer_value)
    except Exception as e:
        try:                        # If the above raises an error, try to make each geometry valid and try unary_union again
            valid_geoms = []
            for geom in geometries:
                try:
                    valid_geom = make_valid(geom.buffer(buffer_value))
                    if valid_geom.is_valid and not valid_geom.is_empty:
                        valid_geoms.append(valid_geom)
                except Exception:   # Skip geometries that aren't fixed by the above method
                    continue
            if not valid_geoms:     # If there aren't any valid geometries, just return an empty polygon
                return Polygon([])
                
            return unary_union(valid_geoms)
        except Exception as e:      # If the above still raises an error, just return an empty polygon
            print(f"Failed to create valid geometry: {e}")
            return Polygon([])

def get_manifold_areas_for_one_chunk(innerMostPolygonsList, infillPercentage, shellThickness):
    """Calculates both the manifold infill areas and internal infill areas for an entire chunk of the STL (or the whole STL).
        If 3-Axis mode is used, this script processes the entire STL.
        If 5-Axis mode is used, this script processes one chunk of the STL, which is the 3D volume of the STL sandwiched between two slice planes.
        A manifold area is any area that needs 100% infill.
        If the user specifies any infill percentage less than 100%, the manifold area for each layer is defined as any exposed areas of the innerMostPolygons for that layer (overhangs or underhangs).
        In the above case, these areas are entirely filled in and solid, thus making the outer surface of the part "manifold" (watertight).
        If the user specifies 100% infill, the manifold area for each layer is simply equal to the area defined by all innerMostPolygons for that layer."""

    def build_up_exposed_layers(exposedLayer, layerOverlapArea):
        """Internally thickens the shell of the part in locations where the top or bottom of a layer is exposed.
            The exposed layer is either the current layer or the layer above the current layer (the upper layer).
            The layerOverlapArea is either the area exposed on the underside of the upper layer or the area exposed on the top of the current layer."""
        
        if exposedLayer == "Current_Layer":
            sign = -1
            indexAddition = 0
        elif exposedLayer == "Upper_Layer":
            sign = 1
            indexAddition = 1
        for k in range(1, shellThickness):                                      # For the remainder of the shellThickness
            nextLayerIndex = layer + sign*k + indexAddition                     # If the exposed layer is the current layer, then the next layer will be the one below it. If the exposed layer is the upper layer, then the next layer will be the one above it
            nextLayerArea = unary_union(innerMostPolygonsList[nextLayerIndex])  # Unify all the polygons of the next layer into one "polygon entity" to simplify area comparison calculations
            try:
                nextIntersection = layerOverlapArea.intersection(nextLayerArea) # Figure out where the layerOverlapArea coincides with the next layer. In rare cases, this can raise a divide by zero error, so the exception is conservative
            except:                                                             # If the above raises an exception, this is a conservative fallback wherein the entire next layer is marked for 100% infill
                nextIntersection = nextLayerArea
            if (nextIntersection.is_empty == False) and (nextIntersection.geom_type == "Polygon" or nextIntersection.geom_type == "MultiPolygon"): # If there is any intersection between the next layer and the layer overlap area, then assign that intersection area to be manifold so it can "thicken" the outer surface of the part in that location
                manifoldAreas[nextLayerIndex].append(nextIntersection)
            elif nextIntersection.geom_type == "GeometryCollection":
                for geometry in nextIntersection.geoms:
                    if (geometry.geom_type == "Polygon" or geometry.geom_type == "MultiPolygon"):
                        manifoldAreas[nextLayerIndex].append(geometry)

    def get_upperLayerOverhangArea():  # Overhang area (Bottom of the upper layer that is exposed)
        """Returns any exposed areas of the upper layer (layer above the current layer)"""
        try:
            if currentLayerArea.intersects(upperLayerArea):
                upperLayerOverhangArea = unary_union(upperLayerArea.difference(currentLayerArea))
            else:   # The bottom of the upper layer is completely exposed if it doesn't intersect the current layer
                upperLayerOverhangArea = upperLayerArea
        except:     # If the above raises an exception for whatever reason, this is a conservative fallback wherein the entire upper layer will be marked for 100% infill
            upperLayerOverhangArea = upperLayerArea
        return upperLayerOverhangArea

    def get_currentLayerUnderHangArea():  # Underhang area (Top of the current layer that is exposed)
        """Returns any exposed areas of the current layer"""
        try:
            if currentLayerArea.intersects(upperLayerArea):
                currentLayerUnderHangArea = unary_union(currentLayerArea.difference(upperLayerArea))
            else:                           # The top of the current layer is completely exposed if the layers don't intersect anywhere
                currentLayerUnderHangArea = currentLayerArea
        except:                             # If the above raises an exception, this is a conservative fallback wherein the entire current layer will be marked for 100% infill
            currentLayerUnderHangArea = currentLayerArea
        return currentLayerUnderHangArea

    manifoldAreas = {}
    for key in range(len(slice_levels)):    # Initializing manifoldAreas dictionary (Holds areas to be filled with solid infill)
        manifoldAreas[key] = []

    internalAreas = {}
    for key in range(len(slice_levels)):    # Initializing internalAreas dictionary (Holds areas to be filled in with internal infill)
        internalAreas[key] = []

    warnings.filterwarnings("error")        # This turns warnings into errors so they can be caught

    if infillPercentage >= 1.0:
        """ For 100% infill, all layers are manifold if they contain innerMostPolygon(s) """
        for layer in range(len(slice_levels)):
            currentLayerArea = fix_polygon_or_multipolygon_ring_orientation(unary_union(innerMostPolygonsList[layer]))  # Makes the exterior ring loop CCW and the interior rings (holes) CW if they aren't already
            if currentLayerArea.is_empty == False:                                                                      # If there's area on this layer, add it to the list of manifold areas
                manifoldAreas[layer].append(currentLayerArea)

    elif infillPercentage >= 0.0 and infillPercentage < 1.0:
        """ If infill is >= 0% and < 100%, need to calculate manifold areas and internal areas """
        for layer in range(len(slice_levels)):
            currentLayerArea = fix_polygon_or_multipolygon_ring_orientation(unary_union(innerMostPolygonsList[layer]))

            """ Bottom layers of the chunk:"""
            if layer < shellThickness:
                if currentLayerArea.is_empty == False:
                    manifoldAreas[layer].append(currentLayerArea)
                upperLayerArea = fix_polygon_or_multipolygon_ring_orientation(unary_union(innerMostPolygonsList[layer + 1]))
                upperLayerOverhangArea = get_upperLayerOverhangArea()               # Returns any exposed areas of the upper layer (layer above the current layer)
                if upperLayerOverhangArea.is_empty == False:                        # If any of the bottom of the upper layer is exposed, add that to the list of manifold areas and thicken that local part of the surface
                    manifoldAreas[layer + 1].append(upperLayerOverhangArea)
                    build_up_exposed_layers("Upper_Layer", upperLayerOverhangArea)  # Thicken the outer surface of the part in this location so that it has as many layers as the shellThickness of the walls

                """ Middle layers of the chunk:"""
            elif layer >= shellThickness and layer < len(slice_levels) - shellThickness:
                upperLayerArea = fix_polygon_or_multipolygon_ring_orientation(unary_union(innerMostPolygonsList[layer + 1]))
                currentLayerUnderHangArea = get_currentLayerUnderHangArea()
                upperLayerOverhangArea = get_upperLayerOverhangArea()

                if currentLayerArea.is_empty == False and upperLayerArea.is_empty == False:     # If both the current layer and the layer above have innerMostPolygons:
                    if currentLayerUnderHangArea.is_empty == False:                             # If any of the top of the current layer is exposed, add that area to the manifold areas list and locally thicken the part's surface
                        manifoldAreas[layer].append(currentLayerUnderHangArea)
                        build_up_exposed_layers("Current_Layer", currentLayerUnderHangArea)
                    if upperLayerOverhangArea.is_empty == False:                                # If any of the bottom of the upper layer is exposed, add that area to the manifold areas list and locally thicken the part's surface
                        manifoldAreas[layer + 1].append(upperLayerOverhangArea)
                        build_up_exposed_layers("Upper_Layer", upperLayerOverhangArea)

                elif currentLayerArea.is_empty == False and upperLayerArea.is_empty == True:    # Elif the current layer has innerMostPolygons but the layer above does not:
                    manifoldAreas[layer].append(currentLayerArea)
                    currentLayerUnderHangArea = currentLayerArea                                # The entirety of the current layer is exposed, so make the current layer area manifold and locally thicken the part's surface
                    build_up_exposed_layers("Current_Layer", currentLayerUnderHangArea)

                elif currentLayerArea.is_empty == True and upperLayerArea.is_empty == False:    # Elif the current layer does not have innerMostPolygons but the layer above does:
                    manifoldAreas[layer + 1].append(upperLayerArea)
                    upperLayerOverhangArea = upperLayerArea                                     # The entirety of the upper layer is exposed, so make the upper layer area manifold and locally thicken the part's surface
                    build_up_exposed_layers("Upper_Layer", upperLayerOverhangArea)

                """ Uppermost layers of the chunk up until the uppermost layer:"""
            elif layer >= shellThickness and layer < len(slice_levels) - 1:
                if currentLayerArea.is_empty == False:
                    manifoldAreas[layer].append(currentLayerArea)
                upperLayerArea = fix_polygon_or_multipolygon_ring_orientation(unary_union(innerMostPolygonsList[layer + 1]))
                currentLayerUnderHangArea = get_currentLayerUnderHangArea()
                if currentLayerUnderHangArea.is_empty == False:                                 # If any of the top of the current layer is exposed, add that area to the manifold areas list and locally thicken the part's surface
                    manifoldAreas[layer].append(currentLayerUnderHangArea)
                    build_up_exposed_layers("Current_Layer", currentLayerUnderHangArea)

                """ Uppermost layer of the chunk:"""
            elif layer == len(slice_levels) - 1:
                if currentLayerArea.is_empty == False:                                          # If any of the top of the uppermost layer is exposed (which it usually is), add that area to the manifold areas list and locally thicken the part's surface
                    manifoldAreas[layer].append(currentLayerArea)
                    currentLayerUnderHangArea = currentLayerArea
                    build_up_exposed_layers("Current_Layer", currentLayerUnderHangArea)

        """ Calculating internalAreas (the areas on each layer that will recieve an infill pattern such as "triangular" that is not 100% solid): """
        if infillPercentage != 0:
            """ If infillPercentage is 0%, internal areas will stay as a dictionary of empty lists. Otherwise, complete the following block of code: """
            for layer in range(len(slice_levels)):
                try:
                    currentLayerArea = fix_polygon_or_multipolygon_ring_orientation(safe_unary_union(innerMostPolygonsList[layer])).buffer(0.00001)
                    if len(manifoldAreas[layer]) > 0:                                                                   # If there are any manifold areas on this layer, the internal infill area is the difference between the manifold area and the current layer area
                        combinedManifoldArea = safe_unary_union(manifoldAreas[layer])                                   # Combine all manifold areas on this layer to simplify area comparison calculations
                        if currentLayerArea.equals_exact(combinedManifoldArea, tolerance=0.001):                        # If the manifold area is equivalent to the current layer area, then there is no internal area on that layer
                            pass
                        else:                                                                                           # If the manifold area does not equal the current layer area, then the area of the current layer that doesn't intersect with the manifold area would be equal to the internal area
                            try:
                                difference_result = currentLayerArea.buffer(0.00001).difference(combinedManifoldArea)   # Get the difference between the current layer area and manifold area to determine the internal area
                                if not difference_result.is_empty and difference_result.is_valid:                       # If the difference yields a valid, nonzero area, then add that to the internal areas for this layer
                                    internalAreas[layer].append(difference_result)
                            except Exception as e:
                                print("1. Error Processing Layer", str(layer), str(e))
                    else:                                                                                               # If there are no manifold areas on this layer, then whatever the current layer area is gets set equal to the internal area for this layer
                        internalAreas[layer].append(currentLayerArea)
                except Exception as e:                                                                                  # If there is some problem with the area calculations, just skip this layer to move on
                    print("2. Error Processing Layer", str(layer), str(e))

    warnings.resetwarnings()                                                                                            # Turns warnings back to warnings instead of errors
    return manifoldAreas, internalAreas


def define_alternating_infill_hatches_once(buildRadius, lineWidth):
    """Defines hatch lines that alternate +45/-45 degrees every layer.
        Used for areas with 100% infill as well as the otherwise exposed top and bottom areas of parts."""
    buildRadius = float(buildRadius)                                        # Radius of build plate
    definedSpacing = lineWidth
    Ypositive = np.arange(definedSpacing, buildRadius, definedSpacing)
    Ynegative = -np.flip(Ypositive)
    Ycoords = np.concatenate((Ynegative, [0], Ypositive))
    buildAreaLines_0 = [LineString([(-buildRadius, y), (buildRadius, y)]) for y in Ycoords]                                 # Generate a bunch of horizontal lines over the area of the build plate
    buildAreaLines_plus_45 = [affinity.rotate(k, 45, origin=Point(0, 0), use_radians=False) for k in buildAreaLines_0]      # Rotate a copy of the horizontal lines by +45 deg
    buildAreaLines_minus_45 = [affinity.rotate(k, 135, origin=Point(0, 0), use_radians=False) for k in buildAreaLines_0]    # Rotate a copy of the horizontal lines by -45 deg
    return buildAreaLines_plus_45, buildAreaLines_minus_45


def get_solid_infill_for_one_layer(layerNumber, solidArea, finalShellPoint, buildAreaLines_plus_45, buildAreaLines_minus_45, minInfillLineLength):
    """Returns the infill hatch lines that intersect with any areas designated for 100% infill"""

    # Since the 100% infill layers criss-cross from one layer to the next, we need to determine which angle we need to orient the hatch for the current layer
    if layerNumber % 2 == 0:                        # Even layers get +45 degree lines
        buildAreaLines = buildAreaLines_plus_45
    else:                                           # Odd layer get -45 degree lines
        buildAreaLines = buildAreaLines_minus_45

    layerInfills = [line.intersection(solidArea) for line in buildAreaLines if line.intersects(solidArea)]  # The solid infill is equivalent to the diagonal hatch lines that intersect with the manifold area of the part for this layer

    infillLineStrings = clean_geometry_list_to_only_linestrings(layerInfills, minInfillLineLength)          # Clean the data into only linestrings so it's easier to work with

    del layerInfills
    if infillLineStrings != []:
        results = get_infill_start_location_for_one_layer(infillLineStrings, finalShellPoint)               # The closest infill line to move to after the shells have finished printing
        firstLineIndex = results[0]
        firstLine = LineString(results[1])
        firstLineStartPoint = results[2]
        optimizedInfillPath = optimize_infill_paths_for_one_layer(firstLineIndex, firstLine, firstLineStartPoint, infillLineStrings)    # Optimize the path the nozzle will take to extrude all lines of the solid infill using a nearest neighbors approach
        del results
    else:                                                                                                   # If there aren't any infill inestrings for this layer, we don't have any paths to optimize
        optimizedInfillPath = []
    return optimizedInfillPath


def apply_get_solid_infill_for_one_layer_function(args):
    """Unpacks list of input arguments and returns an executed function. This is a required step for parallel processing functions with multiple arguments"""
    layerNumber, solidArea, finalShellPoint, buildAreaLines_plus_45, buildAreaLines_minus_45, minInfillLineLength = args
    return get_solid_infill_for_one_layer(layerNumber, solidArea, finalShellPoint, buildAreaLines_plus_45, buildAreaLines_minus_45, minInfillLineLength)


def define_monolithic_infill_hatch_once(infillType, buildRadius, lineWidth, infillPercentage):
    """Defines the infill hatch once for infills that don't change their pattern in the Z-direction.
        This way, time doesn't need to be spent redefining the infill shape on every layer.
        Triangular infill is currently the only option."""
    buildRadius = float(buildRadius)                            # Radius of build plate
    if infillPercentage <= 0.0 or infillPercentage >= 1.0:      # Don't define an infill pattern unless the user-specified infill % is greater than 0 and less than 100
        buildAreaHatch = None
    elif infillType == "Triangular":                            # Define the global triangular infill
        definedSpacing = round(3 * (lineWidth / infillPercentage), 3)
        Ypositive = np.arange(definedSpacing, buildRadius, definedSpacing)
        Ynegative = -np.flip(Ypositive)
        Ycoords = np.concatenate((Ynegative, [0], Ypositive))
        buildAreaLines_0 = [LineString([(-buildRadius, y), (buildRadius, y)]) for y in Ycoords]                         # Generate a bunch of horizontal lines over the area of the build plate
        buildAreaLines_60 = [affinity.rotate(k, 60, origin=Point(0, 0), use_radians=False) for k in buildAreaLines_0]   # Rotate a copy of the horizontal lines by +60 deg
        buildAreaLines_120 = [affinity.rotate(k, 120, origin=Point(0, 0), use_radians=False) for k in buildAreaLines_0] # Rotate a copy of the horizontal lines by +120 deg
        buildAreaHatch = buildAreaLines_0 + buildAreaLines_60 + buildAreaLines_120                                      # Add the 0, 60, and 120 lines together to form the triangular infill pattern
    elif infillType == "Grid":                                  # Define the global grid infill (Not yet defined)
        pass
    return buildAreaHatch


def get_internal_infill_for_one_layer(internalArea, finalShellPoint, buildAreaHatch, minInfillLineLength):
    """Returns the infill hatch lines that intersects with any areas with internal infill"""
    
    layerInfills = [line.intersection(internalArea) for line in buildAreaHatch if line.intersects(internalArea)]    # The internal infill is equivalent to the lines of the infill pattern that intersect with the internal area of the part for this layer
    infillLineStrings = clean_geometry_list_to_only_linestrings(layerInfills, minInfillLineLength)                  # Filter input geometry into usable clean data in the form of linestrings
    del layerInfills
    if infillLineStrings != []:                                                                                     # If there are infill linestrings:
        results = get_infill_start_location_for_one_layer(infillLineStrings, finalShellPoint)                       # The closest infill line to move to after the shells have finished printing
        firstLineIndex = results[0]
        firstLine = LineString(results[1])
        firstLineStartPoint = results[2]
        optimizedInfillPath = optimize_infill_paths_for_one_layer(firstLineIndex, firstLine, firstLineStartPoint, infillLineStrings) # Optimize the path the nozzle will take to extrude all lines of the internal infill using a nearest neighbors approach
        del results
    else:                                                                                                           # If there aren't any infill inestrings for this layer, we don't have any paths to optimize
        optimizedInfillPath = []
    return optimizedInfillPath


def apply_get_internal_infill_for_one_layer_function(args):
    """Unpacks list of input arguments and returns an executed function. This is a required step for parallel processing functions with multiple arguments"""
    internalArea, finalShellPoint, buildAreaHatch, minInfillLineLength = args
    return get_internal_infill_for_one_layer(internalArea, finalShellPoint, buildAreaHatch, minInfillLineLength)


def clean_geometry_list_to_only_linestrings(geometryList, minInfillLineLength):
    """Takes geometry list in the form [[geometry], [geometry], ...] and filters out anything that isn't a LineString or can't be converted into a LineString"""

    lineStringsOnlyList = []
    for element in geometryList:
        geometry = element[0]
        if geometry.is_empty == False:
            if geometry.geom_type == "LineString" and geometry.length > minInfillLineLength:    # Filter out lines that are too small to matter that if left in, would increase print time unnecessarily
                lineStringsOnlyList.append(geometry)
            elif geometry.geom_type == "MultiLineString":
                for g in geometry.geoms:
                    if g.geom_type == "LineString" and g.is_empty == False:
                        if g.length > minInfillLineLength:
                            lineStringsOnlyList.append(g)
            elif geometry.geom_type == "GeometryCollection":
                for g in geometry.geoms:
                    if g.geom_type == "LineString" and g.is_empty == False:
                        if g.length > minInfillLineLength:
                            lineStringsOnlyList.append(g)
                    elif geometry.geom_type == "MultiLineString":
                        for g in geometry.geoms:
                            if g.geom_type == "LineString" and g.is_empty == False:
                                if g.length > minInfillLineLength:
                                    lineStringsOnlyList.append(g)
    return lineStringsOnlyList


def get_infill_start_location_for_one_layer(infillLineStrings, finalShellPoint):
    """Calculates the optimal starting point for infill toolpath based on where the nozzle is positioned after finishing the shells of the given layer."""
    
    euclidianDistances = [finalShellPoint.distance(line) for line in infillLineStrings]             # Distances between finalShellPoint and infillLineStrings
    nearestLineIndex = np.argmin(euclidianDistances)                                                # Index of the line that is closest to the final shell point
    del euclidianDistances
    nearestLine = list(infillLineStrings[nearestLineIndex].coords)                                  # Line nearest to finalShellPoint
    nearestLinePointDistances = [finalShellPoint.distance(Point(coord)) for coord in nearestLine]   # Distances between finalShellPoint and the points defining nearestLine
    nearestLineNearestPointIndex = np.argmin(nearestLinePointDistances)                             # Index of the nearest point of the nearest line to the final shell point
    del nearestLinePointDistances
    nearestLineNearestPoint = nearestLine[nearestLineNearestPointIndex]                             # Point on nearestLine closest to finalShellPoint (Random if both are equidistant)
    firstLineIndex = nearestLineIndex
    firstLine = nearestLine
    firstLineStartPoint = nearestLineNearestPoint
    return firstLineIndex, firstLine, firstLineStartPoint


def get_infill_start_locations_for_one_chunk(allLayerInfills_lineStrings, finalShellPoints):
    """Gets the optimal starting points for the infill toolpaths for all layers of a single chunk"""
    
    firstLineindices = []
    firstLines = []
    firstLineStartPoints = []
    for k in range(len(finalShellPoints)):
        if allLayerInfills_lineStrings[k] != []:
            results = get_infill_start_location_for_one_layer(allLayerInfills_lineStrings[k], finalShellPoints[k])
        else:
            results = [None, [], []]
        firstLineindices.append(results[0])
        firstLines.append(LineString(results[1]))
        firstLineStartPoints.append(results[2])
        del results
    return firstLineindices, firstLines, firstLineStartPoints


def optimize_infill_paths_for_one_layer(firstLineIndex, firstLine, firstLineStartPoint, infillLineStrings):
    """Returns a list of infill paths in an optimized order based on a nearest neighbors approach.
        infillLineStrings must be a list of LineStrings."""
    
    firstLineEndPoint = list(firstLine.coords)
    firstLineEndPoint.remove(firstLineStartPoint)

    firstLineEndPoint = Point(firstLineEndPoint[0])
    visitedLineIndex = firstLineIndex
    previousTailPoint = firstLineEndPoint

    optimizedInfillPath = []
    optimizedInfillPath.append([LineString([firstLineStartPoint, list(firstLineEndPoint.coords)[0]])])      # The first infill line to be added to this list has already been determined, so it's the first one that gets added to this list
    for _ in range(len(infillLineStrings) - 1):                                                             # For the remainder of the infill line strings:
        infillLineStrings.pop(visitedLineIndex)                                                             # Remove the previously visited line from the list of "unoptimized" infill lines
        euclidianDistances = [previousTailPoint.distance(otherLine) for otherLine in infillLineStrings]     # Distances between previousTailPoint and remaining infill lines
        nearestLineIndex = np.argmin(euclidianDistances)                                                    # The nearest line is the one with the smallest euclidian distance
        del euclidianDistances
        nearestLine = list(infillLineStrings[nearestLineIndex].coords)                                      # Line nearest to previousTailPoint
        nearestLinePointDistances = [previousTailPoint.distance(Point(coord)) for coord in nearestLine]     # Distances between previousTailPoint and the points defining nearestLine
        nearestLineNearestPointIndex = np.argmin(nearestLinePointDistances)
        del nearestLinePointDistances
        nearestLineNearestPoint = nearestLine[nearestLineNearestPointIndex]                                 # Point on nearestLine closest to previousTailPoint (Random if both are equidistant)
        if nearestLineNearestPointIndex == 0:                                                               # Whatever was decided to be the index of the nearest point of the nearest line, we define the index of that line's farthest point as the other remaining index
            nearestLineFarthestPointIndex = 1
        else:
            nearestLineFarthestPointIndex = 0
        nearestLineFarthestPoint = nearestLine[nearestLineFarthestPointIndex]                               # Point on nearestLine farthest from previousTailPoint
        optimizedInfillPath.append([LineString([nearestLineNearestPoint, nearestLineFarthestPoint])])       # Add nearestLine to the optimizedInfillPath in the correct orientation
        visitedLineIndex = nearestLineIndex
        previousTailPoint = Point(nearestLineFarthestPoint)                                                 # Keep track of where the line left off so that we can use this to compare distances to other line points on the next iteration of the for loop
    return optimizedInfillPath


def get_3D_paths_for_one_layer(adhesion3D, layerTransform3D, shellRingsList, internalInfills, solidInfills):
    """Uses a transformation matrix to convert 2D paths to 3D paths for plotting purposes"""
    adhesionPath3D = []
    shellPath3D = []
    internalInfillPath3D = []
    solidInfillPath3D = []
    
    for adhesionRing in adhesion3D:
        adhesionPoly = Polygon(adhesionRing)
        adhesionPath2D = load_path(adhesionPoly)
        potentialPath3D = adhesionPath2D.to_3D(layerTransform3D)
        del adhesionPoly, adhesionPath2D
        if potentialPath3D.vertices.shape[1] == 3:  # Checking if 3D
            adhesionPath3D.append(potentialPath3D)
        del potentialPath3D
    for shellRing in shellRingsList:
        shellPoly = Polygon(shellRing)
        shellPath2D = load_path(shellPoly)
        potentialPath3D = shellPath2D.to_3D(layerTransform3D)
        del shellPoly, shellPath2D
        if potentialPath3D.vertices.shape[1] == 3:  # Checking if 3D
            shellPath3D.append(potentialPath3D)
        del potentialPath3D
    for infillLines in internalInfills:
        for geometry in infillLines:
            if geometry.geom_type == "LineString":
                infillPath2D = load_path(geometry.coords)
                try:
                    potentialPath3D = infillPath2D.to_3D(layerTransform3D)
                    del infillPath2D
                    if potentialPath3D.vertices.shape[1] == 3:  # Checking if 3D
                        internalInfillPath3D.append(potentialPath3D)
                    del potentialPath3D
                except:
                    pass
    for infillLines in solidInfills:
        for geometry in infillLines:
            if geometry.geom_type == "LineString":
                infillPath2D = load_path(geometry.coords)
                try:
                    potentialPath3D = infillPath2D.to_3D(layerTransform3D)
                    del infillPath2D
                    if potentialPath3D.vertices.shape[1] == 3:  # Checking if 3D
                        solidInfillPath3D.append(potentialPath3D)
                    del potentialPath3D
                except:
                    pass

    return adhesionPath3D, shellPath3D, internalInfillPath3D, solidInfillPath3D


def apply_get_3D_paths_for_one_layer_function(args):
    """Unpacks list of input arguments and returns an executed function. This is a required step for parallel processing functions with multiple arguments"""
    adhesion3D, layerTransform3D, shellRingsList, internalInfills, solidInfills = args
    return get_3D_paths_for_one_layer(adhesion3D, layerTransform3D, shellRingsList, internalInfills, solidInfills)


def all_calculations(mesh, printSettings):
    """Contains all 3-Axis slicing calculations done before plotting"""

    # First, retrieve print settings
    nozzleTemp = float(printSettings[0])
    initialNozzleTemp = float(printSettings[1])
    bedTemp = float(printSettings[2])
    initialBedTemp = float(printSettings[3])
    infillPercentage = float(printSettings[4]) / 100.0
    shellThickness = int(printSettings[5])
    layerHeight = float(printSettings[6])
    lineWidth = float(layerHeight * 2.0)
    minInfillLineLength = lineWidth * 2.0 # Any infill line shorter than this will not be included in the G-Code. This exists to filter out super tiny movements that have negligible impact on print quality and if included would waste time
    printSpeed = float(printSettings[7])
    initialPrintSpeed = float(printSettings[8])
    travelSpeed = float(printSettings[9])
    initialTravelSpeed = float(printSettings[10])
    enableZHop = bool(printSettings[11])
    enableRetraction = bool(printSettings[12])
    retractionDistance = float(printSettings[13])
    retractionSpeed = float(printSettings[14])
    enableSupports = bool(printSettings[15])
    enableBrim = bool(printSettings[16])

    # Define the different types of infill patterns that will be referenced in later calculations
    buildAreaLines_plus_45, buildAreaLines_minus_45 = define_alternating_infill_hatches_once(buildRadius, lineWidth)    # Define plus and minus diagonal infill hatch lines for areas with 100% infill
    buildAreaHatch = define_monolithic_infill_hatch_once(infillType, buildRadius, lineWidth, infillPercentage)          # Define global internal infill pattern once


    # 1) Obtain all mesh sections
    print("Starting timer for Mesh Sections (PARALLEL TASK)")
    start = time.time()
    argsList = zip([mesh]*len(slice_levels), slice_levels)                                                                      # Package list of arguments for use in parallel computing
    with concurrent.futures.ProcessPoolExecutor(max_workers=workerBees) as executor:                                            # Parallelize the slicing function over the list of arguments to slice multiple layers at once to save time
        meshSections = list(executor.map(apply_slicing_function, argsList))
    shapely_polygons_list = [[Polygon(p) for p in layer.polygons_full] if layer is not None else [] for layer in meshSections]  # List of cross-sections of STL model with slice planes
    transform3DList = [layer.metadata["to_3D"] if layer is not None else np.array([]) for layer in meshSections]                # List of 3D transformation matrices that correspond with each slice
    del meshSections                                                                                                            # Delete meshSections from memory to save space since it won't be referenced anymore
    end = time.time() - start
    print("Mesh Sections took ", end, "seconds.", "\n")



    # 2) Obtain all shell offsets
    print("Starting timer for Shells (PARALLEL TASK)")
    start = time.time()
    argsList = zip(shapely_polygons_list, [lineWidth]*len(shapely_polygons_list), [shellThickness]*len(shapely_polygons_list))
    with concurrent.futures.ProcessPoolExecutor(max_workers=workerBees) as executor:
        innerMostPolygonsList, shellRingsListList = zip(*executor.map(apply_get_shells_for_one_layer, argsList))
    end = time.time() - start
    print("Shells took ", end, "seconds.", "\n")



    # 3) Compare overlaps between layers to determine manifold and internal infill areas
    print("Starting timer for Getting Manifold & Internal Areas (SERIES TASK)")                                                         # This task must be performed in series since the infill area definitions depend on geometrical comparisons within the context of adjacent layers
    start = time.time() 
    manifoldAreasDict, internalAreasDict = get_manifold_areas_for_one_chunk(innerMostPolygonsList, infillPercentage, shellThickness)    # Since this is 3-axis mode, one chunk just means the entire STL
    del innerMostPolygonsList
    manifoldAreas = [[safe_unary_union(manifoldAreasDict[key])] for key in manifoldAreasDict]
    internalAreas = [[safe_unary_union(internalAreasDict[key])] for key in internalAreasDict]
    end = time.time() - start
    print("Getting Manifold & Internal Areas took ", end, "seconds.", "\n")



    # 4) Generate & optimize internal infill toolpaths for all layers
    finalShellPoints = []                                                       # List of coords representing the location of the nozzle when shells have finished printing
    lastNozzleLocation = (0.0, 0.0)                                             # Initializing last known location of the nozzle
    for k in range(len(shellRingsListList)):
        if shellRingsListList[k] == []:                                         # If there are no shell rings on this layer, set the final shell point to the last known previous final shell point of the prior layer
            finalShellPoints.append(lastNozzleLocation)
        else:                                                                   # Else if there are shell rings on this layer, set the final shell point to the last point the nozzle navigates to before moving to the next layer
            lastNozzleLocation = Point(shellRingsListList[k][-1].coords[-1])
            finalShellPoints.append(lastNozzleLocation)
    print("Starting timer for Internal Infill & Respective Path Optimization (PARALLEL)")
    start = time.time()
    if infillPercentage <= 0.0 or infillPercentage >= 1.0:                      # If the internal infill percentage is 0% or 100% but not in between, then there is no internal infill, so just fill it with blanks
        optimizedInternalInfills = [[] for _ in range(len(slice_levels))]
    else:                                                                       # If the user specified infill percentage is between 0-100%, optimize the path taken by the nozzle when extruding internal infill to save time during the print
        argsList = zip(internalAreas, finalShellPoints, [buildAreaHatch] * len(internalAreas), [minInfillLineLength] * len(internalAreas),)
        with concurrent.futures.ProcessPoolExecutor(max_workers=workerBees) as executor:
            optimizedInternalInfills = list(executor.map(apply_get_internal_infill_for_one_layer_function, argsList))
    del buildAreaHatch
    end = time.time() - start
    print("Internal Infill took ", end, "seconds.", "\n")



    # 5) Generate & optimize manifold (solid) infill toolpaths for all layers
    print("Starting timer for Manifold Infill & Respective Path Optimization (PARALLEL)")
    start = time.time()
    argsList = zip(layerNumbers, manifoldAreas, finalShellPoints, [buildAreaLines_plus_45]*len(layerNumbers), [buildAreaLines_minus_45]*len(layerNumbers), [minInfillLineLength]*len(layerNumbers))
    with concurrent.futures.ProcessPoolExecutor(max_workers=workerBees) as executor:
        optimizedSolidInfills = list(executor.map(apply_get_solid_infill_for_one_layer_function, argsList))
    del buildAreaLines_plus_45, buildAreaLines_minus_45
    end = time.time() - start
    print("Manifold Infill took ", end, "seconds.", "\n")



    # 6) Calculate Brims if enabled
    print("Starting timer for Adhesion")
    start = time.time()
    initialLayerPolygons = shapely_polygons_list[0]                         # To create the brim we only need to reference the polygons on the initial layer of the print
    adhesionList = [[] for k in range(len(shellRingsListList))]             # This just formats it in a way that can be processed easier when it is referenced later for rendering or writing the gcode
    if enableBrim == True:
        adhesionList[0] = create_brim(initialLayerPolygons, lineWidth, 4)   # Right now the brim is hard coded to have a shell thickness of 4. A user option to change this value can be added later
    else:
        pass
    end = time.time() - start  #
    print("Adhesion calculations took ", end, "seconds.", "\n")

    return transform3DList, adhesionList, shellRingsListList, optimizedInternalInfills, optimizedSolidInfills

def all_5_axis_calculations(mesh, printSettings, slicingDirections):
    global slice_levels
    """Contains all 5-axis slicing calculations done before plotting"""

    # Collecting standard print settings
    nozzleTemp = float(printSettings[0])
    initialNozzleTemp = float(printSettings[1])
    bedTemp = float(printSettings[2])
    initialBedTemp = float(printSettings[3])
    infillPercentage = float(printSettings[4]) / 100.0
    shellThickness = int(printSettings[5])
    layerHeight = float(printSettings[6])
    lineWidth = float(layerHeight * 2.0)
    minInfillLineLength = lineWidth * 2.0    # Any infill line shorter than this will not be included in the G-Code
    printSpeed = float(printSettings[7])
    initialPrintSpeed = float(printSettings[8])
    travelSpeed = float(printSettings[9])
    initialTravelSpeed = float(printSettings[10])
    enableZHop = bool(printSettings[11])
    enableRetraction = bool(printSettings[12])
    retractionDistance = float(printSettings[13])
    retractionSpeed = float(printSettings[14])
    enableSupports = bool(printSettings[15])
    enableBrim = bool(printSettings[16])
    # Collecting slice plane settings
    numSlicingDirections = int(slicingDirections[0])
    startingPositions = slicingDirections[1]
    directions = slicingDirections[2]
    directionsRad = [np.radians(anglePair).tolist() for anglePair in directions]
    slicePlaneList = list(range(numSlicingDirections))
    reversedSlicePlaneList = slicePlaneList[::-1]
    # Define the different types of infill patterns that will be referenced in later calculations
    buildAreaLines_plus_45, buildAreaLines_minus_45 = define_alternating_infill_hatches_once(buildRadius, lineWidth)    # Define plus and minus infill hatch lines for areas with 100% infill
    buildAreaHatch = define_monolithic_infill_hatch_once(infillType, buildRadius, lineWidth, infillPercentage)          # Define global internal infill pattern once

    def spherical_to_normal(theta, phi):
        """Convert spherical coordinates to a normal vector."""
        
        # Convert to Radians
        theta = theta*(np.pi/180.0)
        phi = phi*(np.pi/180.0)
        
        nx = np.sin(theta) * np.cos(phi)
        ny = np.sin(theta) * np.sin(phi)
        nz = np.cos(theta)
        return np.array([nx, ny, nz])
    
    def create_chunkList():
        '''First define each chunk as the remainder of the mesh that's ahead of each respective sliceplane.'''
        
        chunkList = []
        for k in range(int(numSlicingDirections)):
            currentStart = startingPositions[k]
            currentNormal = spherical_to_normal(*directions[k])
            unprocessedChunk = mesh.slice_plane(currentStart, currentNormal, cap=True, face_index=None, cached_dots=None)
            chunkList.append(unprocessedChunk)
        '''
        Then, for each chunk, gradually chisel away material starting from the lattermost chunk and working backwards until the current chunk index.
        This process ensures no collisions between the printhead and the in-process part.
        '''
        for k in slicePlaneList:
            remainingChunk = chunkList[k]
            for r in reversedSlicePlaneList:
                if r > k:
                    latterChunk = chunkList[r]
                    remainingChunk = remainingChunk.difference(latterChunk, check_volume=False)
            if remainingChunk.is_empty == False:
                chunkList[k] = remainingChunk
            else:
                chunkList[k] = None
        return chunkList

    def align_mesh_base_to_xy(mesh, base_point, base_normal):
        """Transform a mesh so its base (defined by a point and normal) aligns with XY plane at Z=0."""
        
        # Convert inputs to numpy arrays
        base_point = np.array(base_point, dtype=float)
        base_normal = np.array(base_normal, dtype=float)
        
        # Normalize the base normal vector
        base_normal = base_normal / np.linalg.norm(base_normal)
        
        # Calculate rotation to align the base normal with the Z axis (0, 0, 1)
        z_axis = np.array([0, 0, 1])
        
        # Find rotation axis and angle
        rotation_axis = np.cross(base_normal, z_axis)
        
        # If base_normal is already aligned with z_axis
        if np.allclose(rotation_axis, 0):
            # Already aligned with Z axis, only need translation
            rotation_matrix = np.eye(3)
        else:
            # Normal case: compute rotation using axis-angle formula
            rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)
            cos_angle = np.dot(base_normal, z_axis)
            angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
            
            K = np.array([
                [0, -rotation_axis[2], rotation_axis[1]],
                [rotation_axis[2], 0, -rotation_axis[0]],
                [-rotation_axis[1], rotation_axis[0], 0]
            ])
            rotation_matrix = np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)
        
        # Create a homogeneous transformation matrix with rotation
        transform = np.eye(4)
        transform[:3, :3] = rotation_matrix
        
        # Apply this rotation
        rotated_mesh = mesh.copy()
        rotated_mesh.apply_transform(transform)
        
        # After rotation, find the z-coordinate of the rotated base point
        rotated_point = rotation_matrix @ base_point
        z_offset = rotated_point[2]
        
        # Create translation matrix to move the base to z=0
        translation = np.eye(4)
        translation[2, 3] = -z_offset
        
        # Apply the translation
        rotated_mesh.apply_transform(translation)
        
        # Combine transforms
        final_transform = translation @ transform
        return rotated_mesh, final_transform

    def inverse_transform_chunks_to_get_respective_slice_levels():
        maxChunkZextents = {}
        chunk_slice_levels = {}
        for k in range(int(numSlicingDirections)):
            currentChunk = chunkList[k]
            if k == 0: # If it's the initial slicing direction, no transformation is needed to get z_extents
                chunkBounds = currentChunk.bounds
                meshBottom = round(chunkBounds[0][2], 3)
                meshTop = round(chunkBounds[1][2], 3)
                if meshBottom <= 0:  # If the bottom of the mesh is at or below the build surface, only slice what's above the build surface
                    z_extents = [0, meshTop]
                elif meshBottom > 0:  # Else if the bottom of the mesh is above the build surface, slice starting at the bottom of the mesh
                    z_extents = [meshBottom, meshTop]
                maxChunkZextents[str(k)] = z_extents
            else: # For all remaining chunks, will need to perform an inverse transform to get z_extents
                currentStart = startingPositions[k]
                currentNormal = spherical_to_normal(*directions[k])
                rotatedChunk = align_mesh_base_to_xy(currentChunk, currentStart, currentNormal)[0]
                chunkBounds = rotatedChunk.bounds
                meshBottom = round(chunkBounds[0][2], 3)
                meshTop = round(chunkBounds[1][2], 3)
                if meshBottom <= 0:  # If the bottom of the mesh is at or below the build surface, only slice what's above the build surface
                    z_extents = [0, meshTop]
                elif meshBottom > 0:  # Else if the bottom of the mesh is above the build surface, slice starting at the bottom of the mesh
                    z_extents = [meshBottom, meshTop]
                maxChunkZextents[str(k)] = z_extents


        for key in maxChunkZextents:
            current_z_extents = maxChunkZextents[key]
            current_z_levels = np.arange(*current_z_extents, step=layerHeight)  # These are the locations where the nozzle tip will be
            chunk_slice_levels[key] = [round(z - (layerHeight / 2), 5) for z in current_z_levels]  # These are the locations where the mesh will be sliced
            del chunk_slice_levels[key][0]

        return chunk_slice_levels

    global stopSlicing
    stopSlicing = False
    def checkForBedNozzleCollisions(chunk, meshSections, transform3DList):
        global stopSlicing
        minAcceptableBedToNozzleClearance = 12.0
        paths_3D = []
        for layer, path2D in enumerate(meshSections): # Turn 2D paths into 3D paths to make global Z values known
            currentTransform = transform3DList[layer]
            paths_3D.append(path2D.to_3D(currentTransform))
            
        sectionPoints = [path.vertices for path in paths_3D]
        sectionZValuesBySlicePlane = [[point[2] for point in section] for section in sectionPoints]

        for layer, section in enumerate(sectionZValuesBySlicePlane):
            theta = directionsRad[chunk][0]
            for z in section:
                if stopSlicing == False:
                    if z <= minAcceptableBedToNozzleClearance: # Only calculate currentBedToNozzleDistance if this point's z value is less than minAcceptableBedToNozzleClearance
                        currentBedToNozzleDistance = abs(z)/np.sin(theta) # We want this to be larger than 12.0 mm
                        if currentBedToNozzleDistance < minAcceptableBedToNozzleClearance: # Invalid Point (Collision detected between bed and nozzle)
                            stopSlicing = True
        return stopSlicing


    chunkList = create_chunkList()
    chunk_slice_levels = inverse_transform_chunks_to_get_respective_slice_levels()

    '''
    Now that we have the slice levels for each chunk, we can loop through each chunk and perform slicing calculations on each chunk separately.
    '''
    chunk_transform3DList = {}
    chunk_shellRingsListList = {}
    chunk_optimizedInternalInfills = {}
    chunk_optimizedSolidInfills = {}
    for k in range(int(numSlicingDirections)): # For each chunk
        print('__________________________________')
        print('Chunk #:', str(k))
        currentChunk = chunkList[k]
        currentStart = startingPositions[k]
        currentNormal = spherical_to_normal(*directions[k])
        slice_levels = chunk_slice_levels[str(k)]
        layerNumbers = list(range(len(slice_levels)))  # Numerical indices corresponding to the layer number
        
        
        # 1) Obtain all mesh sections
        print("Starting timer for currentChunk Mesh Sections (PARALLEL)")
        start = time.time()
        argsList = zip([currentChunk]*len(slice_levels), [currentNormal]*len(slice_levels), [currentStart]*len(slice_levels), slice_levels)  # Need to have an argsList with mesh repeated multiple times to get around problem with having mesh as a non-global variable
        with concurrent.futures.ProcessPoolExecutor(max_workers=workerBees) as executor:
            meshSections = list(executor.map(apply_slicing_function_5_axis, argsList))
        shapely_polygons_list = [[Polygon(p) for p in layer.polygons_full] if layer is not None else [] for layer in meshSections]  # Takes no time (Not worth parallelizing)
        transform3DList = [layer.metadata["to_3D"] if layer is not None else np.array([]) for layer in meshSections]  # Takes no time (Not worth parallelizing)


        # 1.5) Check that all shell offsets won't cause a collision for chunks > 0
        if k > 0: # The initial chunk inherently won't cause any collisions, so only need to analyze the latter chunks
            checkForBedNozzleCollisions(k, meshSections, transform3DList)
        
        del meshSections
        end = time.time() - start
        print("Mesh Sections took ", end, "seconds.", "\n")
        chunk_transform3DList[str(k)] = transform3DList

        if stopSlicing == False:
            # 2) Obtain all shell offsets
            print("Starting timer for Shells (PARALLEL)")
            start = time.time()
            argsList = zip(shapely_polygons_list, [lineWidth] * len(shapely_polygons_list), [shellThickness] * len(shapely_polygons_list),)
            with concurrent.futures.ProcessPoolExecutor(max_workers=workerBees) as executor:
                innerMostPolygonsList, shellRingsListList = zip(*executor.map(apply_get_shells_for_one_layer, argsList))
            end = time.time() - start
            print("Shells took ", end, "seconds.", "\n")
            chunk_shellRingsListList[str(k)] = shellRingsListList
            
            # 3) Compare overlaps between layers to determine manifold and internal infill areas
            print("Starting timer for Getting Manifold & Internal Areas (SERIES)")
            start = time.time()
            manifoldAreasDict, internalAreasDict = get_manifold_areas_for_one_chunk(innerMostPolygonsList, infillPercentage, shellThickness)
            del innerMostPolygonsList
            manifoldAreas = [[safe_unary_union(manifoldAreasDict[key])] for key in manifoldAreasDict]
            internalAreas = [[safe_unary_union(internalAreasDict[key])] for key in internalAreasDict]
            end = time.time() - start
            print("Getting Manifold & Internal Areas took ", end, "seconds.", "\n")

            # 4) Generate & optimize internal infill toolpaths for all layers
            finalShellPoints = []  # List of coords representing the location of the nozzle when shells have finished printing
            lastNozzleLocation = (0.0, 0.0)  # Initializing last known location of the nozzle
            for c in range(len(shellRingsListList)):
                if shellRingsListList[c] == []:
                    finalShellPoints.append(lastNozzleLocation)
                else:
                    lastNozzleLocation = Point(shellRingsListList[c][-1].coords[-1])
                    finalShellPoints.append(lastNozzleLocation)
            print("Starting timer for Internal Infill & Respective Path Optimization (PARALLEL)")
            start = time.time()
            if infillPercentage <= 0.0 or infillPercentage >= 1.0:
                optimizedInternalInfills = [[] for _ in range(len(slice_levels))]
            else:
                argsList = zip(internalAreas, finalShellPoints, [buildAreaHatch] * len(internalAreas), [minInfillLineLength] * len(internalAreas),)
                with concurrent.futures.ProcessPoolExecutor(max_workers=workerBees) as executor:
                    optimizedInternalInfills = list(executor.map(apply_get_internal_infill_for_one_layer_function, argsList))
            end = time.time() - start
            print("Internal Infill took ", end, "seconds.", "\n")
            chunk_optimizedInternalInfills[str(k)] = optimizedInternalInfills

            # 5) Generate & optimize manifold (solid) infill toolpaths for all layers
            print("Starting timer for Manifold Infill & Respective Path Optimization (PARALLEL)")
            start = time.time()
            argsList = zip(layerNumbers, manifoldAreas, finalShellPoints, [buildAreaLines_plus_45] * len(layerNumbers), [buildAreaLines_minus_45] * len(layerNumbers), [minInfillLineLength] * len(layerNumbers))
            with concurrent.futures.ProcessPoolExecutor(max_workers=workerBees) as executor:
                optimizedSolidInfills = list(executor.map(apply_get_solid_infill_for_one_layer_function, argsList))
            end = time.time() - start
            print("Manifold Infill took ", end, "seconds.", "\n")
            chunk_optimizedSolidInfills[str(k)] = optimizedSolidInfills

            if k == 0: # Only calculate adhesion if it's the initial chunk
                # 6) Calculate Brims if enabled
                print("Starting timer for Adhesion")
                start = time.time()
                initialLayerPolygons = shapely_polygons_list[0]
                adhesionList = [[] for k in range(len(shellRingsListList))]
                if enableBrim == True:
                    adhesionList[0] = create_brim(initialLayerPolygons, lineWidth, 4)
                else:
                    pass
                end = time.time() - start
                print("Adhesion calculations took ", end, "seconds.", "\n")            
                
            print('__________________________________')
            print(' ')
        else:
            print('Slicing Stopped. Detected collision between bed and nozzle.')
            break
    
    return chunk_transform3DList, adhesionList, chunk_shellRingsListList, chunk_optimizedInternalInfills, chunk_optimizedSolidInfills


def export_mesh(importedMesh):  # Export the meshes as a dictionary
    return trimesh.exchange.export.export_dict(importedMesh)


def slice_in_3_axes(printSettings, meshData):
    global mesh, slice_levels, layerNumbers

    layerHeight = float(printSettings[6])

    numObjects = len(meshData[0])

    if numObjects > 1:  # If the user wants to slice multiple STLs, merge all STLs into one big STL to simplify slicing
        print("Multiple STLs Input")
        importedMeshList = list(meshData[1].values())
        importedMergedMesh = trimesh.util.concatenate(importedMeshList)
        importedMesh = importedMergedMesh

    elif numObjects == 1:  # Only one STL needs to be sliced
        print("Slicing one STL")
        fileKey = meshData[0][0]
        importedMesh = meshData[1][fileKey]

    mesh = importedMesh.copy()  # Makes a local copy of the imported mesh so it can be pickleable

    meshBounds = mesh.bounds
    meshBottom = meshBounds[0][2]
    meshTop = meshBounds[1][2]

    if meshBottom <= 0:  # If the bottom of the mesh is at or below the build surface, only slice what's above the build surface
        z_extents = [0, meshTop]
    elif meshBottom > 0:  # Else if the bottom of the mesh is above the build surface, slice starting at the bottom of the mesh
        z_extents = [meshBottom, meshTop]

    z_levels = np.arange(*z_extents, step=layerHeight)  # These are the locations where the nozzle tip will be

    slice_levels = [round(z - (layerHeight / 2), 5) for z in z_levels]  # These are the locations where the mesh will be sliced
    print(str(len(slice_levels) - 1), "layers", "\n")
    del slice_levels[0]

    layerNumbers = list(range(len(slice_levels)))  # Numerical indices corresponding to the layer number

    transform3DList, adhesionList, shellRingsListList, optimizedInternalInfills, optimizedSolidInfills = all_calculations(mesh, printSettings)

    return transform3DList, adhesionList, shellRingsListList, optimizedInternalInfills, optimizedSolidInfills

def slice_in_5_axes(printSettings, meshData, slicingDirections):
    global mesh, slice_levels, layerNumbers
    
    # Getting some variables
    layerHeight = float(printSettings[6])
    numObjects = len(meshData[0])


    if numObjects > 1:  # If the user wants to slice multiple STLs, merge all STLs into one big STL to simplify slicing
        print("Multiple STLs Input")
        importedMeshList = list(meshData[1].values())
        importedMergedMesh = trimesh.util.concatenate(importedMeshList)
        importedMesh = importedMergedMesh

    elif numObjects == 1:  # Only one STL needs to be sliced
        print("Slicing one STL")
        fileKey = meshData[0][0]
        importedMesh = meshData[1][fileKey]

    mesh = importedMesh.copy()  # Makes a local copy of the imported mesh so it can be pickleable

    chunk_transform3DList, adhesionList, chunk_shellRingsListList, chunk_optimizedInternalInfills, chunk_optimizedSolidInfills = all_5_axis_calculations(mesh, printSettings, slicingDirections)

    return chunk_transform3DList, adhesionList, chunk_shellRingsListList, chunk_optimizedInternalInfills, chunk_optimizedSolidInfills


def write_5_axis_gcode(newFile, savedFileName, printSettings, startingPositions, directions, chunk_transform3DList, adhesionList, chunk_shellRingsListList, chunk_optimizedInternalInfills, chunk_optimizedSolidInfills):

    def path_to_machine_coordinates(pathPoints, fixedA):
        """Convert one path from bed coordinates to ArtPrint machine coordinates.
        Each input point is (x, y, z) in the bed's own frame, with (0, 0) at the bed's rotation centre.
        Each output point is (X, Y, Z, A, bedPoint): the bed is turned by A degrees, then moved so the
        point lands under the nozzle at (X, Y). The nozzle only reaches the +Y half of the bed (0 <= Y <= Y_TRAVEL),
        so when a path wraps too far around the centre, the bed turns while the path is printed.
        fixedA: bed angle for chunks whose layers are tilted (the bed must not turn during them), else None."""
        bedPoints = np.array(pathPoints, dtype=float)
        if fixedA is not None:
            a = np.radians(fixedA)
            Q = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
            return [(q[0], q[1], q[2], fixedA, p) for q, p in zip(bedPoints @ Q.T, bedPoints)]

        def polar_angle(p, previousAngle):  # Angle of a point around the bed centre, unwrapped to stay close to the previous one
            if np.hypot(p[0], p[1]) < 1e-6:
                return previousAngle
            angle = np.degrees(np.arctan2(p[1], p[0]))
            return angle + 360.0 * np.round((previousAngle - angle) / 360.0)

        angles = [polar_angle(bedPoints[0], 90.0)]
        for p in bedPoints[1:]:
            angles.append(polar_angle(p, angles[-1]))
        sweep = max(angles) - min(angles)
        # Share of the path's turn done by the nozzle side (c = 1: bed stays still; c < 1: bed turns by the rest)
        c = 1.0 if sweep <= MAX_SWEEP_DEG else MAX_SWEEP_DEG / sweep
        midAngle = 0.5 * (max(angles) + min(angles))

        # Straight lines on the bed become curves once the bed turns, so cut segments into small steps.
        # Near the centre the angle changes fast, so keep halving a step until the bed turns little enough on it.
        points = [(bedPoints[0], angles[0])]
        for k in range(1, len(bedPoints)):
            if c == 1.0:  # Bed does not turn on this path: straight lines stay straight
                points.append((bedPoints[k], angles[k]))
                continue
            pending = [1.0]  # Fractions of the segment still to reach, last one first
            done = 0.0
            while pending:
                t = pending[-1]
                p = bedPoints[k-1] + (bedPoints[k] - bedPoints[k-1]) * t
                angle = polar_angle(p, points[-1][1])
                if abs(angle - points[-1][1]) * (1.0 - c) > MAX_A_STEP_DEG and t - done > 1e-6:
                    pending.append(0.5 * (done + t))
                else:
                    points.append((p, angle))
                    done = pending.pop()

        machinePoints = []
        for p, angle in points:
            psi = 90.0 + c * (angle - midAngle)  # Where the point ends up around the centre, seen from the machine (90 = +Y)
            A = psi - angle                       # Bed rotation that puts it there
            r = np.hypot(p[0], p[1])
            machinePoints.append([r * np.cos(np.radians(psi)), r * np.sin(np.radians(psi)), p[2], A, p])
        # Pick the equivalent bed angle (give or take whole turns) that keeps this path's angles closest to zero,
        # so the bed never winds up turn after turn (its heater wires could not follow)
        midA = 0.5 * (max(m[3] for m in machinePoints) + min(m[3] for m in machinePoints))
        shift = -360.0 * np.round(midA / 360.0)
        for m in machinePoints:
            m[3] += shift
        return machinePoints

    def transcribe_pathPoints_to_gcode(pathPoints, PRINT_FEEDRATE, runOnce, newChunk):
        """Write one path as G-Code. Each point is (x, y, z) at mid-layer height, in bed coordinates.
        X, Y, Z and the bed angle A can all change along a path on ArtPrint."""
        global E, previousE

        machinePoints = path_to_machine_coordinates(pathPoints, nozzleState['fixedA'])
        for p, (mx, my, mz, mA, bedPoint) in enumerate(machinePoints):
            X = round(mx, 5)
            Y = round(my, 5)
            Z = round(mz + 0.5 * layerHeight, 5)  # The nozzle tip sits half a layer above the slice plane
            A = round(mA, 4)
            if abs(X) > X_HALF_TRAVEL + 1e-3 or Y < -1e-3 or Y > Y_TRAVEL + 1e-3:
                nozzleState['outOfReach'] += 1
            if p == 0:  # If it's the first point in the path, travel to it
                if enableRetraction == True:
                    openFile.write("G1 F" + str(E_FEEDRATE) + " E" + str(round(E - retractionDistance, 5)) + " ; Retraction" + "\n")
                # Always go up before moving sideways and come down last, so travels never drag the nozzle through the part
                travelZ = max(nozzleState['Z'], Z)
                if enableZHop == True:
                    travelZ += layerHeight
                if newChunk == True:
                    travelZ += 30.0
                    newChunk = False
                if travelZ != nozzleState['Z']:
                    openFile.write("G0 F" + str(G0Z_FEEDRATE) + " Z" + str(round(travelZ, 5)) + "\n")
                if A != nozzleState['A']:
                    openFile.write("G0 F" + str(G0XY_FEEDRATE) + " X" + str(X) + " Y" + str(Y) + " A" + str(A) + "\n")
                else:
                    openFile.write("G0 F" + str(G0XY_FEEDRATE) + " X" + str(X) + " Y" + str(Y) + "\n")
                if Z != travelZ:
                    openFile.write("G0 F" + str(G0Z_FEEDRATE) + " Z" + str(Z) + "\n")
                if enableRetraction == True:
                    openFile.write("G1 F" + str(E_FEEDRATE) + " E" + str(round(E, 5)) + " ; Reversed Retraction" + "\n")
            else:  # If it's any point other than the first point in the path
                s = float(np.linalg.norm(bedPoint - previousBedPoint))  # Real length of filament laid on the part
                E += ((4.0 * layerHeight * lineWidth * s) / (np.pi * (1.75**2)))  # Use conservation of mass to determine length of 1.75mm filament to extrude
                # Klipper times a move by its X/Y/Z length only. When the bed turns, that length differs from the
                # real length on the part, so scale the feedrate to keep the real printing speed.
                machineDistance = ((X - previousX) ** 2 + (Y - previousY) ** 2 + (Z - previousZ) ** 2) ** 0.5
                feedrate = PRINT_FEEDRATE * machineDistance / s if s > 1e-9 and machineDistance > 1e-9 else PRINT_FEEDRATE
                line = "G1 F" + str(round(feedrate, 3)) + " X" + str(X) + " Y" + str(Y)
                if Z != previousZ:
                    line += " Z" + str(Z)
                if A != nozzleState['A']:
                    line += " A" + str(A)
                openFile.write(line + " E" + str(round(E, 5)) + "\n")
                previousE = E

            previousX = X
            previousY = Y
            previousZ = Z
            previousBedPoint = bedPoint
            nozzleState['Z'] = Z
            nozzleState['A'] = A
            nozzleState['maxZ'] = max(nozzleState['maxZ'], Z)

    def rotate_coordinates(coords, phi):
        """Rotate 2D coordinates about the Z-axis by a given angle."""
        
        # Create 2D rotation matrix
        rotation_matrix = np.array([
            [np.cos(phi), -np.sin(phi)],
            [np.sin(phi), np.cos(phi)]
        ])
        
        # Convert input to numpy array if it's not already
        coords_array = np.array(coords)
        
        # Apply rotation matrix
        rotated_coords = coords_array @ rotation_matrix.T
        return rotated_coords

    def transform_paths_to_printable_orientation(layer_paths, transformation_matrices, DCM_AB):  # Works with both linearrings and linestrings
        """
        Convert a list of layers (each containing multiple LineStrings or LinearRings) to 3D line segments,
        applying the appropriate transformation matrix for each layer."""
        
        printable_pathPoints = []
        midLayer_Z_Heights = []

        for layer_idx, (paths, transform) in enumerate(zip(layer_paths, transformation_matrices)):
            layerPaths = []
            # Handle each path in the current layer
            for path in paths:
                
                # Get 2D coordinates from the path
                coords_2d = np.array(path.coords)

                # Transform each point in the path
                coords_3d = np.array([transform_point(point, transform) for point in coords_2d])
                
                printable_coords_3d = np.array([np.matmul(DCM_AB, point3D) for point3D in coords_3d])

                layerPaths.append([(point[0], point[1], point[2]) for point in printable_coords_3d])  # Keep Z: tilted layers are not flat on ArtPrint
            printable_pathPoints.append(layerPaths)
            midLayer_Z_Heights.append(printable_coords_3d[0][2])

        return printable_pathPoints, midLayer_Z_Heights

    def transform_infill_paths_to_printable_orientation(layer_paths, transformation_matrices, DCM_AB):  # Works with both linearrings and linestrings
        """
        Convert a list of layers (each containing multiple LineStrings or LinearRings) to 3D line segments,
        applying the appropriate transformation matrix for each layer."""
        
        printable_pathPoints = []

        for layer_idx, (paths, transform) in enumerate(zip(layer_paths, transformation_matrices)):
            layerPaths = []
            # Handle each path in the current layer
            for line in paths:
                
                # Get 2D coordinates from the line
                coords_2d = np.array(line[0].coords)

                # Transform each point in the line
                coords_3d = np.array([transform_point(point, transform) for point in coords_2d])
                
                printable_coords_3d = np.array([np.matmul(DCM_AB, point3D) for point3D in coords_3d])

                layerPaths.append([(point[0], point[1], point[2]) for point in printable_coords_3d])  # Keep Z: tilted layers are not flat on ArtPrint
            printable_pathPoints.append(layerPaths)

        return printable_pathPoints



    nozzleTemp = float(printSettings[0])
    initialNozzleTemp = float(printSettings[1])
    bedTemp = float(printSettings[2])
    initialBedTemp = float(printSettings[3])
    infillPercentage = float(printSettings[4]) / 100.0
    shellThickness = int(printSettings[5])
    layerHeight = float(printSettings[6])
    lineWidth = float(layerHeight * 2.0)
    printSpeed = float(printSettings[7])
    initialPrintSpeed = float(printSettings[8])
    travelSpeed = float(printSettings[9])
    initialTravelSpeed = float(printSettings[10])
    enableZHop = bool(printSettings[11])
    enableRetraction = bool(printSettings[12])
    retractionDistance = float(printSettings[13])
    retractionSpeed = float(printSettings[14])
    enableSupports = bool(printSettings[15])
    enableBrim = bool(printSettings[16])

    # Setting Feedrates
    E_FEEDRATE = retractionSpeed * 60.0  # mm/min
    G0XY_FEEDRATE = travelSpeed * 60.0  # mm/min
    G1XY_SLOW_FEEDRATE = initialPrintSpeed * 60.0  # mm/min
    G1XY_FEEDRATE = printSpeed * 60.0  # mm/min
    G0Z_FEEDRATE = G0XY_FEEDRATE / 5.0  # mm/min (PLACEHOLDER)

    G1XY_FEEDRATE_SHELLS = G1XY_FEEDRATE  # mm/min (PLACEHOLDER)
    G1XY_FEEDRATE_SOLIDINFILL = G1XY_FEEDRATE  # mm/min (PLACEHOLDER)
    G1XY_FEEDRATE_INTERNALINFILL = G1XY_FEEDRATE  # mm/min (PLACEHOLDER)

    # ArtPrint: the bed only rotates about Z (A axis). It never tilts, so there is no B axis on the bed.
    # A turns the bed so the slope of each tilted chunk faces +Y, where the tilting head will lean (step 2).
    directions = np.array(directions)
    directions[:, 1] = 90 - directions[:, 1]
    directions[0] = [0.0, 0.0]
    AMOVE_Degrees = [sublist[1] for sublist in directions]
    TILT_Degrees = [sublist[0] for sublist in directions]  # Tilt of each chunk's layers, not yet compensated by the head

    nozzleState = {'Z': 30.0, 'maxZ': 30.0, 'A': 0.0, 'fixedA': None, 'outOfReach': 0}  # Current and highest nozzle Z, bed angle, moves the nozzle cannot reach

    openFile = open(newFile, "w")

    """ HEADER """
    openFile.write(";" + "SLICER:       Fractal Cortex" + "\n")
    openFile.write(";" + "FIRMWARE:     Klipper" + "\n")
    openFile.write(";" + "FILE:         " + savedFileName + "\n")
    openFile.write(";" + "--------------------------" + "\n")
    openFile.write(";" + "PRINT SETTINGS:" + "\n")
    openFile.write(";" + "--------------------------" + "\n")
    openFile.write(";" + "initialNozzleTemp:   " + str(initialNozzleTemp) + "\n")
    openFile.write(";" + "nozzleTemp:          " + str(nozzleTemp) + "\n")
    openFile.write(";" + "initialBedTemp:      " + str(initialBedTemp) + "\n")
    openFile.write(";" + "bedTemp:             " + str(bedTemp) + "\n")
    openFile.write(";" + "infillPercentage:    " + str(infillPercentage) + "\n")
    openFile.write(";" + "shellThickness:      " + str(shellThickness) + "\n")
    openFile.write(";" + "layerHeight:         " + str(layerHeight) + "\n")
    openFile.write(";" + "lineWidth:           " + str(lineWidth) + "\n")
    openFile.write(";" + "initialPrintSpeed:   " + str(initialPrintSpeed) + "\n")
    openFile.write(";" + "printSpeed:          " + str(printSpeed) + "\n")
    openFile.write(";" + "initialTravelSpeed:  " + str(initialTravelSpeed) + "\n")
    openFile.write(";" + "travelSpeed:         " + str(travelSpeed) + "\n")
    openFile.write(";" + "enableZHop:          " + str(enableZHop) + "\n")
    openFile.write(";" + "enableRetraction:    " + str(enableRetraction) + "\n")
    if enableRetraction == True:
        openFile.write(";" + "retractionDistance:  " + str(retractionDistance) + "\n")
        openFile.write(";" + "retractionSpeed:     " + str(retractionSpeed) + "\n")
    openFile.write(";" + "enableSupports:      " + str(enableSupports) + "\n")
    openFile.write(";" + "enableBrim:          " + str(enableBrim) + "\n")
    openFile.write(";" + "--------------------------" + "\n")
    openFile.write("G28                   ;Home X, Y, & Z axes" + "\n")
    openFile.write("home_ab               ;Home B Axis and Enable A Axis" + "\n")
    openFile.write("MANUAL_STEPPER STEPPER=" + ROTARY_STEPPER + " GCODE_AXIS=A ;Bed rotation becomes axis A on G1 moves" + "\n")
    openFile.write("M140 S" + str(initialBedTemp) + "            ;Set initial bed temp" + "\n")
    openFile.write("M105                  ;Get nozzle temp" + "\n")
    openFile.write("M190 S" + str(initialBedTemp) + "            ;Set initial bed temperature and wait" + "\n")
    openFile.write("M104 S" + str(initialNozzleTemp) + "           ;Set initial nozzle temperature" + "\n")
    openFile.write("M105                  ;Get nozzle temp" + "\n")
    openFile.write("M109 S" + str(initialNozzleTemp) + "           ;Set initial nozzle temperature and wait" + "\n")
    openFile.write("M82                   ;Absolute extrusion mode" + "\n")
    openFile.write("Z_TILT_ADJUST         ;Z Tilt the Bed" + "\n")
    openFile.write("G0 F3000.0 Z30.0" + "\n")
    openFile.write("G0 X0.0 Y0.0" + "\n")
    openFile.write("DIAG_CENTRALIZE" + "\n")
    openFile.write("G0 X0.0 Y0.0" + "\n")
    openFile.write("G92 E0                ;Reset extruder position" + "\n")
    openFile.write("G1 F2700 E-5" + "\n")
    openFile.write(";END OF HEADER" + "\n")

    # May want to have a command that lays a curve of filament near the OD of the bed as the bed rotates to clear the nozzle before each print

    """ BODY """
    numChunks = len(chunk_transform3DList)

    global E, previousE
    E = 0  # Cumulative length of 1.75mm diameter filament used at every line of G-Code
    previousE = 0

    for key in chunk_transform3DList: # For each chunk
        openFile.write(";" + "Chunk " + key + "\n")
        transform3DList = chunk_transform3DList[key]
        shellRingsListList = chunk_shellRingsListList[key]
        optimizedSolidInfills = chunk_optimizedSolidInfills[key]
        optimizedInternalInfills = chunk_optimizedInternalInfills[key]

        DCM_AB = np.eye(3)  # Toolpaths stay in bed coordinates; the bed angle is worked out point by point when writing G-Code
        tilted = round(TILT_Degrees[int(key)], 5) != 0
        # A tilted chunk is printed with the bed held at one angle, so its slope faces the side the head will lean to.
        # A flat chunk can be printed in any orientation, so the bed is free to turn while it prints.
        nozzleState['fixedA'] = AMOVE_Degrees[int(key)] - 360.0 * np.round(AMOVE_Degrees[int(key)] / 360.0) if tilted else None

        if key != '0': # If it's not the initial chunk, get ready for the new orientation
            newChunk = True
            # Lift the head above everything printed so far before the bed turns under it.
            # The bed moves in X on ArtPrint, so no X/Y "park" move is needed to get out of the way.
            clearanceZ = nozzleState['maxZ'] + ROTATION_CLEARANCE_Z
            openFile.write("G0 F" + str(G0Z_FEEDRATE) + " Z" + str(round(clearanceZ, 5)) + "; Lifting head to clear bed rotation" + "\n")
            nozzleState['Z'] = clearanceZ
            if tilted:
                openFile.write("G0 F" + str(ROTATION_SPEED * 60.0) + " A" + str(round(nozzleState['fixedA'], 4)) + " ; Turning the bed for this chunk" + "\n")
                nozzleState['A'] = round(nozzleState['fixedA'], 4)
                openFile.write('; WARNING: layers of this chunk are tilted ' + str(round(TILT_Degrees[int(key)], 5)) + ' deg. They need the tilting head (not supported yet)' + '\n')
        else:
            newChunk = False

        printable_shell_pathPoints, midLayer_Z_Heights = transform_paths_to_printable_orientation(shellRingsListList, transform3DList, DCM_AB)
        printable_solidInfill_pathPoints = transform_infill_paths_to_printable_orientation(optimizedSolidInfills, transform3DList, DCM_AB)
        printable_internalInfill_pathPoints = transform_infill_paths_to_printable_orientation(optimizedInternalInfills, transform3DList, DCM_AB)

        numLayers = len(transform3DList)
        for k in range(numLayers):  # For each layer
            openFile.write(";" + "Layer " + str(k) + "\n")
            if k == 0:  # If it's the initial layer, use initial layer speeds
                G0XY_FEEDRATE = initialTravelSpeed * 60.0
                G1XY_FEEDRATE_SHELLS = G1XY_SLOW_FEEDRATE
                G1XY_FEEDRATE_SOLIDINFILL = G1XY_SLOW_FEEDRATE
                G1XY_FEEDRATE_INTERNALINFILL = G1XY_SLOW_FEEDRATE
            else:  # For all layers aside from the initial layer, use nominal speeds
                G0XY_FEEDRATE = travelSpeed * 60.0
                G1XY_FEEDRATE_SHELLS = G1XY_FEEDRATE
                G1XY_FEEDRATE_SOLIDINFILL = G1XY_FEEDRATE
                G1XY_FEEDRATE_INTERNALINFILL = G1XY_FEEDRATE
            if k == 1:  # If it's the second layer, transition to nominal print settings
                openFile.write("M104 S" + str(nozzleTemp) + "   ;Set nozzle temperature for remainder of print" + "\n")
                openFile.write("M140 S" + str(bedTemp) + "    ;Set bed temp for remainder of print" + "\n")

            current3DTransform = transform3DList[k]

            if current3DTransform.shape == (4, 4):  # If there is something to print at this layer, do so. Otherwise, there is a vertical gap underneath a floating island in which G-Code shouldn't be generated
                # No separate Z command: every point carries its own Z, since tilted layers are not flat on ArtPrint

                if key == '0' and k == 0 and adhesionList[0] != []: # If it's layer zero of the initial chunk and there is adhesion gcode (brims, skirts) to write, do so
                    """ ADHESION FEATURE TITLE """
                    if enableBrim == True:
                        openFile.write(";" + "Brim" + "\n")

                    flattened_adhesion_rings = sum(adhesionList[0], [])
                    flattened_adhesion_rings.reverse() # Reorder brim rings so the outer brim is printed first. That way the nozzle is primed for the innermost part of the brim that contacts the part

                    adhesions = [[(x, y, midLayer_Z_Heights[0]) for x, y in ring.coords] for ring in flattened_adhesion_rings]  # Brim lies flat on the bed at the first layer height
                    
                    runOnce = True  # True if this is the start of a new feature on this layer (feature means shells, infill, etc.)
                    newChunk = False
                    for a in adhesions:  # G0 commands are written between each path on the same layer
                        pathPoints = a
                        """ XYE COMMANDS """
                        transcribe_pathPoints_to_gcode(pathPoints, G1XY_FEEDRATE_SHELLS, runOnce, newChunk)
                        runOnce = False
                
                if shellRingsListList[k] != []:  # If there are shells on this layer, write GCode for it
                    """ SHELL(S) FEATURE TITLE """
                    openFile.write(";" + "Shell(s)" + "\n")

                    shells = printable_shell_pathPoints[k]

                    runOnce = True  # True if this is the start of a new feature on this layer (feature means shells, infill, etc.)
                    for shell in shells:  # G0 commands are written between each path on the same layer
                        pathPoints = shell
                        
                        """ XYE COMMANDS """
                        transcribe_pathPoints_to_gcode(pathPoints, G1XY_FEEDRATE_SHELLS, runOnce, newChunk)
                        runOnce = False
                        newChunk = False

                if optimizedSolidInfills[k] != []:  # If there is solid infill on this layer, write GCode for it
                    """ SOLID INFILL FEATURE  TITLE """
                    openFile.write(";" + "Solid Infill" + "\n")

                    solidInfills = printable_solidInfill_pathPoints[k]

                    runOnce = True
                    for solidInfill in solidInfills:
                        pathPoints = solidInfill

                        """ XYE COMMANDS """
                        transcribe_pathPoints_to_gcode(pathPoints, G1XY_FEEDRATE_SOLIDINFILL, runOnce, newChunk)
                        runOnce = False
                        newChunk = False

                if optimizedInternalInfills[k] != []:  # If there is internal infill on this layer, write GCode for it
                    """ INTERNAL INFILL FEATURE  TITLE """
                    openFile.write(";" + "Internal Infill" + "\n")

                    internalInfills = printable_internalInfill_pathPoints[k]

                    runOnce = True
                    for internalInfill in internalInfills:
                        pathPoints = internalInfill

                        """ XYE COMMANDS """
                        transcribe_pathPoints_to_gcode(pathPoints, G1XY_FEEDRATE_INTERNALINFILL, runOnce, newChunk)
                        runOnce = False
                        newChunk = False



    """ FOOTER """
    openFile.write(";" + "FOOTER:" + "\n")
    openFile.write("G1 F" + str(E_FEEDRATE) + " E" + str(round(E - 2.0, 5)) + " ; Retract for end of print" + "\n") #######
    openFile.write("G0 F" + str(G0Z_FEEDRATE) + " Z" + str(round(nozzleState['Z'] + layerHeight, 5)) + "\n")
    openFile.write("M140 S0       ;Set bed temp to zero" + "\n")
    openFile.write("M104 S0       ;Set nozzle temp to zero" + "\n")
    openFile.write("G28 Y         ;Home X-Axis" + "\n")
    openFile.write("G28 X         ;Home X-Axis" + "\n")
    openFile.write("G0 F" + str(ROTATION_SPEED * 60.0) + " A0.0 ;Bed rotation back to zero" + "\n")
    openFile.write("MANUAL_STEPPER STEPPER=" + ROTARY_STEPPER + " GCODE_AXIS= ;Back to manual control of the bed rotation" + "\n")
    if nozzleState['outOfReach'] > 0:
        openFile.write("; WARNING: " + str(nozzleState['outOfReach']) + " points are outside the nozzle's reach (check X_HALF_TRAVEL and Y_TRAVEL)" + "\n")
        print("WARNING:", nozzleState['outOfReach'], "points are outside the nozzle's reach")
    openFile.write(";" + "End of GCODE" + "\n")

    openFile.close()


def write_3_axis_gcode(newFile, savedFileName, printSettings, transform3DList, adhesionList, shellRingsListList, optimizedInternalInfills, optimizedSolidInfills):
    
    def transcribe_pathPoints_to_gcode(pathPoints, PRINT_FEEDRATE, runOnce):
        global E, previousE

        for p in range(len(pathPoints)):
            point = pathPoints[p]
            X = round(point[0], 5)
            Y = round(point[1], 5)
            if p == 0:  # If it's the first point in the path
                if enableRetraction == True:
                    openFile.write("G1 F" + str(E_FEEDRATE) + " E" + str(round(E - retractionDistance, 5)) + " ; Retraction" + "\n")
                if enableZHop == True:
                    openFile.write("G0 F" + str(G0Z_FEEDRATE) + " Z" + str(round(nozzleHeight + layerHeight, 5)) + "\n")                    
                if runOnce == True:  # If both the G0 and G1 feedrate for this feature hasn't yet been set on this layer
                    openFile.write("G0 F" + str(G0XY_FEEDRATE) + " X" + str(X) + " Y" + str(Y) + "\n")
                else:  # If it's the first point in the path and G0 and G1 feedrates have already been set
                    openFile.write("G0 F" + str(G0XY_FEEDRATE) + " X" + str(X) + " Y" + str(Y) + "\n") # ("G0 F" + str(G0XY_FEEDRATE) + " X" + str(X) + " Y" + str(Y) + "\n")
                    if enableZHop == True:
                        openFile.write("G0 F" + str(G0Z_FEEDRATE) + " Z" + str(round(nozzleHeight, 5)) + "\n")
                    if enableRetraction == True:
                        openFile.write("G1 F" + str(E_FEEDRATE) + " E" + str(round(E, 5)) + " ; Reversed Retraction" + "\n")
            else:  # If it's any point other than the first point in the path
                s = ((X - previousX) ** 2 + (Y - previousY) ** 2) ** 0.5  # Calculate Euclidian distance
                E += ((4.0 * layerHeight * lineWidth * s) / (np.pi * (1.75**2)))  # Use conservation of mass to determine length of 1.75mm filament to extrude
                if runOnce == True:  # If both the G0 and G1 feedrate for this feature hasn't yet been set on this layer
                    if enableZHop == True:
                        openFile.write("G0 F" + str(G0Z_FEEDRATE) + " Z"+ str(round(nozzleHeight, 5)) + "\n")
                    if enableRetraction == True:
                        openFile.write("G1 F" + str(E_FEEDRATE) + " E" + str(round(previousE, 5)) + " ; Reversed Retraction" + "\n")
                    openFile.write("G1 F" + str(PRINT_FEEDRATE) + " X" + str(X) + " Y"+ str(Y) + " E" + str(round(E, 5)) + "\n")
                    runOnce = False
                else:  # If it's the second (or any following) points on the path and the G0 and G1 feedrates have already been set
                    openFile.write("G1 F" + str(PRINT_FEEDRATE) + " X" + str(X) + " Y"+ str(Y) + " E" + str(round(E, 5)) + "\n") # ("G1 X" + str(X) + " Y" + str(Y) + " E" + str(round(E, 5)) + "\n")
                previousE = E

            previousX = X
            previousY = Y

    nozzleTemp = float(printSettings[0])
    initialNozzleTemp = float(printSettings[1])
    bedTemp = float(printSettings[2])
    initialBedTemp = float(printSettings[3])
    infillPercentage = float(printSettings[4]) / 100.0
    shellThickness = int(printSettings[5])
    layerHeight = float(printSettings[6])
    lineWidth = float(layerHeight * 2.0)
    printSpeed = float(printSettings[7])
    initialPrintSpeed = float(printSettings[8])
    travelSpeed = float(printSettings[9])
    initialTravelSpeed = float(printSettings[10])
    enableZHop = bool(printSettings[11])
    enableRetraction = bool(printSettings[12])
    retractionDistance = float(printSettings[13])
    retractionSpeed = float(printSettings[14])
    enableSupports = bool(printSettings[15])
    enableBrim = bool(printSettings[16])

    # Setting Feedrates
    E_FEEDRATE = retractionSpeed * 60.0  # mm/min
    G0XY_FEEDRATE = travelSpeed * 60.0  # mm/min
    G1XY_SLOW_FEEDRATE = initialPrintSpeed * 60.0  # mm/min
    G1XY_FEEDRATE = printSpeed * 60.0  # mm/min
    G0Z_FEEDRATE = G0XY_FEEDRATE / 5.0  # mm/min (PLACEHOLDER)

    G1XY_FEEDRATE_SHELLS = G1XY_FEEDRATE  # mm/min (PLACEHOLDER)
    G1XY_FEEDRATE_SOLIDINFILL = G1XY_FEEDRATE  # mm/min (PLACEHOLDER)
    G1XY_FEEDRATE_INTERNALINFILL = G1XY_FEEDRATE  # mm/min (PLACEHOLDER)

    openFile = open(newFile, "w")

    """ HEADER """
    openFile.write(";" + "SLICER:       Fractal Cortex" + "\n")
    openFile.write(";" + "FIRMWARE:     Klipper" + "\n")
    openFile.write(";" + "FILE:         " + savedFileName + "\n")
    openFile.write(";" + "--------------------------" + "\n")
    openFile.write(";" + "PRINT SETTINGS:" + "\n")
    openFile.write(";" + "--------------------------" + "\n")
    openFile.write(";" + "initialNozzleTemp:   " + str(initialNozzleTemp) + "\n")
    openFile.write(";" + "nozzleTemp:          " + str(nozzleTemp) + "\n")
    openFile.write(";" + "initialBedTemp:      " + str(initialBedTemp) + "\n")
    openFile.write(";" + "bedTemp:             " + str(bedTemp) + "\n")
    openFile.write(";" + "infillPercentage:    " + str(infillPercentage) + "\n")
    openFile.write(";" + "shellThickness:      " + str(shellThickness) + "\n")
    openFile.write(";" + "layerHeight:         " + str(layerHeight) + "\n")
    openFile.write(";" + "lineWidth:           " + str(lineWidth) + "\n")
    openFile.write(";" + "initialPrintSpeed:   " + str(initialPrintSpeed) + "\n")
    openFile.write(";" + "printSpeed:          " + str(printSpeed) + "\n")
    openFile.write(";" + "initialTravelSpeed:  " + str(initialTravelSpeed) + "\n")
    openFile.write(";" + "travelSpeed:         " + str(travelSpeed) + "\n")
    openFile.write(";" + "enableZHop:          " + str(enableZHop) + "\n")
    openFile.write(";" + "enableRetraction:    " + str(enableRetraction) + "\n")
    if enableRetraction == True:
        openFile.write(";" + "retractionDistance:  " + str(retractionDistance) + "\n")
        openFile.write(";" + "retractionSpeed:     " + str(retractionSpeed) + "\n")
    openFile.write(";" + "enableSupports:      " + str(enableSupports) + "\n")
    openFile.write(";" + "enableBrim:          " + str(enableBrim) + "\n")
    openFile.write(";" + "--------------------------" + "\n")
    openFile.write("G28                   ;Home X, Y, & Z axes" + "\n")
    openFile.write("home_ab               ;Home B Axis and Enable A Axis" + "\n")
    openFile.write("M140 S" + str(initialBedTemp) + "            ;Set initial bed temp" + "\n")
    openFile.write("M105                  ;Get nozzle temp" + "\n")
    openFile.write("M190 S" + str(initialBedTemp) + "            ;Set initial bed temperature and wait" + "\n")
    openFile.write("M104 S" + str(initialNozzleTemp) + "           ;Set initial nozzle temperature" + "\n")
    openFile.write("M105                  ;Get nozzle temp" + "\n")
    openFile.write("M109 S" + str(initialNozzleTemp) + "           ;Set initial nozzle temperature and wait" + "\n")
    openFile.write("M82                   ;Absolute extrusion mode" + "\n")
    openFile.write("Z_TILT_ADJUST         ;Z Tilt the Bed" + "\n")
    openFile.write("G28 Y                 ;Home Y Axis" + "\n")
    openFile.write("G0 F3000.0 Z30.0" + "\n")
    openFile.write("G0 X0.0 Y0.0" + "\n")
    openFile.write("G92 E0                ;Reset extruder position" + "\n")
    openFile.write("G1 F2700 E-5" + "\n")
    openFile.write(";END OF HEADER" + "\n")

    # May want to have a command that lays a curve of filament near the OD of the bed as the bed rotates to clear the nozzle before each print

    """ BODY """
    # Remember to add half the layerHeight to the Z commands
    numLayers = len(transform3DList)
    print(numLayers)

    global E, previousE
    E = 0  # Cumulative length of 1.75mm diameter filament used at every line of G-Code
    previousE = 0
    for k in range(numLayers):  # For each layer
        openFile.write(";" + "Layer " + str(k) + "\n")
        if k == 0:  # If it's the initial layer, use initial layer speeds
            G0XY_FEEDRATE = initialTravelSpeed * 60.0
            G1XY_FEEDRATE_SHELLS = G1XY_SLOW_FEEDRATE
            G1XY_FEEDRATE_SOLIDINFILL = G1XY_SLOW_FEEDRATE
            G1XY_FEEDRATE_INTERNALINFILL = G1XY_SLOW_FEEDRATE
        else:  # For all layers aside from the initial layer, use nominal speeds
            G0XY_FEEDRATE = travelSpeed * 60.0
            G1XY_FEEDRATE_SHELLS = G1XY_FEEDRATE
            G1XY_FEEDRATE_SOLIDINFILL = G1XY_FEEDRATE
            G1XY_FEEDRATE_INTERNALINFILL = G1XY_FEEDRATE
        if k == 1:  # If it's the second layer, transition to nominal print settings
            openFile.write("M104 S" + str(nozzleTemp) + "   ;Set nozzle temperature for remainder of print" + "\n")
            openFile.write("M140 S" + str(bedTemp) + "    ;Set bed temp for remainder of print" + "\n")

        current3DTransform = transform3DList[k]

        if current3DTransform.shape == (4, 4):  # If there is something to print at this layer, do so. Otherwise, there is a vertical gap underneath a floating island in which G-Code shouldn't be generated
            nozzleHeight = current3DTransform[2][3] + 0.5 * layerHeight  # Current height of nozzle

            """ Z COMMAND """
            openFile.write("G0 F" + str(G0Z_FEEDRATE) + " Z" + str(round(nozzleHeight, 5)) + "\n")

            if k == 0 and adhesionList[0] != []: # If it's layer zero and there is adhesion gcode (brims, skirts) to write, do so
                """ ADHESION FEATURE TITLE """
                if enableBrim == True:
                    openFile.write(";" + "Brim" + "\n")

                flattened_adhesion_rings = sum(adhesionList[0], [])
                flattened_adhesion_rings.reverse() # Reorder brim rings so the outer brim is printed first. That way the nozzle is primed for the innermost part of the brim that contacts the part

                adhesions = [list(ring.coords) for ring in flattened_adhesion_rings]
                
                runOnce = True  # True if this is the start of a new feature on this layer (feature means shells, infill, etc.)
                for a in adhesions:  # G0 commands are written between each path on the same layer
                    pathPoints = a
                    """ XYE COMMANDS """
                    transcribe_pathPoints_to_gcode(pathPoints, G1XY_FEEDRATE_SHELLS, runOnce)
                    runOnce = False
            
            if shellRingsListList[k] != []:  # If there are shells on this layer, write GCode for it
                """ SHELL(S) FEATURE TITLE """
                openFile.write(";" + "Shell(s)" + "\n")

                shells = [list(ring.coords) for ring in shellRingsListList[k]]

                runOnce = True  # True if this is the start of a new feature on this layer (feature means shells, infill, etc.)
                for shell in shells:  # G0 commands are written between each path on the same layer
                    pathPoints = shell
                    """ XYE COMMANDS """
                    transcribe_pathPoints_to_gcode(pathPoints, G1XY_FEEDRATE_SHELLS, runOnce)
                    runOnce = False

            if optimizedSolidInfills[k] != []:  # If there is solid infill on this layer, write GCode for it
                """ SOLID INFILL FEATURE  TITLE """
                openFile.write(";" + "Solid Infill" + "\n")

                solidInfills = [list(line[0].coords) for line in optimizedSolidInfills[k]]

                runOnce = True
                for solidInfill in solidInfills:
                    pathPoints = solidInfill
                    """ XYE COMMANDS """
                    transcribe_pathPoints_to_gcode(pathPoints, G1XY_FEEDRATE_SOLIDINFILL, runOnce)
                    runOnce = False

            if optimizedInternalInfills[k] != []:  # If there is internal infill on this layer, write GCode for it
                """ INTERNAL INFILL FEATURE  TITLE """
                openFile.write(";" + "Internal Infill" + "\n")

                internalInfills = [list(line[0].coords) for line in optimizedInternalInfills[k]]

                runOnce = True
                for internalInfill in internalInfills:
                    pathPoints = internalInfill
                    """ XYE COMMANDS """
                    transcribe_pathPoints_to_gcode(pathPoints, G1XY_FEEDRATE_INTERNALINFILL, runOnce)
                    runOnce = False

    """ FOOTER """
    openFile.write(";" + "FOOTER:" + "\n")
    openFile.write("G1 F" + str(E_FEEDRATE) + " E" + str(round(E - 2.0, 5)) + " ; Retract for end of print" + "\n")
    openFile.write("G0 F" + str(G0Z_FEEDRATE) + " Z" + str(round(nozzleHeight + layerHeight, 5)) + "\n")
    openFile.write("M140 S0       ;Set bed temp to zero" + "\n")
    openFile.write("M104 S0       ;Set nozzle temp to zero" + "\n")
    openFile.write("G28 Y         ;Home X-Axis" + "\n")
    openFile.write("G28 X         ;Home X-Axis" + "\n")
    openFile.write("MANUAL_STEPPER STEPPER=stepper_a MOVE=0.0 SPEED=24.43822 SYNC=0" + "\n")
    openFile.write(";" + "A & B Axes Homed" + "\n")
    openFile.write(";" + "End of GCODE" + "\n")

    openFile.close()


def transform_point(point, matrix):
    """Transform a 2D point using a 4x4 transformation matrix."""
    
    # Convert 2D point to homogeneous coordinates
    point_h = np.array([point[0], point[1], 0, 1])
    # Apply transformation
    transformed = matrix @ point_h
    # Return 3D point
    return transformed[:3]


def paths_to_3d_segments(layer_paths, transformation_matrices):  # Works with both linearrings and linestrings
    """
    Convert a list of layers (each containing multiple LineStrings or LinearRings) to 3D line segments,
    applying the appropriate transformation matrix for each layer."""
    
    all_segments = []

    for layer_idx, (paths, transform) in enumerate(zip(layer_paths, transformation_matrices)):
        # Handle each path in the current layer
        for path in paths:
            
            # Get 2D coordinates from the path
            coords_2d = np.array(path.coords)

            # Transform each point in the path
            coords_3d = np.array([transform_point(point, transform) for point in coords_2d])

            # Create segments from the transformed coordinates
            # For LineString: use all points to create segments
            # For LinearRing: last point is same as first, so exclude it
            segments = np.zeros((len(coords_3d) - 1, 6))
            segments[:, :3] = coords_3d[:-1]  # Start points
            segments[:, 3:] = coords_3d[1:]  # End points

            all_segments.append(segments)

    # Combine all segments into a single array
    if all_segments:
        return np.vstack(all_segments)
    else:
        return np.zeros((0, 6))


def convert_slice_data_to_renderable_vertices(transform3DList, adhesionList, shellRingsListList, optimizedInternalInfills, optimizedSolidInfills):
    print("Starting timer for plotting preparation (PARALLEL)")
    start = time.time()

    if isinstance(transform3DList, dict): # If transform3DList was input as a dictionary, that means 5-axis mode was used. Convert into lists in that case
        transform3DList = [num for sublist in transform3DList.values() for num in sublist]
        shellRingsListList = [num for sublist in shellRingsListList.values() for num in sublist]
        optimizedInternalInfills = [num for sublist in optimizedInternalInfills.values() for num in sublist]
        optimizedSolidInfills = [num for sublist in optimizedSolidInfills.values() for num in sublist]

    adhesionPath3D = paths_to_3d_segments(adhesionList[0], [transform3DList[0]]*len(transform3DList))
    
    shellPath3D = paths_to_3d_segments(shellRingsListList, transform3DList)
    
    solidInfillPath3D = paths_to_3d_segments([[ls[0] for ls in layer] for layer in optimizedSolidInfills], transform3DList)

    internalInfillPath3D = paths_to_3d_segments([[ls[0] for ls in layer] for layer in optimizedInternalInfills], transform3DList)

    del transform3DList, adhesionList, shellRingsListList, optimizedInternalInfills, optimizedSolidInfills

    adhesionPathsCombined = adhesionPath3D
    shellPathsCombined = shellPath3D
    internalInfillPathsCombined = internalInfillPath3D
    solidInfillPathsCombined = solidInfillPath3D

    end = time.time() - start
    print("Plotting preparation took ", end, "seconds.", "\n")

    return adhesionPathsCombined, shellPathsCombined, internalInfillPathsCombined, solidInfillPathsCombined


# Set a safe number of workerBees (number of cores) to assign to parallel slicing computation tasks
try:
    maxProcesses = os.cpu_count()       # Retrieves the number of cores your computer has
    workerBees = int(maxProcesses / 2)  # Only use half of the available cores to be safe. It's a good idea to leave some cores for other tasks your computer may have going on
except:
    workerBees = 2                      # Just set number of cores to 2 if the above fails for some reason (perhaps change this to 1 if you want to be extra safe)

