# RadiAID

Latest stable version of an interface that's used to set up mice for high-precision proton irradiation based on a previously performed CT scan and a delineated target structure. Relies on proton radiographic images for on-site image-guidance.

### Setup
You'll need a bit of stuff to set up RadiAID and get it running. Most noteably, that should be Python 3, it's recommended to use the Anaconda distribution for a quick and easy setup. If you don't have it, get it [here](https://www.anaconda.com/products/individual).

#### Additional packages:
RadiAID requires a few python packages that don't come with the anaconda distribution. To download and install new packages, install anaconda and launch the anaconda command line. You can do this in two ways. You can either open the console through the windows start menu 
![](./imgs/launch_prompt1.png)
or through the Anaconda interface. For the second option, start anaconda and navigate to the ''Environments'' tab. Click the green triangle next to ''root'' and then click ''open terminal'' 
![](./imgs/launch_prompt2.png)

Onco you started the anaconda command prompt, you will have to install/update the following packages:
* PySerial: type the following to install: `conda install -c anaconda pyserial`
* PyDicom: type the following to install: `conda install -c conda-forge pydicom`

### 1. How to run:

* Go to folder with Positioning_AssistantMAIN.py (presumably the one you are at right now)
* click into addressline
* type "cmd" and hit Enter
* in console, type "python Positioning_AssistantMAIN.py", the programm will then start

### 2. Necessary Input
* .dcm Lynx image of Collimator for IsoCenter definition
* .dcm Lynx image of Bed with Earpins in Transport Box
* RS [...].dcm RT struct file that holds CT-based plan information ("structure set")
* .dcm Planar X-Ray image (angle: 90degree) from Planning day
* .dcm Planar X-Ray image (angle: 90degree) from Treatment day
* A good spirit! :)

### 3. Bug handling
* if unexpected behaviour occurrs: please report!
* Coordinate addition was currently only tested without repositioning Scan!
* Make sure that you load correct planar images; programm becomes buggy when files are loaded on top of old one
    Better: Close and start again

### 4. Logfile
A Logfile can be exported that saves all sorts of stuff. 
The default location for the creation of the logfile is in the directory of the program itself.

### 5. Citations
If you use this software, please cite the following publications:

Müller, J. et al. Proton radiography for inline treatment planning and positioning verification of small animals. Acta Oncol. (Madr). 56, 1399–1405 (2017).

Suckert, T. et al. High-precision image-guided proton irradiation of mouse brain sub-volumes. Radiother. Oncol. 146, 205–212 (2020).
