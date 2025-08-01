"""
widget_functions.py

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

import pyglet
from pyglet import event
from pyglet.window import key
import glooey
from glooey import drawing
from tkinter import filedialog
import os
from glooey.helpers import *
from fractal_widgets import *
from slicing_functions import *

"""
Instantiates and places all widgets within the GUI.
Contains all functions that are triggered upon interacting with widgets.
"""

# Adding a custom font
pyglet.font.add_file("Roboto-Regular.ttf")
pyglet.font.load("Roboto")

""" GLOBAL VARIABLES """
# Geometry Action Variables
translateX = 0.0
translateY = 0.0
translateZ = 0.0
rotateX = 0.0
rotateY = 0.0
rotateZ = 0.0
scaleFactor = 100.0

nozzleTemp = 200.0
initialNozzleTemp = nozzleTemp + 5.0
bedTemp = 60.0
initialBedTemp = bedTemp + 5.0
infillPercentage = 20.0
shellThickness = 3
layerHeight = 0.3
printSpeed = 100.0
initialPrintSpeed = printSpeed - 50.0
travelSpeed = 150.0
initialTravelSpeed = travelSpeed - 50.0
enableZHop = True
enableRetraction = True
retractionDistance = 1.0
retractionSpeed = 20.0
enableSupports = False
enableBrim = False

buildPlateBounds = [-150, 150]
zBounds = [0, 300]
rotateBounds = [-720, 720]
scaleBounds = [1, 1000]

bannerHeight = 80
baseGridRight = 450
baseGridTop = 720 - bannerHeight

numSlicingDirections = 1
maxSlicingDirections = 20
startingPositions = [[0.0, 0.0, 0.0]]   # [xPosition, yPosition, zPosition]
directions = [[0.0, 0.0]]               # [theta, phi]
NANs = ["", "-", ".", "-."]

widgetBufferRight = 20
widgetBufferVertical = 10
widgetHeightSpacing = 40
popUpWidgetHeightSpacing = 35

""" WIDGET FUNCTIONS """

def cycle_decks(width, height):  # This cycles through all deck states for all decks so that the visual artifacts don't appear in the lower left corner of the window. This is basically a band-aid for an anomalous problem with glooey/pyglet
    for state in r0GeometryActionDeck.known_states:
        set_geometry_action_deck_states(state)
    set_geometry_action_deck_states(geometryActionState)
    geometryActionBackgroundDeck.set_state(geometryActionBackgroundState)

    for state in r0c0SettingsDeck.known_states:
        set_settings_deck_states(state)
    set_settings_deck_states(settingsState)

def set_geometry_action_deck_states(currentState):
    r0GeometryActionDeck.set_state(currentState)
    r2c0GeometryActionDeck.set_state(currentState)
    r2c1GeometryActionDeck.set_state(currentState)
    r3c0GeometryActionDeck.set_state(currentState)
    r3c1GeometryActionDeck.set_state(currentState)
    r4c0GeometryActionDeck.set_state(currentState)
    r4c1GeometryActionDeck.set_state(currentState)

def set_settings_deck_states(currentState):
    r0c0SettingsDeck.set_state(currentState)
    r0c1SettingsDeck.set_state(currentState)
    r1c0SettingsDeck.set_state(currentState)
    r1c1SettingsDeck.set_state(currentState)
    r2c0SettingsDeck.set_state(currentState)
    r2c1SettingsDeck.set_state(currentState)
    r3c0SettingsDeck.set_state(currentState)
    r3c1SettingsDeck.set_state(currentState)
    r4c0SettingsDeck.set_state(currentState)
    r4c1SettingsDeck.set_state(currentState)
    r5c0SettingsDeck.set_state(currentState)
    r5c1SettingsDeck.set_state(currentState)
    r6c0SettingsDeck.set_state(currentState)
    r6c1SettingsDeck.set_state(currentState)
    r7c0SettingsDeck.set_state(currentState)
    r7c1SettingsDeck.set_state(currentState)

transform3DList = None
adhesionList = None
shellRingsListList = None
optimizedInternalInfills = None
optimizedSolidInfills = None

chunk_transform3DList = None
chunk_shellRingsListList = None
chunk_optimizedInternalInfills = None
chunk_optimizedSolidInfills = None

def disable_all_settings():
    r0c1SettingsDeck.get_widget("material").set_disabled(True)
    r0c1SettingsDeck.get_widget("strength").set_disabled(True)
    r0c1SettingsDeck.get_widget("resolution").set_disabled(True)
    r0c1SettingsDeck.get_widget("movement").set_disabled(True)
    r0c1SettingsDeck.get_widget("supports").set_disabled(True)
    r0c1SettingsDeck.get_widget("adhesion").set_disabled(True)

    r1c1SettingsDeck.get_widget("material").set_disabled(True)
    r1c1SettingsDeck.get_widget("strength").set_disabled(True)
    r1c1SettingsDeck.get_widget("movement").set_disabled(True)

    r2c1SettingsDeck.get_widget("material").set_disabled(True)
    r2c1SettingsDeck.get_widget("movement").set_disabled(True)

    r3c1SettingsDeck.get_widget("material").set_disabled(True)
    r3c1SettingsDeck.get_widget("movement").set_disabled(True)

    r4c1SettingsDeck.get_widget("movement").set_disabled(True)
    r5c1SettingsDeck.get_widget("movement").set_disabled(True)
    r6c1SettingsDeck.get_widget("movement").get_widget("enabled").set_disabled(True)
    r7c1SettingsDeck.get_widget("movement").get_widget("enabled").set_disabled(True)

def enable_all_settings():
    r0c1SettingsDeck.get_widget("material").set_disabled(False)
    r0c1SettingsDeck.get_widget("strength").set_disabled(False)
    r0c1SettingsDeck.get_widget("resolution").set_disabled(False)
    r0c1SettingsDeck.get_widget("movement").set_disabled(False)
    r0c1SettingsDeck.get_widget("supports").set_disabled(False)
    r0c1SettingsDeck.get_widget("adhesion").set_disabled(False)

    r1c1SettingsDeck.get_widget("material").set_disabled(False)
    r1c1SettingsDeck.get_widget("strength").set_disabled(False)
    r1c1SettingsDeck.get_widget("movement").set_disabled(False)

    r2c1SettingsDeck.get_widget("material").set_disabled(False)
    r2c1SettingsDeck.get_widget("movement").set_disabled(False)

    r3c1SettingsDeck.get_widget("material").set_disabled(False)
    r3c1SettingsDeck.get_widget("movement").set_disabled(False)

    r4c1SettingsDeck.get_widget("movement").set_disabled(False)
    r5c1SettingsDeck.get_widget("movement").set_disabled(False)
    r6c1SettingsDeck.get_widget("movement").get_widget("enabled").set_disabled(False)
    r7c1SettingsDeck.get_widget("movement").get_widget("enabled").set_disabled(False)

def toggle_viewMode_layout(parentWidget):
    global \
        transform3DList, \
        adhesionList, \
        shellRingsListList, \
        optimizedInternalInfills, \
        optimizedSolidInfills, \
        chunk_transform3DList, \
        chunk_shellRingsListList, \
        chunk_optimizedInternalInfills, \
        chunk_optimizedSolidInfills
    currentViewMode = parentWidget.currentlyChecked # Prepare or Preview Mode
    printMode = R_viewMode.D_variables["printMode"]
    if currentViewMode == "Preview" and (transform3DList is not None or chunk_transform3DList is not None):
        disable_all_settings() # Gray out all the entry boxes so the user can't change values in Preview mode
        """ Turning slice data into renderable vertices """
        if R_viewMode.preRendered == False: # If the toolpaths haven't been processed for rendering yet, process them, otherwise, don't do anything
                
            if printMode == "3-Axis Mode":
                adhesionPathsCombined, shellPathsCombined, internalInfillPathsCombined, solidInfillPathsCombined = convert_slice_data_to_renderable_vertices(transform3DList, adhesionList, shellRingsListList,optimizedInternalInfills,optimizedSolidInfills)
            elif printMode == "5-Axis Mode":
                adhesionPathsCombined, shellPathsCombined, internalInfillPathsCombined, solidInfillPathsCombined = convert_slice_data_to_renderable_vertices(chunk_transform3DList, adhesionList, chunk_shellRingsListList, chunk_optimizedInternalInfills, chunk_optimizedSolidInfills)

            R_viewMode.D_variables["adhesionPathsCombined"] = adhesionPathsCombined
            R_viewMode.D_variables["shellPathsCombined"] = shellPathsCombined
            R_viewMode.D_variables["internalInfillPathsCombined"] = internalInfillPathsCombined
            R_viewMode.D_variables["solidInfillPathsCombined"] = solidInfillPathsCombined
            

        elif R_viewMode.preRendered == True:
            sliceButtonDeck.set_state("B_saveGcodeAs")
            
    elif currentViewMode == "Prepare":  # If the user switches to Prepare mode, reenable the slice button
        enable_all_settings()           # Reenable all settings
        if R_viewMode.preRendered == True:
            sliceButtonDeck.set_state("B_slice")

def toggle_left_toolbar_layout(parentWidget):
    global geometryActionState, geometryActionBackgroundState
    unhide_geometry_action_pop_up_window()
    selectedAction = parentWidget.currentlyChecked
    if selectedAction == "Translate":
        currentState = "translate"
        geometryActionBackgroundState = "base"

    elif selectedAction == "Rotate":
        currentState = "rotate"
        geometryActionBackgroundState = "base"

    elif selectedAction == "Scale":
        currentState = "scale"
        geometryActionBackgroundState = "scale"

    elif selectedAction == "Deactivated":
        currentState = "blank"
        geometryActionBackgroundState = "deactivated"

    geometryActionBackgroundDeck.set_state(geometryActionBackgroundState)
    geometryActionState = currentState
    set_geometry_action_deck_states(currentState)

def unhide_geometry_action_pop_up_window():
    r0GeometryActionDeck.unhide()

def hide_geometry_action_pop_up_window():
    geometryActionBackgroundDeck.set_state("deactivated")
    set_geometry_action_deck_states("blank")

def toggle_printMode_layout(parentWidget):
    printMode = parentWidget.currentlyChecked
    if printMode == "3-Axis Mode":
        enable_3_axis_mode()
    elif printMode == "5-Axis Mode":
        enable_5_axis_mode()

def toggle_settings_layout(parentWidget):
    global settingsState
    update_values()
    selectedMenu = parentWidget.currentlyChecked
    if selectedMenu == "Material":
        currentState = "material"

    elif selectedMenu == "Strength":
        currentState = "strength"

    elif selectedMenu == "Resolution":
        currentState = "resolution"

    elif selectedMenu == "Movement":
        currentState = "movement"

    elif selectedMenu == "Supports":
        currentState = "supports"

    elif selectedMenu == "Adhesion":
        currentState = "adhesion"

    settingsState = currentState
    set_settings_deck_states(currentState)

def update_mode_placeholder(parentWidget):
    mode = parentWidget.currentlyChecked

def apply_placeholder():
    pass

def update_values():
    global nozzleTemp, E_nozzleTemp, initialNozzleTemp, E_initialNozzleTemp, bedTemp, E_bedTemp, initialBedTemp, E_initialBedTemp
    global infillPercentage, E_infillPercentage, shellThickness, E_shellThickness
    global layerHeight, E_layerHeight
    global \
        printSpeed, \
        E_printSpeed, \
        initialPrintSpeed, \
        E_initialPrintSpeed, \
        travelSpeed, \
        E_travelSpeed, \
        initialTravelSpeed, \
        E_initialTravelSpeed, \
        enableZHop, \
        C_enableZHop, \
        enableRetraction, \
        C_enableRetraction, \
        retractionDistance, \
        E_retractionDistance, \
        retractionSpeed, \
        E_retractionSpeed
    global enableSupports, C_enableSupports
    global enableBrim, C_enableBrim
    try:
        nozzleTemp = r0c1SettingsDeck.get_widget("material").entryBoxEditableLabel.get_text()
        initialNozzleTemp = r1c1SettingsDeck.get_widget("material").entryBoxEditableLabel.get_text()
        bedTemp = r2c1SettingsDeck.get_widget("material").entryBoxEditableLabel.get_text()
        initialBedTemp = r3c1SettingsDeck.get_widget("material").entryBoxEditableLabel.get_text()
    except:
        pass
    try:
        infillPercentage = r0c1SettingsDeck.get_widget( "strength").entryBoxEditableLabel.get_text()
        shellThickness = r1c1SettingsDeck.get_widget("strength").entryBoxEditableLabel.get_text()
    except:
        pass
    try:
        layerHeight = r0c1SettingsDeck.get_widget("resolution").entryBoxEditableLabel.get_text()
    except:
        pass
    try:
        printSpeed = r0c1SettingsDeck.get_widget("movement").entryBoxEditableLabel.get_text()
        initialPrintSpeed = r1c1SettingsDeck.get_widget("movement").entryBoxEditableLabel.get_text()
        travelSpeed = r2c1SettingsDeck.get_widget("movement").entryBoxEditableLabel.get_text()
        initialTravelSpeed = r3c1SettingsDeck.get_widget("movement").entryBoxEditableLabel.get_text()
        enableZHop = r4c1SettingsDeck.get_widget("movement").is_checked
        enableRetraction = r5c1SettingsDeck.get_widget("movement").is_checked
    except:
        pass
    try:
        retractionDistance = r6c1SettingsDeck.get_widget("movement").get_widget("enabled").entryBoxEditableLabel.get_text()
        retractionSpeed = r7c1SettingsDeck.get_widget("movement").get_widget("enabled").entryBoxEditableLabel.get_text()
    except:
        pass
    try:
        enableSupports = r0c1SettingsDeck.get_widget("supports").is_checked
    except:
        pass
    try:
        enableBrim = r0c1SettingsDeck.get_widget("adhesion").is_checked
    except:
        pass

def print_slicing_parameters():
    print("nozzleTemp:", nozzleTemp, "\n")
    print("initialNozzleTemp:", initialNozzleTemp, "\n")
    print("bedTemp:", bedTemp, "\n")
    print("initialBedTemp:", initialBedTemp, "\n")
    print("infillPercentage:", infillPercentage, "\n")
    print("shellThickness:", shellThickness, "\n")
    print("layerHeight:", layerHeight, "\n")
    print("printSpeed:", printSpeed, "\n")
    print("initialPrintSpeed:", initialPrintSpeed, "\n")
    print("travelSpeed:", travelSpeed, "\n")
    print("initialTravelSpeed:", initialTravelSpeed, "\n")
    print("enableZHop:", enableZHop, "\n")
    print("enableRetraction:", enableRetraction, "\n")
    if enableRetraction == True:
        print("Retraction Distance:", retractionDistance, "\n")
        print("Retraction Speed:", retractionSpeed, "\n")
    print("enableSupports:", enableSupports, "\n")
    print("enableBrim:", enableBrim, "\n")

def set_sliceFlag(args):
    sliceButtonDeck.get_widget("B_slice").sliceFlag = True

def slice_function(meshData):
    global \
        printSettings, \
        transform3DList, \
        adhesionList, \
        shellRingsListList, \
        optimizedInternalInfills, \
        optimizedSolidInfills, \
        chunk_transform3DList, \
        chunk_shellRingsListList, \
        chunk_optimizedInternalInfills, \
        chunk_optimizedSolidInfills
    update_values()
    print_slicing_parameters() # Print all slicing parameters
    printSettings = [
        nozzleTemp,
        initialNozzleTemp,
        bedTemp,
        initialBedTemp,
        infillPercentage,
        shellThickness,
        layerHeight,
        printSpeed,
        initialPrintSpeed,
        travelSpeed,
        initialTravelSpeed,
        enableZHop,
        enableRetraction,
        retractionDistance,
        retractionSpeed,
        enableSupports,
        enableBrim,
    ]

    if sliceButtonDeck.get_widget("B_slice").argsList[0][0] != []: # Only proceed with slicing if there are STL's to slice
        printMode = R_printMode.currentlyChecked

        if printMode == "3-Axis Mode":
            (
                transform3DList,
                adhesionList,
                shellRingsListList,
                optimizedInternalInfills,
                optimizedSolidInfills,
            ) = slice_in_3_axes(printSettings, meshData)            

        elif printMode == "5-Axis Mode":
            numSlicingDirections = R_optionMode.D_variables['numSlicingDirections']
            startingPositions = R_optionMode.D_variables['startingPositions']
            directions = R_optionMode.D_variables['directions']
            slicingDirections = [numSlicingDirections, startingPositions, directions]
            
            chunk_transform3DList, adhesionList, chunk_shellRingsListList, chunk_optimizedInternalInfills, chunk_optimizedSolidInfills = slice_in_5_axes(printSettings, meshData, slicingDirections)

        sliceButtonDeck.get_widget("B_slice").clearVBOs = True  # Tracks if there is new slice data (Used for determining when to reset toolpath VBO's for "Preview" mode
        R_viewMode.preRendered = False                          # Next time the "Preview" button is selected, toolpaths need to be regenerated
        R_viewMode.set_disabled(False)

def save_gcode_as(fileName):
    global \
        printSettings, \
        transform3DList, \
        adhesionList, \
        shellRingsListList, \
        optimizedInternalInfills, \
        optimizedSolidInfills, \
        chunk_transform3DList, \
        chunk_shellRingsListList, \
        chunk_optimizedInternalInfills, \
        chunk_optimizedSolidInfills
    print("Save G-Code As...")
    desktopDirectory = os.path.join(os.path.expanduser("~"), "Desktop")
    if len(fileName) == 1:
        fileName_start_index = fileName[0].rfind("/") + 1
        fileName_end_index = fileName[0].index(".stl")
        stlFileName = fileName[0][fileName_start_index:fileName_end_index]
    else:
        stlFileName = "new_file"

    newFile = filedialog.asksaveasfilename(initialdir=desktopDirectory, title="Save Gcode File As...", defaultextension=".gcode", filetypes=(("gcode File", "*.gcode*"), ("Text Document", "*.txt")), initialfile=stlFileName)

    print(newFile)

    if newFile:  # Only write the gcode if the user hits "save". Otherwise, the user canceled out of the menu
        savedFileName_start_index = newFile.rfind("/") + 1
        savedFileName_extension = newFile[newFile.rfind(".") :]
        savedFileName_end_index = newFile.index(savedFileName_extension)
        savedFileName = newFile[savedFileName_start_index:savedFileName_end_index]

        printMode = R_printMode.currentlyChecked

        if printMode == "3-Axis Mode":
            write_3_axis_gcode(
                newFile,
                savedFileName,
                printSettings,
                transform3DList,
                adhesionList,
                shellRingsListList,
                optimizedInternalInfills,
                optimizedSolidInfills
            )
        elif printMode == "5-Axis Mode":
            startingPositions = R_optionMode.D_variables['startingPositions']
            directions = R_optionMode.D_variables['directions']
            
            write_5_axis_gcode(
                newFile,
                savedFileName,
                printSettings,
                startingPositions,
                directions,
                chunk_transform3DList,
                adhesionList,
                chunk_shellRingsListList,
                chunk_optimizedInternalInfills,
                chunk_optimizedSolidInfills
            )

fileKey = 0  # Keeps track of which file has been opened
def select_file():      # Called when the user clicks the file select button
    global selectedNewFile, fileKey
    desktopDirectory = os.path.join(
        os.path.expanduser("~"), "Desktop"
    )
    fileName = filedialog.askopenfilename(
        initialdir=desktopDirectory,
        title="Select an STL File",
        filetypes=(("STL Files", "*.stl"), ("All Files", "*.*")),
    )

    if fileName:        # If a file has been selected
        B_selectFile.D_variables[fileKey] = (
            fileName    # Add the filename to the list of selected files
        )
        fileKey += 1    # Update the fileKey
    return fileName

def checkSlicePlaneValidity():
    """Checks if any of the user-defined slice planes are oriented in "illegal" positions that would cause a collision between the bed and nozzle.
        If a slice plane is determined to cause a collision, this script raises a flag to stop the slicing process from continuing."""
    
    numSlicingDirections = R_optionMode.D_variables['numSlicingDirections']
    slicingDirections = list(range(int(numSlicingDirections)))
    startingPositions = R_optionMode.D_variables['startingPositions']
    directionsDeg = R_optionMode.D_variables['directions']
    directionsRad = [np.radians(anglePair).tolist() for anglePair in directionsDeg]
    meshSections = []
    meshData = B_numSlicingDirections.D_variables['meshData']

    numObjects = len(meshData[0])

    if numObjects > 1:  # If there are multiple STLs, merge all STLs into one big STL
        importedMeshList = list(meshData[1].values())
        importedMergedMesh = trimesh.util.concatenate(importedMeshList)
        importedMesh = importedMergedMesh

    elif numObjects == 1:  # There is only one STL
        fileKey = meshData[0][0]
        importedMesh = meshData[1][fileKey]

    mesh = importedMesh.copy()  # Makes a local copy of the imported mesh so it can be pickleable

    def spherical_to_normal(theta, phi):
        """
        Convert spherical coordinates to a normal vector.
        """
        nx = np.sin(theta) * np.cos(phi)
        ny = np.sin(theta) * np.sin(phi)
        nz = np.cos(theta)
        
        return np.array([nx, ny, nz])

    '''
    First, get cross Sections of where each slice plane intersects with the STL mesh
    '''
    for k in slicingDirections:
        if k > 0: # The initial sliceplane is automatically safe since slicing happens perpendicular to the bed
            start = startingPositions[k]
            normal = spherical_to_normal(*directionsRad[k])
            meshSections.append(mesh.section(plane_normal=normal, plane_origin=start))

    '''
    Second, get points from mesh Sections and extract their Z values
    '''
    sectionPoints = [section.vertices for section in meshSections]
    sectionZValuesBySlicePlane = [[point[2] for point in section] for section in sectionPoints]

    '''
    Third, Calculate the distance between each point to the build surface given theta (bed tilt angle) and each point's Z value
    '''
    minAcceptableBedToNozzleClearance = 12.0                                            # Too much closer than this would result in a collision (if the bed was tilted at 90 degrees)
    D_slicePlaneValidity = {}
    for slicePlane in range(len(sectionZValuesBySlicePlane)):                           # For each slicePlane, get the ZValues and theta value
        ZValues = sectionZValuesBySlicePlane[slicePlane]
        theta = directionsRad[slicePlane+1][0]
        D_slicePlaneValidity[str(slicePlane+1)] = []
        for z in ZValues:                                                               # For each point in the section, calculate the bed to nozzle distance to see if it's passable
            if round(theta, 2) == 0:                                                    # If the sliceplane is mostly pointing up, assume it is safe and also do this step to avoid dividing by zero later
                D_slicePlaneValidity[str(slicePlane+1)].append(True)
            else:                                                                       # For non-vertical slicing normals:
                if z <= minAcceptableBedToNozzleClearance:                              # Only calculate currentBedToNozzleDistance if this point's z value is less than minAcceptableBedToNozzleClearance 
                    currentBedToNozzleDistance = abs(z)/np.sin(theta)                   # We want this to be larger than 12.0 mm
                    if currentBedToNozzleDistance > minAcceptableBedToNozzleClearance:  # Valid (No collision)
                        D_slicePlaneValidity[str(slicePlane+1)].append(True)
                    else:                                                               # Invalid (Collision between bed and nozzle)
                        D_slicePlaneValidity[str(slicePlane+1)].append(False)
                else:                                                                   # If the z value of the point is greater than minAcceptableBedToNozzleClearance, it inherently won't cause a collision and does not require a calculation
                    D_slicePlaneValidity[str(slicePlane+1)].append(True)

    '''
    Lastly, process D_slicePlaneValidity so it shows True or False for a given sliceplane
    '''
    for key in D_slicePlaneValidity:
        if any(slicePlane is False for slicePlane in D_slicePlaneValidity[key]):
            D_slicePlaneValidity[key] = False
        else:
            D_slicePlaneValidity[key] = True

    validityCheck = [all([value for value in D_slicePlaneValidity.values()]), D_slicePlaneValidity]

    R_optionMode.D_variables['D_slicePlaneValidity'] = D_slicePlaneValidity
    return validityCheck

def set_numSlicingDirections():
    global numSlicingDirections, slicingDirectionList, startingPositions, directions, D_slicePlaneValidity
    numSlicingDirections = S_numSlicingDirections.entryBox.entryBoxEditableLabel.get_text()
    if numSlicingDirections in NANs:
        numSlicingDirections = 2
    def get_maxHeightOfAllSTLs():
        # Find the max height of the STL (or collection of STL's) to evenly space the startingPositions
        heights = []
        meshData = B_numSlicingDirections.D_variables['meshData']
        importedMeshList = list(meshData[1].values())
        for k in importedMeshList:
            heights.append(k.bounds[1][2])

        maxHeight = max(heights)
        return maxHeight

    maxHeight = get_maxHeightOfAllSTLs()
    verticalSpacing = float(maxHeight/int(numSlicingDirections))
    D_slicePlaneValidity = {}
    for k in range(int(numSlicingDirections)):
        D_slicePlaneValidity[str(k)] = True                                     # Initialize all sliceplanes as valid until proven otherwise
        
    for k in range(int(numSlicingDirections)-1):
        startingPositions.append([0.0, 0.0, verticalSpacing+k*verticalSpacing]) # Vertically space out slicing directions when initially spawned
    directions = [[0.0, 0.0]] * int(numSlicingDirections)
    slicingDirectionList = list(range(2, int(numSlicingDirections) + 1))        # List of slicing direction numbers starting at 2 and going until n

    R_optionMode.D_variables['numSlicingDirections'] = numSlicingDirections     # Update this so it can be retrieved from the main script
    R_optionMode.D_variables['startingPositions'] = startingPositions
    R_optionMode.D_variables['directions'] = directions
    R_optionMode.D_variables['D_slicePlaneValidity'] = D_slicePlaneValidity
    
    enable_5_axis_mode()

    update_current_selection()

def add_new_slicing_direction():
    global slicingDirectionList, startingPositions, directions, D_slicePlaneValidity
    if slicingDirectionList[-1] < maxSlicingDirections:
        newMaxValue = slicingDirectionList[-1] + 1
        lastZ = startingPositions[-1][2]
        startingPositions.append([0.0, 0.0, float(lastZ)+5.0])                                              # Spawn the next slicePlane slightly above the last one
        directions.append([0.0, 0.0])

        S_currentSlicingDirection.update_maxValue(newMaxValue)                                              # Update the size of slicingDirectionList
        slicingDirectionList = list(range(2, newMaxValue + 1))                                              # Update slicingDirectionList
        S_currentSlicingDirection.entryBox.entryBoxEditableLabel.set_text(str(slicingDirectionList[-1]))    # Set the current text to the last index

        D_slicePlaneValidity[str(newMaxValue-1)] = True
        
        update_current_selection()

        R_optionMode.D_variables['numSlicingDirections'] = newMaxValue # Update this so it can be retrieved from the main script

def remove_slicing_direction():
    global slicingDirectionList, startingPositions, directions, D_slicePlaneValidity
    if slicingDirectionList[-1] > 2:
        newMaxValue = slicingDirectionList[-1] - 1
        S_currentSlicingDirection.update_maxValue(newMaxValue)                                              # Update the size of slicingDirectionList
        slicingDirectionList.pop(-1)                                                                        # Update slicingDirectionList
        startingPositions.pop(-1)
        directions.pop(-1)

        S_currentSlicingDirection.entryBox.entryBoxEditableLabel.set_text(str(slicingDirectionList[-1]))    # Set the current text to the last index

        del D_slicePlaneValidity[str(newMaxValue)]
        
        update_current_selection()

        R_optionMode.D_variables['numSlicingDirections'] = newMaxValue                                      # Update this so it can be retrieved from the main script

def remove_all_slicing_directions():
    global numSlicingDirections, slicingDirectionList, startingPositions, directions, D_slicePlaneValidity
    numSlicingDirections = 1
    slicingDirectionList = []
    startingPositions = [[0.0, 0.0, 0.0]]
    directions = [[0.0, 0.0]]
    S_numSlicingDirections.entryBox.entryBoxEditableLabel.set_text(str(2))      # Reset the current text to 2
    S_currentSlicingDirection.entryBox.entryBoxEditableLabel.set_text(str(2))   # Reset the current text to 2
    slicingDirectionBoard.clear()                                               # This line makes it so that the units text doesn't appear in the lower left corner of the window

    D_slicePlaneValidity = {'0': True}

    R_optionMode.D_variables['numSlicingDirections'] = 1 # Update this so it can be retrieved from the main script
    R_optionMode.D_variables['startingPositions'] = [[0.0, 0.0, 0.0]]
    R_optionMode.D_variables['directions'] = [[0.0, 0.0]]
    
    enable_5_axis_mode()

def update_starting_positions():  # This is called every time the up or down button is pressed on a starting position spin box. This should also be called every time the text is updated on them
    global startingPositions
    currentIndex = (int(S_currentSlicingDirection.entryBox.entryBoxEditableLabel.get_text()) - 1)
    xPosition = S_startingX.entryBox.entryBoxEditableLabel.get_text()
    yPosition = S_startingY.entryBox.entryBoxEditableLabel.get_text()
    zPosition = S_startingZ.entryBox.entryBoxEditableLabel.get_text()
    if xPosition in NANs:
        xPosition = 0.0
    else:
        xPosition = float(xPosition)

    if yPosition in NANs:
        yPosition = 0.0
    else:
        yPosition = float(yPosition)

    if zPosition in NANs:
        zPosition = 0.0
    else:
        zPosition = float(zPosition)
    startingPositions[currentIndex] = [xPosition, yPosition, zPosition]

def update_directions():
    global directions
    currentIndex = (int(S_currentSlicingDirection.entryBox.entryBoxEditableLabel.get_text()) - 1)
    theta = S_theta.entryBox.entryBoxEditableLabel.get_text()
    phi = S_phi.entryBox.entryBoxEditableLabel.get_text()
    if theta in NANs:
        theta = 0.0
    else:
        theta = float(theta)
    if phi in NANs:
        phi = 0.0
    else:
        phi = float(phi)
    directions[currentIndex] = [theta, phi]

def update_current_selection():
    global startingPositions
    currentSlicingDirection = S_currentSlicingDirection.entryBox.entryBoxEditableLabel.get_text()
    if currentSlicingDirection == "":
        currentIndex = 1
    else:
        currentIndex = int(S_currentSlicingDirection.entryBox.entryBoxEditableLabel.get_text()) - 1
    S_startingX.entryBox.entryBoxEditableLabel.set_text(str(startingPositions[currentIndex][0]))
    S_startingY.entryBox.entryBoxEditableLabel.set_text(str(startingPositions[currentIndex][1]))
    S_startingZ.entryBox.entryBoxEditableLabel.set_text(str(startingPositions[currentIndex][2]))
    S_theta.entryBox.entryBoxEditableLabel.set_text(str(directions[currentIndex][0]))
    S_phi.entryBox.entryBoxEditableLabel.set_text(str(directions[currentIndex][1]))

def update_placeholder():
    pass

""" Functions for adding widgets """

def enable_3_axis_mode():
    R_optionMode.D_variables['numSlicingDirections'] = 1
    R_optionMode.D_variables['startingPositions'] = [[0.0, 0.0, 0.0]]
    R_optionMode.D_variables['directions'] = [[0.0, 0.0]]
    
    for w in startingBoxWidgets:
        w.hide()
    for w in slicingDirectionsBoxWidgets:
        w.hide()
    lowerLine.hide()
    slicingDirectionBoard.clear()
    settingsBoard.add(
        R_optionMode,
        center_x_percent=0.5,
        top=baseGridTop - 2 * widgetHeightSpacing - 2 * widgetBufferVertical,
    )
    settingsBoard.add(
        r0c0SettingsDeck,
        left=widgetBufferRight,
        top=13 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    settingsBoard.add(
        r0c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=13 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    settingsBoard.add(
        r1c0SettingsDeck,
        left=widgetBufferRight,
        top=12 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    settingsBoard.add(
        r1c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=12 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    settingsBoard.add(
        r2c0SettingsDeck,
        left=widgetBufferRight,
        top=11 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    settingsBoard.add(
        r2c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=11 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    settingsBoard.add(
        r3c0SettingsDeck,
        left=widgetBufferRight,
        top=10 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    settingsBoard.add(
        r3c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=10 * widgetHeightSpacing - widgetBufferVertical - 18,
    )

    settingsBoard.add(
        r4c0SettingsDeck,
        left=widgetBufferRight,
        top=9 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    settingsBoard.add(
        r4c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=9 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    
    settingsBoard.add(
        r5c0SettingsDeck,
        left=widgetBufferRight,
        top=8 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    settingsBoard.add(
        r5c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=8 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    settingsBoard.add(
        r6c0SettingsDeck,
        left=widgetBufferRight,
        top=7 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    settingsBoard.add(
        r6c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=7 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    settingsBoard.add(
        r7c0SettingsDeck,
        left=widgetBufferRight,
        top=6 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    settingsBoard.add(
        r7c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=6 * widgetHeightSpacing - widgetBufferVertical - 18,
    )
    
    cycle_decks(0, 0)

def display_starting_box():
    settingsBoard.add(I_startingBox, center_x_percent=0.5, top=baseGridTop - 2 * widgetHeightSpacing - 2 * widgetBufferVertical)
    slicingDirectionBoard.add(S_numSlicingDirections, left=285, top=baseGridTop - 2 * widgetHeightSpacing - 2 * widgetBufferVertical - 13,)
    slicingDirectionBoard.add(B_numSlicingDirections, left=355, top=baseGridTop - 2 * widgetHeightSpacing - 2 * widgetBufferVertical - 11,)

def display_slicing_directions_box():
    height = 320

    rightToolBarBoard.add(I_slicingDirectionBox, left=21, bottom=5)

    rightToolBarTopBoard.add(S_currentSlicingDirection, left=285, top=height - 2 * widgetHeightSpacing - 2 * widgetBufferVertical - 13)
    S_currentSlicingDirection.update_maxValue(int(numSlicingDirections))  # Update the size of slicingDirectionList

    rightToolBarTopBoard.add(B_addNew, left=352, top=height - 2 * widgetHeightSpacing - 2 * widgetBufferVertical - 11)
    rightToolBarTopBoard.add(B_remove, left=391, top=height - 2 * widgetHeightSpacing - 2 * widgetBufferVertical - 11)
    rightToolBarTopBoard.add(B_removeAll, left=229, top=height - 275)

    rightToolBarTopBoard.add(S_startingX, left=90, top=height - 180)
    rightToolBarTopBoard.add(S_startingY, left=90, top=height - 220)
    rightToolBarTopBoard.add(S_startingZ, left=90, top=height - 260)
    rightToolBarTopBoard.add(S_theta, left=285, top=height - 180)
    rightToolBarTopBoard.add(S_phi, left=285, top=height - 220)

def enable_5_axis_mode():
    global numSlicingDirections, startingPositions, directions

    R_optionMode.D_variables['numSlicingDirections'] = numSlicingDirections
    R_optionMode.D_variables['startingPositions'] = startingPositions
    R_optionMode.D_variables['directions'] = directions

    if (numSlicingDirections == 1):  # If the user has not yet specified the number of slicing directions, display the starter box
        spacing = 68
        display_starting_box()
        B_numSlicingDirections.D_variables['applied'] = False
        for w in slicingDirectionsBoxWidgets:
            w.hide()
        for w in startingBoxWidgets:
            w.unhide()
    else:  # Display the slicing direction box
        B_numSlicingDirections.D_variables['applied'] = True
        spacing = 0
        display_slicing_directions_box()
        for w in startingBoxWidgets:
            w.hide()
        for w in slicingDirectionsBoxWidgets:
            w.unhide()

    lowerLine.unhide()
    settingsBoard.add(
        lowerLine,
        left=0,
        top=baseGridTop - 2 * widgetHeightSpacing - widgetBufferVertical - spacing,
    )
    settingsBoard.add(
        R_optionMode,
        center_x_percent=0.5,
        top=baseGridTop - 2 * widgetHeightSpacing - 2 * widgetBufferVertical - spacing,
    )
    settingsBoard.add(
        r0c0SettingsDeck,
        left=widgetBufferRight,
        top=13 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r0c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=13 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r1c0SettingsDeck,
        left=widgetBufferRight,
        top=12 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r1c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=12 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r2c0SettingsDeck,
        left=widgetBufferRight,
        top=11 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r2c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=11 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r3c0SettingsDeck,
        left=widgetBufferRight,
        top=10 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r3c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=10 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r4c0SettingsDeck,
        left=widgetBufferRight,
        top=9 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r4c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=9 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r5c0SettingsDeck,
        left=widgetBufferRight,
        top=8 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r5c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=8 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r6c0SettingsDeck,
        left=widgetBufferRight,
        top=7 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r6c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=7 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r7c0SettingsDeck,
        left=widgetBufferRight,
        top=6 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    settingsBoard.add(
        r7c1SettingsDeck,
        right=baseGridRight - widgetBufferRight,
        top=6 * widgetHeightSpacing - widgetBufferVertical - 15 - spacing,
    )
    
    cycle_decks(0, 0)

def initialize_all_widgets(gui, windowHeight):
    """CONTAINER WIDGETS"""
    # Entire window
    gui.add(baseGrid)
    baseGrid.clear()
    # R0 C0
    baseGrid.add(0, 0, topLeftGrid)
    topLeftGrid.add(0, 1, topLeftStack1)
    topLeftStack1.insert(Dark_Gray_Background(), 0)
    # R0 C1
    # R1 C0
    leftToolBarStack.insert(leftToolBarBoard, 0)
    leftToolBarStack.insert(leftToolBarTopBoard, 1)
    rightToolBarStack.insert(rightToolBarBoard, 0)
    rightToolBarStack.insert(rightToolBarTopBoard, 1)
    
    # R1 C1
    baseGrid.add(1, 1, settingsStack)
    settingsStack.insert(Light_Gray_Background(), 0)
    settingsStack.insert(settingsBoard, 1)
    settingsStack.insert(slicingDirectionBoard, 2)
    
    # R2 C0

    # R2 C1
    baseGrid.add(2, 1, Light_Gray_Background())

    """ Adjust container parameters """
    baseGrid.set_row_height(0, bannerHeight)
    baseGrid.set_col_width(1, baseGridRight)
    baseGrid.set_row_height(1, baseGridTop)
    lowerLeftTop = windowHeight - (bannerHeight + baseGridTop)
    topLeftGrid.set_col_width(0, 315)

    """ Add widgets to containers """
    # R0 C0
    topLeftStack1.add(R_viewMode)
    topLeftGrid.add(0, 0, I_logo)
    # R0 C1
    baseGrid.add(0, 1, Dark_Gray_Background())
    # R1 C0
    leftToolBarBoard.add(B_selectFile, left=0, top=baseGridTop)
    leftToolBarBoard.add(R_geometryAction, left=0, bottom=5)
    leftToolBarBoard.add(geometryActionBackgroundDeck, left=60, bottom=5)
    leftToolBarTopBoard.add(r0GeometryActionDeck,center_x=130, bottom=120)
    leftToolBarTopBoard.add(r2c0GeometryActionDeck, left=70, bottom=115 - popUpWidgetHeightSpacing + 15)
    leftToolBarTopBoard.add(r2c1GeometryActionDeck,left=85, bottom=115 - popUpWidgetHeightSpacing + 10)
    leftToolBarTopBoard.add(r3c0GeometryActionDeck,left=70, bottom=115 - 2 * popUpWidgetHeightSpacing + 15)
    leftToolBarTopBoard.add(r3c1GeometryActionDeck,left=85, bottom=115 - 2 * popUpWidgetHeightSpacing + 10)
    leftToolBarTopBoard.add(r4c0GeometryActionDeck,left=70, bottom=115 - 3 * popUpWidgetHeightSpacing + 15)
    leftToolBarTopBoard.add(r4c1GeometryActionDeck,left=85, bottom=115 - 3 * popUpWidgetHeightSpacing + 10)
    # R1 C1
    settingsBoard.add(L_settingsTitle, center_x_percent=0.5, top=baseGridTop - widgetBufferVertical)
    settingsBoard.add(Black_Underline_Frame(), left=0, top=baseGridTop - widgetHeightSpacing)
    settingsBoard.add(R_printMode, center_x_percent=0.5, top=baseGridTop - widgetHeightSpacing - widgetBufferVertical)
    settingsBoard.add(Gray_Underline_Frame(), left=0, top=baseGridTop - 2 * widgetHeightSpacing - widgetBufferVertical)
    enable_5_axis_mode()  # Default mode provides starter 5-axis options

    viewportGrid.set_col_width(1, 420)
    rightToolBarHBox.add(rightToolBarStack)
    viewportGrid.add(0, 0, leftToolBarStack)
    viewportGrid.add(0, 1, rightToolBarHBox)
    baseGrid.add(1, 0, viewportGrid) # This needs to be added after everything has been added to the settingsBoard or else the radio button order will get messed up again
    
    # R2 C0

    # R2 C1
    settingsBoard.add(sliceButtonDeck, center_x_percent=0.5, bottom=2 * widgetBufferVertical)

""" WIDGET DEFINITIONS """
# CONTAINER WIDGETS:
# Entire Window
baseGrid = glooey.Grid(3, 2)
# R0 C0
topLeftGrid = glooey.Grid(1, 2)
topLeftStack1 = glooey.Stack()
# R0 C1
# R1 C0
viewportGrid = glooey.Grid(1, 2)
rightToolBarHBox = glooey.HBox()
rightToolBarHBox.alignment = 'bottom right'
rightToolBarStack = glooey.Stack()
rightToolBarBoard = glooey.Board()
rightToolBarTopBoard = glooey.Board()
leftToolBarStack = glooey.Stack()
leftToolBarBoard = glooey.Board()
leftToolBarTopBoard = glooey.Board()
# R1 C1
settingsStack = glooey.Stack()
settingsBoard = glooey.Board()
slicingDirectionBoard = glooey.Board()
# R2 C0

# R2 C1
lowerSettingsStack = glooey.Stack()

# WIDGETS
# Rotate Mode Radio Button Variables
rotateModeBackground = "image_resources/rotateMode_Radio_Button_Images/background.png"
rotateModeNames = ["X", "Y", "Z"]
rotateModeImages = [
    [
        "image_resources/rotateMode_Radio_Button_Images/x/R_uncheckedBase.png",
        "image_resources/rotateMode_Radio_Button_Images/x/R_uncheckedOver.png",
        "image_resources/rotateMode_Radio_Button_Images/x/R_uncheckedDown.png",
        "image_resources/rotateMode_Radio_Button_Images/x/R_checked.png",
    ],
    [
        "image_resources/rotateMode_Radio_Button_Images/y/R_uncheckedBase.png",
        "image_resources/rotateMode_Radio_Button_Images/y/R_uncheckedOver.png",
        "image_resources/rotateMode_Radio_Button_Images/y/R_uncheckedDown.png",
        "image_resources/rotateMode_Radio_Button_Images/y/R_checked.png",
    ],
    [
        "image_resources/rotateMode_Radio_Button_Images/z/R_uncheckedBase.png",
        "image_resources/rotateMode_Radio_Button_Images/z/R_uncheckedOver.png",
        "image_resources/rotateMode_Radio_Button_Images/z/R_uncheckedDown.png",
        "image_resources/rotateMode_Radio_Button_Images/z/R_checked.png",
    ],
]

rotateModeDefaultIndex = 0

geometryActionBackgroundDeck = glooey.Deck(
    "deactivated",
    deactivated=Widget_Label(""),
    base=Custom_Image("image_resources/geometryActionPopUpBox_Images/background.png"),
    scale=Custom_Image(
        "image_resources/geometryActionPopUpBox_Images/scaleBackground.png"
    ),
)
geometryActionBackgroundState = "deactivated"
geometryActionState = "blank"
settingsState = "material"

r0GeometryActionDeck = glooey.Deck(
    "blank",
    blank=Widget_Label(""),
    translate=Pop_Up_Box_Label("Translate", color="black"),
    rotate=Pop_Up_Box_Label("Rotate", color="black"),
    scale=Pop_Up_Box_Label("Scale", color="black"),
)
r2c0GeometryActionDeck = glooey.Deck(
    "blank",
    blank=Widget_Label(""),
    translate=Widget_Label("X", color="red"),
    rotate=Widget_Label("", color="red"),
    scale=Widget_Label("", color="red"),
)
r2c1GeometryActionDeck = glooey.Deck(
    "blank",
    blank=Widget_Label(""),
    translate=Entry_Box(
        str(translateX), buildPlateBounds[0], buildPlateBounds[1], "mm"
    ),
    rotate=Radio_Buttons(
        "Horizontal",
        False,
        False,
        rotateModeBackground,
        rotateModeNames,
        rotateModeImages,
        rotateModeDefaultIndex,
        None,
        update_mode_placeholder,
        [],
    ),
    scale=Entry_Box(str(scaleFactor), scaleBounds[0], scaleBounds[1], "%"),
)
r3c0GeometryActionDeck = glooey.Deck(
    "blank",
    blank=Widget_Label(""),
    translate=Widget_Label("Y", color="green"),
    rotate=Widget_Label("", color="green"),
    scale=Widget_Label("", color="green"),
)
r3c1GeometryActionDeck = glooey.Deck(
    "blank",
    blank=Widget_Label(""),
    translate=Entry_Box(
        str(translateY), buildPlateBounds[0], buildPlateBounds[1], "mm"
    ),
    rotate=Entry_Box(str(rotateY), rotateBounds[0], rotateBounds[1], "°CCW"),
    scale=Unlabeled_Image_Button(
        "image_resources/apply_Button_Images/base.png",
        "image_resources/apply_Button_Images/over.png",
        "image_resources/apply_Button_Images/down.png",
        apply_placeholder,
        [],
    ),
)
r4c0GeometryActionDeck = glooey.Deck(
    "blank",
    blank=Widget_Label(""),
    translate=Widget_Label("Z", color="blue"),
    rotate=Widget_Label("", color="blue"),
    scale=Widget_Label("", color="blue"),
)
r4c1GeometryActionDeck = glooey.Deck(
    "blank",
    blank=Widget_Label(""),
    translate=Entry_Box(str(translateZ), zBounds[0], zBounds[1], "mm"),
    rotate=Unlabeled_Image_Button(
        "image_resources/apply_Button_Images/base.png",
        "image_resources/apply_Button_Images/over.png",
        "image_resources/apply_Button_Images/down.png",
        apply_placeholder,
        [],
    ),
    scale=Widget_Label(""),
)

# Print Mode Radio Button Variables
printModeBackground = "image_resources/printMode_Radio_Button_Images/background.png"
printModeNames = ["5-Axis Mode", "3-Axis Mode"]
printModeImages = [
    [
        "image_resources/printMode_Radio_Button_Images/5AxisMode/R_uncheckedBase.png",
        "image_resources/printMode_Radio_Button_Images/5AxisMode/R_uncheckedOver.png",
        "image_resources/printMode_Radio_Button_Images/5AxisMode/R_uncheckedDown.png",
        "image_resources/printMode_Radio_Button_Images/5AxisMode/R_checked.png",
    ],
    [
        "image_resources/printMode_Radio_Button_Images/3AxisMode/R_uncheckedBase.png",
        "image_resources/printMode_Radio_Button_Images/3AxisMode/R_uncheckedOver.png",
        "image_resources/printMode_Radio_Button_Images/3AxisMode/R_uncheckedDown.png",
        "image_resources/printMode_Radio_Button_Images/3AxisMode/R_checked.png",
    ],
]

printModeDefaultIndex = 0
# Option Mode Radio Button Variables
optionModeBackground = "image_resources/optionMode_Radio_Button_Images/background.png"
optionModeNames = [
    "Material",
    "Strength",
    "Resolution",
    "Movement",
    "Supports",
    "Adhesion",
]
optionModeImages = [
    [
        "image_resources/optionMode_Radio_Button_Images/material/R_uncheckedBase.png",
        "image_resources/optionMode_Radio_Button_Images/material/R_uncheckedOver.png",
        "image_resources/optionMode_Radio_Button_Images/material/R_uncheckedDown.png",
        "image_resources/optionMode_Radio_Button_Images/material/R_checked.png",
    ],
    [
        "image_resources/optionMode_Radio_Button_Images/strength/R_uncheckedBase.png",
        "image_resources/optionMode_Radio_Button_Images/strength/R_uncheckedOver.png",
        "image_resources/optionMode_Radio_Button_Images/strength/R_uncheckedDown.png",
        "image_resources/optionMode_Radio_Button_Images/strength/R_checked.png",
    ],
    [
        "image_resources/optionMode_Radio_Button_Images/resolution/R_uncheckedBase.png",
        "image_resources/optionMode_Radio_Button_Images/resolution/R_uncheckedOver.png",
        "image_resources/optionMode_Radio_Button_Images/resolution/R_uncheckedDown.png",
        "image_resources/optionMode_Radio_Button_Images/resolution/R_checked.png",
    ],
    [
        "image_resources/optionMode_Radio_Button_Images/movement/R_uncheckedBase.png",
        "image_resources/optionMode_Radio_Button_Images/movement/R_uncheckedOver.png",
        "image_resources/optionMode_Radio_Button_Images/movement/R_uncheckedDown.png",
        "image_resources/optionMode_Radio_Button_Images/movement/R_checked.png",
    ],
    [
        "image_resources/optionMode_Radio_Button_Images/supports/R_uncheckedBase.png",
        "image_resources/optionMode_Radio_Button_Images/supports/R_uncheckedOver.png",
        "image_resources/optionMode_Radio_Button_Images/supports/R_uncheckedDown.png",
        "image_resources/optionMode_Radio_Button_Images/supports/R_checked.png",
    ],
    [
        "image_resources/optionMode_Radio_Button_Images/adhesion/R_uncheckedBase.png",
        "image_resources/optionMode_Radio_Button_Images/adhesion/R_uncheckedOver.png",
        "image_resources/optionMode_Radio_Button_Images/adhesion/R_uncheckedDown.png",
        "image_resources/optionMode_Radio_Button_Images/adhesion/R_checked.png",
    ],
]

optionModeDefaultIndex = 0

geometryActionBackground = (
    "image_resources/geometryAction_Radio_Button_Images/background.png"
)
geometryActionNames = ["Translate", "Rotate", "Scale"]
geometryActionImages = [
    [
        "image_resources/geometryAction_Radio_Button_Images/translate/R_uncheckedBase.png",
        "image_resources/geometryAction_Radio_Button_Images/translate/R_uncheckedOver.png",
        "image_resources/geometryAction_Radio_Button_Images/translate/R_uncheckedDown.png",
        "image_resources/geometryAction_Radio_Button_Images/translate/R_checked.png",
    ],
    [
        "image_resources/geometryAction_Radio_Button_Images/rotate/R_uncheckedBase.png",
        "image_resources/geometryAction_Radio_Button_Images/rotate/R_uncheckedOver.png",
        "image_resources/geometryAction_Radio_Button_Images/rotate/R_uncheckedDown.png",
        "image_resources/geometryAction_Radio_Button_Images/rotate/R_checked.png",
    ],
    [
        "image_resources/geometryAction_Radio_Button_Images/scale/R_uncheckedBase.png",
        "image_resources/geometryAction_Radio_Button_Images/scale/R_uncheckedOver.png",
        "image_resources/geometryAction_Radio_Button_Images/scale/R_uncheckedDown.png",
        "image_resources/geometryAction_Radio_Button_Images/scale/R_checked.png",
    ],
]
geometryActionDefaultIndex = None
# View Mode Radio Button Variables
viewModeBackground = "image_resources/viewMode_Radio_Button_Images/background.png"
viewModeNames = ["Prepare", "Preview"]
viewModeImages = [
    [
        "image_resources/viewMode_Radio_Button_Images/prepare/R_uncheckedBase.png",
        "image_resources/viewMode_Radio_Button_Images/prepare/R_uncheckedOver.png",
        "image_resources/viewMode_Radio_Button_Images/prepare/R_uncheckedDown.png",
        "image_resources/viewMode_Radio_Button_Images/prepare/R_checked.png",
    ],
    [
        "image_resources/viewMode_Radio_Button_Images/preview/R_uncheckedBase.png",
        "image_resources/viewMode_Radio_Button_Images/preview/R_uncheckedOver.png",
        "image_resources/viewMode_Radio_Button_Images/preview/R_uncheckedDown.png",
        "image_resources/viewMode_Radio_Button_Images/preview/R_checked.png",
    ],
]
viewModeDefaultIndex = 0
viewModeState = "prepare"

# Define widget decks for all rows and columns of all settings menu layout states
defaultState = "material"
r0c0SettingsDeck = glooey.Deck(
    defaultState,
    material=Widget_Label("Nozzle Temperature"),
    strength=Widget_Label("Infill %"),
    resolution=Widget_Label("Layer Height"),
    movement=Widget_Label("Print Speed"),
    supports=Widget_Label("Enable Supports (NOT YET IMPLEMENTED)"),
    adhesion=Widget_Label("Enable Brim"),
)
r0c1SettingsDeck = glooey.Deck(
    defaultState,
    material=Entry_Box(str(nozzleTemp), 100.0, 250.0, "°C"),
    strength=Entry_Box(str(infillPercentage), 0.0, 100.0, "%"),
    resolution=Entry_Box(str(layerHeight), 0.05, 2.0, "mm"),
    movement=Entry_Box(str(printSpeed), 5.0, 300.0, "mm/s"),
    supports=Checkbox(),
    adhesion=Checkbox(),
)
r1c0SettingsDeck = glooey.Deck(
    defaultState,
    material=Widget_Label("    Initial Nozzle Temperature"),
    strength=Widget_Label("Shell Thickness"),
    resolution=Light_Gray_Background(),
    movement=Widget_Label("    Initial Print Speed"),
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)
r1c1SettingsDeck = glooey.Deck(
    defaultState,
    material=Entry_Box(str(initialNozzleTemp), 100.0, 250.0, "°C"),
    strength=Entry_Box(str(shellThickness), 1, 10, "layers"),
    resolution=Light_Gray_Background(),
    movement=Entry_Box(str(initialPrintSpeed), 5.0, 300.0, "mm/s"),
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)
r2c0SettingsDeck = glooey.Deck(
    defaultState,
    material=Widget_Label("Print Bed Temperature"),
    strength=Light_Gray_Background(),
    resolution=Light_Gray_Background(),
    movement=Widget_Label("Travel Speed"),
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)
r2c1SettingsDeck = glooey.Deck(
    defaultState,
    material=Entry_Box(str(bedTemp), 10.0, 70.0, "°C"),
    strength=Light_Gray_Background(),
    resolution=Light_Gray_Background(),
    movement=Entry_Box(str(travelSpeed), 5.0, 300.0, "mm/s"),
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)
#
r3c0SettingsDeck = glooey.Deck(
    defaultState,
    material=Widget_Label("    Initial Print Bed Temperature"),
    strength=Light_Gray_Background(),
    resolution=Light_Gray_Background(),
    movement=Widget_Label("    Initial Travel Speed"),
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)
r3c1SettingsDeck = glooey.Deck(
    defaultState,
    material=Entry_Box(str(initialBedTemp), 10.0, 70.0, "°C"),
    strength=Light_Gray_Background(),
    resolution=Light_Gray_Background(),
    movement=Entry_Box(str(initialTravelSpeed), 5.0, 300.0, "mm/s"),
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)
#
r4c0SettingsDeck = glooey.Deck(
    defaultState,
    material=Light_Gray_Background(),
    strength=Light_Gray_Background(),
    resolution=Light_Gray_Background(),
    movement=Widget_Label("Enable Z-Hop When Travelling"),
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)
r4c1SettingsDeck = glooey.Deck(
    defaultState,
    material=Light_Gray_Background(),
    strength=Light_Gray_Background(),
    resolution=Light_Gray_Background(),
    movement=Checkbox(),
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)
#
r5c0SettingsDeck = glooey.Deck(
    defaultState,
    material=Light_Gray_Background(),
    strength=Light_Gray_Background(),
    resolution=Light_Gray_Background(),
    movement=Widget_Label("Enable Retraction"),
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)
r5c1SettingsDeck = glooey.Deck(
    defaultState,
    material=Light_Gray_Background(),
    strength=Light_Gray_Background(),
    resolution=Light_Gray_Background(),
    movement=Checkbox(),
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)

r6c0MovementDeck = glooey.Deck( # This deck is nested so that it only becomes visible if retraction is checked
    defaultState,
    enabled=Widget_Label("    Retraction Distance"),
    disabled=Light_Gray_Background(),
)

r6c0SettingsDeck = glooey.Deck(
    defaultState,
    material=Light_Gray_Background(),
    strength=Light_Gray_Background(),
    resolution=Light_Gray_Background(),
    movement=r6c0MovementDeck,
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)

r6c1MovementDeck = glooey.Deck( # This deck is nested so that it only becomes visible if retraction is checked
    defaultState,
    enabled=Entry_Box(str(retractionDistance), 0.1, 10.0, "mm"),
    disabled=Light_Gray_Background(),
)

r6c1SettingsDeck = glooey.Deck(
    defaultState,
    material=Light_Gray_Background(),
    strength=Light_Gray_Background(),
    resolution=Light_Gray_Background(),
    movement=r6c1MovementDeck,
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)

r7c0MovementDeck = glooey.Deck( # This deck is nested so that it only becomes visible if retraction is checked
    defaultState,
    enabled=Widget_Label("    Retraction Speed"),
    disabled=Light_Gray_Background(),
)

r7c0SettingsDeck = glooey.Deck(
    defaultState,
    material=Light_Gray_Background(),
    strength=Light_Gray_Background(),
    resolution=Light_Gray_Background(),
    movement=r7c0MovementDeck,
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)

r7c1MovementDeck = glooey.Deck( # This deck is nested so that it only becomes visible if retraction is checked
    defaultState,
    enabled=Entry_Box(str(retractionSpeed), 5.0, 60.0, "mm/s"),
    disabled=Light_Gray_Background(),
)

r7c1SettingsDeck = glooey.Deck(
    defaultState,
    material=Light_Gray_Background(),
    strength=Light_Gray_Background(),
    resolution=Light_Gray_Background(),
    movement=r7c1MovementDeck,
    supports=Light_Gray_Background(),
    adhesion=Light_Gray_Background(),
)

r1c0SettingsDeck.get_widget("material").set_style(italic=True)
r1c0SettingsDeck.get_widget("movement").set_style(italic=True)
r3c0SettingsDeck.get_widget("material").set_style(italic=True)
r3c0SettingsDeck.get_widget("movement").set_style(italic=True)
r6c0SettingsDeck.get_widget("movement").get_widget("enabled").set_style(italic=True)
r7c0SettingsDeck.get_widget("movement").get_widget("enabled").set_style(italic=True)
r4c1SettingsDeck.get_widget("movement").check() # INITIALIZE Z HOP AS CHECKED BY DEFAULT
r5c1SettingsDeck.get_widget("movement").check() # INITIALIZE RETRACTION AS CHECKED BY DEFAULT
r6c0MovementDeck.set_state("enabled")
r6c1MovementDeck.set_state("enabled")
r7c0MovementDeck.set_state("enabled")
r7c1MovementDeck.set_state("enabled")
# Slice button deck
sliceButtonDeck = glooey.Deck(
    "B_slice",
    B_slice=Disableable_Unlabeled_Image_Button(
        "image_resources/Slice_Button_Images/slice/base.png",
        "image_resources/Slice_Button_Images/slice/over.png",
        "image_resources/Slice_Button_Images/slice/down.png",
        set_sliceFlag,
        [],
        "image_resources/Slice_Button_Images/slice/disabled.png",
    ),
    B_saveGcodeAs=Unlabeled_Image_Button(
        "image_resources/Slice_Button_Images/saveGcodeAs/base.png",
        "image_resources/Slice_Button_Images/saveGcodeAs/over.png",
        "image_resources/Slice_Button_Images/saveGcodeAs/down.png",
        save_gcode_as,
        [],
    ),
)

sliceButtonDeck.get_widget("B_slice").set_disabled(True) # Start out with the slice button disabled. Only enable it when there is something to slice
# R0 C0
I_logo = Custom_Image("image_resources/logo/logo.png")  # New
R_viewMode = Radio_Buttons(
    "Horizontal",
    False,
    False,
    viewModeBackground,
    viewModeNames,
    viewModeImages,
    viewModeDefaultIndex,
    None,
    toggle_viewMode_layout,
    [],
)

R_viewMode.set_disabled(True) # Start out with this disabled so the user can't switch to the "Preview" mode since there's nothing there initially

# R0 C1

# R1 C0
B_selectFile = Unlabeled_Image_Button(
    "image_resources/File_Button_Images/base.png",
    "image_resources/File_Button_Images/over.png",
    "image_resources/File_Button_Images/down.png",
    select_file,
    [],
)
R_geometryAction = Radio_Buttons(
    "Vertical",
    False,
    True,
    geometryActionBackground,
    geometryActionNames,
    geometryActionImages,
    geometryActionDefaultIndex,
    None,
    toggle_left_toolbar_layout,
    [],
)
# R1 C1
L_settingsTitle = Title_Label("Print Settings")
R_printMode = Radio_Buttons(
    "Horizontal",
    False,
    False,
    printModeBackground,
    printModeNames,
    printModeImages,
    printModeDefaultIndex,
    None,
    toggle_printMode_layout,
    [],
)
# Slicing Directions Box:
I_startingBox = Custom_Image(
    "image_resources/slicingDirectionBox_Images/startingBox/background.png"
)
B_numSlicingDirections = Disableable_Unlabeled_Image_Button(
    "image_resources/slicingDirectionBox_Images/startingBox/apply/base.png",
    "image_resources/slicingDirectionBox_Images/startingBox/apply/over.png",
    "image_resources/slicingDirectionBox_Images/startingBox/apply/down.png",
    set_numSlicingDirections,
    [],
    "image_resources/slicingDirectionBox_Images/startingBox/apply/disabled.png"
)
B_numSlicingDirections.set_disabled(True)
B_numSlicingDirections.D_variables['applied'] = False

I_slicingDirectionBox = Custom_Image(
    "image_resources/slicingDirectionBox_Images/background.png"
)

S_numSlicingDirections = Spin_Box(
    40, "2", 2, maxSlicingDirections, 1, "int", update_placeholder, ""
)

S_currentSlicingDirection = Spin_Box(
    40, "2", 2, int(numSlicingDirections) + 1, 1, "int", update_current_selection, ""
)
B_addNew = Unlabeled_Image_Button(
    "image_resources/slicingDirectionBox_Images/addNew/base.png",
    "image_resources/slicingDirectionBox_Images/addNew/over.png",
    "image_resources/slicingDirectionBox_Images/addNew/down.png",
    add_new_slicing_direction,
    [],
)
B_remove = Unlabeled_Image_Button(
    "image_resources/slicingDirectionBox_Images/remove/base.png",
    "image_resources/slicingDirectionBox_Images/remove/over.png",
    "image_resources/slicingDirectionBox_Images/remove/down.png",
    remove_slicing_direction,
    [],
)
B_removeAll = Unlabeled_Image_Button(
    "image_resources/slicingDirectionBox_Images/removeAll/base.png",
    "image_resources/slicingDirectionBox_Images/removeAll/over.png",
    "image_resources/slicingDirectionBox_Images/removeAll/down.png",
    remove_all_slicing_directions,
    [],
)

S_startingX = Spin_Box(
    80,
    "0.0",
    buildPlateBounds[0],
    buildPlateBounds[1],
    5.0,
    "float",
    update_starting_positions,
    "mm",
)
S_startingY = Spin_Box(
    80,
    "0.0",
    buildPlateBounds[0],
    buildPlateBounds[1],
    5.0,
    "float",
    update_starting_positions,
    "mm",
)
S_startingZ = Spin_Box(
    80,
    "0.0",
    0.0,
    250.0,
    5.0,
    "float",
    update_starting_positions,
    "mm",
)
S_theta = Spin_Box(80, "0.0", 0.0, 90.0, 15.0, "float", update_directions, "°")
S_phi = Spin_Box(
    80,
    "0.0",
    rotateBounds[0],
    rotateBounds[1],
    15.0,
    "float",
    update_directions,
    "°CCW",
)
lowerLine = Gray_Underline_Frame()
startingBoxWidgets = [I_startingBox, S_numSlicingDirections, B_numSlicingDirections]
slicingDirectionsBoxWidgets = [
    I_slicingDirectionBox,
    S_currentSlicingDirection,
    B_addNew,
    B_remove,
    B_removeAll,
    S_startingX,
    S_startingY,
    S_startingZ,
    S_theta,
    S_phi,
]
#
R_optionMode = Radio_Buttons(
    "Horizontal",
    False,
    False,
    optionModeBackground,
    optionModeNames,
    optionModeImages,
    optionModeDefaultIndex,
    None,
    toggle_settings_layout,
    [],
)

R_optionMode.D_variables['numSlicingDirections'] = 1
R_optionMode.D_variables['startingPositions'] = [[0.0, 0.0, 0.0]]
R_optionMode.D_variables['directions'] = [[0.0, 0.0]]
R_optionMode.D_variables['D_slicePlaneValidity'] = {'0': True}
# R2 C0
geometryActionPopUpBox = Custom_Image(
    "image_resources/geometryActionPopUpBox_Images/background.png"
)
# R2 C1
