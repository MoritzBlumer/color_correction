#!/usr/bin/env python
#
# Moritz Blumer | 2025-04-24
#
# Batch-color-correct images with a colorard, based on one images that is
# set as a reference.


## FILE INFO
__author__ = 'Moritz Blumer, 2025'
__email__ = 'lmb215@cam.ac.uk'



## CONFIG

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

    global input_dir_path, output_dir_path, review_dir_path, ref_path, \
        img_format, icc_profile_path

    parser = argparse.ArgumentParser(description="Batch-color correct RAW \
        image files.")

    # add arguments
    parser.add_argument('input_dir_path', type=str, help='Path to the input\
        directory containing RAW (or PNG/TIFF) files')
    parser.add_argument('output_dir_path', type=str, help='Path to the output \
        directory to which color-corrected TIFF files will be saved')
    parser.add_argument('review_dir_path', type=str, help='Path to the PlantCV \
        debug directory which will contain PNGs with the masked color card for \
        review')
    parser.add_argument('ref_path', type=str, help='Path to the RAW \
        (or PNG/TIFF) image serving as the reference for for color correction \
        (or previously extracted reference color matrix in TSV format)')
    parser.add_argument('img_format', type=str, help='Image format, this \
        could be "ARW" (Sony), "NEF" (Nikon), "CR3" (Canon) or others \
        (check rawpy) – PNG and TIFF formats are also supported')
    parser.add_argument('icc_profile_path', type=str, help='Path to the ICC \
        color profile to be embedded in the output TIFFs, for example the \
        supplied sRGB profile: data/sRGB_profile.icc')

    # parse
    args = parser.parse_args()

    # reassign variable names
    input_dir_path, output_dir_path, review_dir_path, ref_path, \
        img_format, icc_profile_path = args.input_dir_path, \
        args.output_dir_path, args.review_dir_path, args.ref_path, \
        args.img_format, args.icc_profile_path



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


def get_ref_color_matrix(ref_path, img_format, ADAPTIVE_METHOD, BLOCK_SIZE, \
        RADIUS, MIN_SIZE, RAW_SUFFIX_LST, TIF_PNG_SUFFIX_LST):

    '''
    Extract reference color matrix from a RAW/PNG/TIFF image: First detect
    color card with detect_color_card(), then read it in again as in
    apply_color_correction() and extract color mask.
    '''

    # enable debug/print
    pcv.params.debug = 'print'

    # get color profile from reference image
    ref_card_mask = detect_color_card(
        ref_path,
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
        raw = rawpy.imread(ref_path)

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

        bgr = cv2.imread(ref_path, cv2.IMREAD_COLOR)

    # derive color card matrix
    _, ref_color_matrix = pcv.transform.get_color_matrix(
        rgb_img=bgr,
        mask=ref_card_mask
    )

    return ref_color_matrix


def read_ref_color_matrix(ref_path):

    '''
    Read in previously extracted reference color matrix
    '''

    ref_color_matrix = np.loadtxt(
        ref_path,
        delimiter='\t'
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
    if img_format in RAW_SUFFIX_LST:

        # read RAW
        raw = rawpy.imread(image_path)

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

        bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)

    # derive color card matrix
    _, color_matrix = pcv.transform.get_color_matrix(
        rgb_img=bgr,
        mask=card_mask
    )

    # derive upside-down color card matrix
    card_mask_ud = np.flipud(card_mask)
    _, color_matrix_ud = pcv.transform.get_color_matrix(
        rgb_img=bgr,
        mask=card_mask_ud
    )

    # compute “distance” to reference matrix (sum of squared differences)
    diff_normal = np.linalg.norm(color_matrix - ref_color_matrix)
    diff_flipped = np.linalg.norm(color_matrix_ud - ref_color_matrix)

    # select correct orientation
    if diff_normal >= diff_flipped:
        print(
            f'[INFO] {image_path}: Color card upside down',
            file=sys.stderr,
        )
        color_matrix = color_matrix_ud

    # correct colors
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

    # import remaining packages
    import rawpy
    import cv2
    from plantcv import plantcv as pcv
    from PIL import Image
    import numpy as np

    # make directories if they don't exist
    check_make_dir(review_dir_path)
    check_make_dir(output_dir_path)

    # set up PlantCV (i.e. set debugging directory )
    pcv.params.debug_outdir = review_dir_path

    # fetch target images & sort
    target_image_lst = [
        x for x in os.listdir(input_dir_path)
        if x.lower().endswith(img_format.lower())
    ]
    target_image_lst.sort()

    # read ICC color profile
    with open(icc_profile_path, "rb") as f:
        icc_profile = f.read()

    # extract reference/target color mask
    if img_format in RAW_SUFFIX_LST + TIF_PNG_SUFFIX_LST \
        and ref_path.lower().endswith(img_format.lower()):
        ref_color_matrix = get_ref_color_matrix(
            ref_path,
            img_format,
            ADAPTIVE_METHOD,
            BLOCK_SIZE,
            RADIUS,
            MIN_SIZE,
            RAW_SUFFIX_LST,
            TIF_PNG_SUFFIX_LST,
        )
    elif ref_path.endswith('.tsv'):
        ref_color_matrix = read_ref_color_matrix(
            ref_path,
        )
    else:
        print(
            f'[ERROR] <ref_path> must be either in {img_format} or .tsv'
             ' format',
             file=sys.stderr,
        )
        sys.exit()

    # process images
    for image in target_image_lst:

        # detect color card
        card_mask = detect_color_card(
            f'{input_dir_path}/{image}',
            img_format,
            ADAPTIVE_METHOD,
            BLOCK_SIZE,
            RADIUS,
            MIN_SIZE,
            RAW_SUFFIX_LST,
            TIF_PNG_SUFFIX_LST,
        )

        # apply correction
        rgb_corr = apply_color_correction(
            f'{input_dir_path}/{image}',
            card_mask,
            ref_color_matrix,
        )

        # save
        pil_img = Image.fromarray(rgb_corr)
        out_image = f'{os.path.splitext(image)[0]}.tiff'
        pil_img.save(
            f"{output_dir_path}/{out_image}",
            format="TIFF",
            icc_profile=icc_profile,
            compression='tiff_adobe_deflate',
        )


if __name__ == '__main__':
    main()
