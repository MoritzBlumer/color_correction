#!/usr/bin/env python
#
# Moritz Blumer | 2025-04-24
#
# Correct a single image but infer corrections from another (proxy) image from 
# the same series (this is useful if the color card in the target image is 
# covered and can't be used for auto-correction)


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

    global target_image_path, proxy_image_path, ref_image_path, \
        ref_image_path, output_path, review_dir_path, icc_profile_path

    parser = argparse.ArgumentParser(description="Batch-color correct RAW \
        image files.")

    # add arguments
    parser.add_argument('target_image_path', type=str, help='Path to the RAW \
        image to apply corrections to')
    parser.add_argument('proxy_image_path', type=str, help='Path to the (proxy) \
        RAW image used to infer corrections from')
    parser.add_argument('ref_image_path', type=str, help='Path to the RAW \
        image serving as the reference for for color correction')
    parser.add_argument('output_path', type=str, help='Path to the \
        color-corrected output TIFF')
    parser.add_argument('review_dir_path', type=str, help='Path to the PlantCV \
        debug directory which will contain PNGs with the masked color card for \
        review')
    parser.add_argument('icc_profile_path', type=str, help='Path to the ICC color \
        profile to be embedded in the output TIFFs, for example the supplied sRGB \
        profile: data/sRGB_profile.icc')
    
    # parse
    args = parser.parse_args()

    # reassign variable names
    target_image_path, proxy_image_path, ref_image_path, output_path, \
        review_dir_path, icc_profile_path = \
        args.target_image_path, args.proxy_image_path, args.ref_image_path, \
        args.output_path, args.review_dir_path, args.icc_profile_path



## FUNCTIONS

def check_make_dir(dir_path):

    '''
    Check if a directory exists, if not, create it.
    '''

    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)


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
        ADAPTIVE_METHOD, 
        BLOCK_SIZE, 
        RADIUS,
        MIN_SIZE
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


def proxy_correct(proxy_image_path, target_image_path, ref_color_matrix):

    '''
    Fetch color matrix from proxy image, apply corrections to taget image.
    '''

    # detect color card
    card_mask = detect_color_card(
        proxy_image_path,
            ADAPTIVE_METHOD, 
            BLOCK_SIZE, 
            RADIUS,
            MIN_SIZE,
    )

    # disable debug/print
    pcv.params.debug = None

    # read RAW (good image)
    raw = rawpy.imread(proxy_image_path)

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

    # read RAW (bad image)
    raw = rawpy.imread(target_image_path)

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

    # parse arguments
    cli()
    
    # make directories if they don't exist
    check_make_dir(review_dir_path)

    # set up PlantCV (i.e. set debugging directory )
    pcv.params.debug_outdir = review_dir_path

    # read ICC color profile
    with open(icc_profile_path, "rb") as f:
        icc_profile = f.read()

    # extract reference/target color mask
    ref_color_matrix = get_ref_color_matrix(ref_image_path)

    # apply proxy corrections
    rgb_corr = proxy_correct(
        proxy_image_path, 
        target_image_path, 
        ref_color_matrix,
    )

    # save
    pil_img = Image.fromarray(rgb_corr)
    pil_img.save(
        output_path,
        format="TIFF",
        icc_profile=icc_profile,
        compression='tiff_adobe_deflate',
    )


if __name__ == '__main__':
    main()
