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
RAW_SUFFIX_LST = ['RAW', 'raw', 'ARW', 'arw', 'NEF', 'nef']
TIF_PNG_SUFFIX_LST = ['TIFF', 'tiff', 'TIF', 'tif', 'PNG', 'png']


## SETUP

#  import packages
import argparse
import sys
import os



## CLI

def cli():

    '''
    Parse command line arguments.
    '''

    global ref_img_path, output_path, review_dir_path, img_format

    parser = argparse.ArgumentParser(description="Extract and save color \
        matrix from RAW (or PNG/TIFF) to be used as reference to \
        color-correct other images.")

    # add arguments
    parser.add_argument('ref_img_path', type=str, help='Path to the RAW \
        (or PNG/TIFF) image to extract reference color matrix from')
    parser.add_argument('output_path', type=str, help='Path to the \
        output TSV')
    parser.add_argument('review_dir_path', type=str, help='Path to the PlantCV \
        debug directory which will contain PNGs with the masked color card for \
        review')
    parser.add_argument('img_format', type=str, help='Image format, this \
        could be "ARW" (Sony), "NEF" (Nikon), "CR3" (Canon) or others \
        (check rawpy) – PNG and TIFF formats are also supported')

    # parse
    args = parser.parse_args()

    # reassign variable names
    ref_img_path, output_path, review_dir_path, img_format = \
        args.ref_img_path, args.output_path, args.review_dir_path, \
        args.img_format



## FUNCTIONS

def check_make_dir(dir_path):

    '''
    Check if a directory exists, if not, create it.
    '''

    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)


def detect_color_card(image_path, img_format, ADAPTIVE_METHOD, BLOCK_SIZE, \
        RADIUS, MIN_SIZE, RAW_SUFFIX_LST, TIF_PNG_SUFFIX_LST):
    '''
    Read in 8 bit image using auto brightness, autoscaling, no 4-channel-RGB,
    no gamma supression. Return color card mask.
    '''

    # enable debug/print
    pcv.params.debug = 'print'

    # read RAW
    if img_format in RAW_SUFFIX_LST:

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

    # read TIFF/PNG
    elif img_format in TIF_PNG_SUFFIX_LST:

        bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)

    # else print error message and exit
    else:
        print(
            '[ERROR] images must be either in a RAW, TIFF or PNG format',
             file=sys.stderr,
        )
        sys.exit()

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


def get_ref_color_matrix(ref_img_path, img_format, ADAPTIVE_METHOD, \
        BLOCK_SIZE, RADIUS, MIN_SIZE, RAW_SUFFIX_LST, TIF_PNG_SUFFIX_LST):

    '''
    Extract reference color matrix from a RAW/PNG/TIFF image: First detect
    color card with detect_color_card(), then read it in again as in
    apply_color_correction() and extract color mask.
    '''

    # enable debug/print
    pcv.params.debug = 'print'

    # get color profile from reference image
    ref_card_mask = detect_color_card(
        ref_img_path,
        img_format,
        ADAPTIVE_METHOD,
        BLOCK_SIZE,
        RADIUS,
        MIN_SIZE,
        RAW_SUFFIX_LST,
        TIF_PNG_SUFFIX_LST,
    )

    # disable debug/print
    pcv.params.debug = None

    # read RAW
    if img_format in RAW_SUFFIX_LST:

        # read RAW
        raw = rawpy.imread(ref_img_path)

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

    # read TIFF/PNG
    else:

        bgr = cv2.imread(ref_img_path, cv2.IMREAD_COLOR)

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

    # import remaining packages
    import rawpy
    import cv2
    from plantcv import plantcv as pcv

    # make directories if they don't exist
    check_make_dir(review_dir_path)

    # set up PlantCV (i.e. set debugging directory )
    pcv.params.debug_outdir = review_dir_path

    # extract reference/target color mask
    ref_color_matrix = get_ref_color_matrix(
        ref_img_path,
        img_format,
        ADAPTIVE_METHOD,
        BLOCK_SIZE,
        RADIUS,
        MIN_SIZE,
        RAW_SUFFIX_LST,
        TIF_PNG_SUFFIX_LST,
    )

    # save
    with open(output_path, 'w') as output_file:
        for row in ref_color_matrix:
            line = '\t'.join(f'{x:.8e}' for x in row)
            output_file.write(f'{line}\n')


if __name__ == '__main__':
    main()
