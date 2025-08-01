# Installation instructions:
Tested on Ubuntu 24.04, but should work on other Linux too and on Windows if you already have a recent Python3 install (v3.10+)

0. create clean directory
```
mkdir fractalCortex
cd fractalCortex
```

1. Download Git source and unzip here or use 
```
git clone https://github.com/fractalrobotics/Fractal-Cortex.git 
```
Note: if you are in Linux or MacOs, you will need a patched version from my fork instead, if it has not been merged yet in the official release: 
```
git clone https://github.com/jcugnoni/Fractal-Cortex.git
```

2. create Python3 venv
```
cd Fractal-Cortex
cd fractal-cortex
python3 -m venv fractalCortexVenv
```

3. using Python3 from Venv : install dependencies (fix documentation: many more modules are also required, see 2nd line below!)
```
fractalCortexVenv/bin/python3 -m pip install numpy==1.26.4 numpy-stl==3.1.1 pyglet==1.5.28 pyOpenGL==3.1.0 shapely==2.0.4 trimesh==4.3.1 glooey==0.3.6 

fractalCortexVenv/bin/python3 -m pip install scipy rtree mapbox_earcut manifold3d
```
   
4. execute slicer:
```
fractalCortexVenv/bin/python3 slicer_main.py
```
--- patching for case sensitive OS (Linux ; MacOs):

if using the official version of Fractal Cortex code released before this fork changes are commited, you will need to patch the following files:
```
fractal_widgets.py:916 > modify line to fix case of image file name
     pyglet.resource.path = [".", "image_resources/CheckBox_Images"]

widget_functions.py:1171+ > correct case of image file names
   scale=Unlabeled_Image_Button(
        "image_resources/apply_Button_Images/base.png",
        "image_resources/apply_Button_Images/over.png",
        "image_resources/apply_Button_Images/down.png",
        apply_placeholder,
        [],
    ),

widget_functions.py:1171+ > correct case of image file names
	rotate=Unlabeled_Image_Button(
        "image_resources/apply_Button_Images/base.png",
        "image_resources/apply_Button_Images/over.png",
        "image_resources/apply_Button_Images/down.png",
        apply_placeholder,
        [],
    ),
    scale=Widget_Label(""),

```
-- testing: 

the example pipe_fitting.stl was successfully sliced with this install procedure on Ubunt 24.04.
