# _Automated color and exposure correction based on color card_

Batch-correct color and exposure among a set of RAW (e.g. .ARW, .NEF, .CR3) images that all contain the same color card. One image is set as the reference and used to extract a reference color matrix, then all images are read in one by one and corrections are applied to match the reference image color matrix. **All images must contain a 24 patch color card like the Calibrite ColorChecker Classic Mini, but cheaper models work as well as long as the same card is consistently used**.

<br />
<br />

## Dependencies
[PlantCV](https://github.com/danforthcenter/plantcv) is used to detect the color card, to extract color matrices and to apply corrections. [Rawpy](https://github.com/letmaik/rawpy) is used to read in RAW files and [Pillow](https://github.com/python-pillow/Pillow) to write output TIFFs. [OpenCV](https://github.com/opencv/opencv) is used to rearrange color channels in the scripts and PlantCV heavily relies on OpenCV.

All dependencies can be installed with conda/mamba

```
mamba install -c conda-forge plantcv opencv rawpy pillow 
```
