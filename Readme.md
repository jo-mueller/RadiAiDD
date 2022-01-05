# RadiAIDD
[![test](https://github.com/jo-mueller/RadiAiDD/actions/workflows/test.yml/badge.svg)](https://github.com/jo-mueller/RadiAiDD/actions/workflows/test.yml)

Latest version of an interface that's used to set up mice for high-precision proton irradiation based on registration of three necessary image sources:
- Detector image (*radiography*) of collimated beam shape
- 2D Planning projection image which shows target structure
- Beam-site radiography of target structure (e.g. small animal) of region of interest.

## Setup

If you do not yet have the Anaconda Python package manager, get it [here](https://www.anaconda.com/products/individual). After installing, open an anaconda command prompt:
![screenshot_1](https://user-images.githubusercontent.com/38459088/143623993-f3cb9842-c067-47f4-acfa-5fbbf9d25dcb.png)

In the command prompt, create a new environment for RadiAIDD:
```
conda create -n RadiAIDD
conda activate  RadiAIDD
```

Install `git` and `pip` in this environment:
```conda install pip git```

Now, create a new directory for RadiAIDD. Move into this directory and download + install this repository using
```
git clone https://github.com/jo-mueller/RadiAiDD.git
pip install -e .
```

Lastly, you can run RadiAIDD by simply typing `RadiAIDD`  in the command line.

### Necessary Input
As written above, you'll need these data input sources:
* .tif Lynx image of Collimator for IsoCenter definition
* .tif Planing image of animal. Stack images are supported for 2 layers.
* .tif Treatment radiography image of animal

## Workflow
The workflow is as follows.

1. Define the beam isocenter. Navigate to the *Radiography* tab (top left) and click ![Define](https://github.com/jo-mueller/RadiAiDD/raw/master/RadiAIDD/imgs/Define_button.PNG). In the opening IsoCenter definition window, load the image of the collimated beam spot and draw rectangle around it. It should look somehow like this:
![IsoCenter](https://github.com/jo-mueller/RadiAiDD/raw/master/RadiAIDD/imgs/IsoCenter.PNG)
Note: You **have** to click the Lock-button to confirm the detection of the isocenter.

2. Load Plan and treatment image: For this, head to the *active positioning* tab and load the respective images. You can change the grayscales by moving the mouse over the image, *middle-mouse click* and drag the mouse. When you are happy with the display, proceed to registration.
3. Registration: Click *Set default landmarks* for both images and drag the appearing dots (you can change their sizes with the sliders below) to corresponding locations in both images. Click *run Registration* to display the resulting image transformation. The image overlay will show the same grayscale as the input images. The result should look somewhat like this:
![AcceptedRegistration](https://github.com/jo-mueller/RadiAiDD/raw/master/RadiAIDD/imgs/Accepted_registration.PNG?raw=true)
Use the slider below the overlay images to flip back and forth between planing and treatment image.

4. Target definition: In the *target coordinates* field, click the *Get* button to place the target marker in a random location in the plan image. If available, you can use the *Show atlas* button to display any provided overlays of the image. It may happen that, after loading the plan image, you will see only the atlas, and not the actual image. If this is the case, use the *Flip Image* button to exchange image and overlay. Drag&drop the target marker to your desired location in the planing image and click *run Registration* again to project the target coordinates into the treatment image. When you're good to go, click *Accept Registration*. 

5. Motor control: to be written

This gif shows the entire workflow: ![Workflow](https://github.com/jo-mueller/RadiAiDD/raw/master/RadiAIDD/imgs/Workflow.gif)

## Bug handling & known issues
* if unexpected behaviour occurrs: please report!
* If Planing image is loaded and not correctly display, try the *flip* button!
* Motor stability: RadiAIDD has crashed a couple of times randomly when adressing the motor stages through RadiAIDD - will be investigated and fixed in future releases.

## Citations
If you use this software, please cite the following publications:

Müller, J. et al. Proton radiography for inline treatment planning and positioning verification of small animals. Acta Oncol. (Madr). 56, 1399–1405 (2017).

Suckert, T. et al. High-precision image-guided proton irradiation of mouse brain sub-volumes. Radiother. Oncol. 146, 205–212 (2020).
