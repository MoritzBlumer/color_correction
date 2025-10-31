#!/usr/bin/env python
#
# Moritz Blumer | 2025-10-31
#
# Extract and save color matrix from RAW to be used as reference to
# color-correct other images


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



## CLI

def cli():

    '''
    Parse command line arguments.
    '''

    global target_image_path, proxy_image_path, ref_image_path, \
        ref_image_path, output_path, review_dir_path, icc_profile_path

    parser = argparse.ArgumentParser(description="Infer color corrections from \
        proxy image,  apply them to target image.")

    # add arguments
    parser.add_argument('ref_image_path', type=str, help='Path to the RAW \
        image serving as the reference for for color correction')
    parser.add_argument('output_path', type=str, help='Path to the \
        color-corrected output TIFF')
    parser.add_argument('review_dir_path', type=str, help='Path to the PlantCV \
        debug directory which will contain PNGs with the masked color card for \
        review')

    # parse
    args = parser.parse_args()

    # reassign variable names
    ref_image_path, output_path, review_dir_path = \
        args.ref_image_path, args.output_path, args.review_dir_path



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
        four_color_rgb=False,
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



## MAIN

def main():

    # parse arguments
    cli()

    # make directories if they don't exist
    check_make_dir(review_dir_path)

    # set up PlantCV (i.e. set debugging directory )
    pcv.params.debug_outdir = review_dir_path

    # extract reference/target color mask
    ref_color_matrix = get_ref_color_matrix(ref_image_path)

    # save
    with open(output_path, 'w') as output_file:
        for row in ref_color_matrix:
            line = '\t'.join(f'{x:.8e}' for x in row)
            output_file.write(f'{line}\n')


if __name__ == '__main__':
    main()
