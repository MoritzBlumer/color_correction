#!/usr/bin/env python
#
# Moritz Blumer | 2025-04-24
#
# Batch-color-correct images with a colorard, based on one images that is
# set as a reference. 


## FILE INFO
__author__ = 'Moritz Blumer, 2025'
__email__ = 'lmb215@cam.ac.uk'



## PLANTCV CONFIG

# adjust variable for card detection (see README)
ADAPTIVE_METHOD = 0
BLOCK_SIZE = 101
RADIUS = 50
MIN_SIZE = 20000



## SETUP

#  import packages
import argparse
import os
import rawpy
import cv2
from plantcv import plantcv as pcv
from PIL import Image



## CLI

def cli():

    '''
    Parse command line arguments.
    '''

    global input_dir_path, output_dir_path, review_dir_path, ref_image_path, \
        raw_suffix, icc_profile_path

    parser = argparse.ArgumentParser(description="Batch-color correct RAW \
        image files.")

    # add arguments
    parser.add_argument('input_dir_path', type=str, help='Path to the input\
        directory containing input RAW files')
    parser.add_argument('output_dir_path', type=str, help='Path to the output \
        directory which will contain color-corrected TIFF files')
    parser.add_argument('review_dir_path', type=str, help='Path to the PlantCV \
        debug directory which will contain PNGs with the masked color card for \
        review')
    parser.add_argument('ref_image_path', type=str, help='Path to the a single \
        RAW image with color card that will serve as the reference for all \
        input RAW files')
    parser.add_argument('raw_suffix', type=str, help='RAW suffix, this could \
        be be e.g. "ARW" (Sony), "NEF" (Nikon), "CR3" or any other format \
        accepted by rawpy')
    parser.add_argument('icc_profile_path', type=str, help='Path to the ICC \
        color profile to be embedded in the output TIFFs, for example the sRGB \
        profile supplied at data/sRGB_profile.icc can be specified.')

    # parse
    args = parser.parse_args()

    # reassign variable names
    input_dir_path, output_dir_path, review_dir_path, ref_image_path, \
        raw_suffix, icc_profile_path = args.input_dir_path, \
        args.output_dir_path, args.ref_image_path, args.raw_suffix, \
        args.icc_profile_path



## FUNCTIONS

def detect_color_card(image_path, ADAPTIVE_METHOD, BLOCK_SIZE, RADIUS, \
                      MIN_SIZE):

    '''
    Read in 8 bit image using auto brightness, autoscaling, no 4-channel-RGB,
    no gamma supression. Return color card mask.
    '''

    # enable debug/print
    pcv.params.debug = 'print'
    
    # read RAW
    raw = rawpy.imread(image_path)

    # convert to RGB
    rgb = raw.postprocess(
        output_bps=8,
        no_auto_bright=False,
        use_camera_wb=False,
        use_auto_wb=True,
        no_auto_scale=False,
        four_color_rgb=False,
        output_color=rawpy.ColorSpace.sRGB,
    )

    # rearrange channels because plantcv expects BGR
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    # detect color card
    card_mask = pcv.transform.detect_color_card(
        rgb_img=bgr,
        label=image_path.split('/')[-1].split('_')[0],
        adaptive_method=ADAPTIVE_METHOD,
        block_size=BLOCK_SIZE,
        radius=RADIUS,
        min_size=MIN_SIZE,
        )

    return card_mask


def get_ref_color_matrix(ref_image_path):

    '''
    Extract reference color matrix from a RAW image: First detect color card 
    with detect_color_card(), then read it in again as in
    apply_color_correction() and extract color mask.
    '''

    # enable debug/print
    pcv.params.debug = 'print'

    # get color profile from reference image 
    ref_card_mask = detect_color_card(
        ref_image_path,
    )

    # disable debug/print
    pcv.params.debug = None

    # read RAW
    raw = rawpy.imread(ref_image_path)

    # convert to RGB
    rgb = raw.postprocess(
        output_bps=8,
        no_auto_bright=True,
        use_camera_wb=False,
        use_auto_wb=False,
        no_auto_scale=False,
        four_color_rgb=True,
        output_color=rawpy.ColorSpace.sRGB,
    )

    # rearrange channels because plantcv expects BGR
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    # derive color card matrix
    _, ref_color_matrix = pcv.transform.get_color_matrix(
        rgb_img=bgr,
        mask=ref_card_mask
    )

    return ref_color_matrix


def apply_color_correction(image_path, card_mask, ref_color_matrix):

    '''
    Read in 8 bit image with no auto brightness, no WB adjustment, 
    4-channel-RGB, no gamma correction. Using  card_mask, derive card_matrix 
    and adjust colors using ref_color_matrix. Return color-corrected RGB image.
    '''

    # disable debug/print
    pcv.params.debug = None

    # read RAW
    raw = rawpy.imread(image_path)

    # convert to RGB
    rgb = raw.postprocess(
        output_bps=8,
        no_auto_bright=True,
        use_camera_wb=False,
        use_auto_wb=False,
        no_auto_scale=False,
        four_color_rgb=True,
        output_color=rawpy.ColorSpace.sRGB,
    )

    # rearrange channels because plantcv expects BGR
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    # derive color card matrix
    _, color_matrix = pcv.transform.get_color_matrix(
        rgb_img=bgr,
        mask=card_mask
    )

    # Color correct your image to the standard values
    bgr_corr = pcv.transform.affine_color_correction(
        rgb_img=bgr,
        source_matrix=color_matrix,
        target_matrix=ref_color_matrix
    )

    # convert back to RGB
    rgb_corr = cv2.cvtColor(bgr_corr, cv2.COLOR_BGR2RGB)

    return rgb_corr



## MAIN

def main():
    
    # set up PlantCV (i.e. set debugging directory )
    pcv.params.debug_outdir = review_dir_path

    # fetch target images & sort
    target_image_lst = [
        x for x in os.listdir(input_dir_path) if x.endswith(raw_suffix)
    ]
    target_image_lst.sort()

    # read ICC color profile
    with open(icc_profile_path, "rb") as f:
        icc_profile = f.read()

    # extract reference/target color mask
    ref_color_matrix = get_ref_color_matrix(ref_image_path)

    # process images
    for i, image in enumerate(target_image_lst):

        # detect color card
        card_mask = detect_color_card(
            f'{input_dir_path}/{image}',
        )

        # apply correction
        rgb_corr = apply_color_correction(
            f'{input_dir_path}/{image}', 
            card_mask, 
            ref_color_matrix,
        )
        
        # save
        pil_img = Image.fromarray(rgb_corr)
        pil_img.save(
            f"{output_dir_path}/{image.replace(raw_suffix, 'tiff')}",
            format="TIFF",
            icc_profile=icc_profile,
            compression='tiff_adobe_deflate',
        )


if __name__ == '__main__':
    main()