import os, requests, json, argparse, sys, filetype
from PIL import Image as PILImage
from exif import Image as exifImage
from PIL.ExifTags import TAGS
from pathlib import Path
from rich import print
import logging

logging.basicConfig(level=logging.DEBUG)

#Initialize parser and cli arguments
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--outputfile", required=False, help = "Output file")# might be able to specifiy file type
parser.add_argument("-i", "--input", help = "Input image")# might be able to specifiy file type
parser.add_argument("-d", "--input_directory", help = "Input directory")
parser.add_argument("-T", "--cftoken", required=False, help = "Cloudflare token")
parser.add_argument("-I", "--cfid", required=False, help = "Cloudflare account ID")
parser.add_argument("-H", "--cfhash", required=False, help = "Cloudflare account hash")
args = parser.parse_args()

def meta_scrubber(input_abspath):# scrub all metadata
    dirtyimg = exifImage(open(input_abspath, 'rb'))
    # checkimg = PILImage.open(input_abspath)
    # for tag, value in checkimg._getexif().items():
    #     print(TAGS.get(tag), value)
    if dirtyimg.has_exif == True:
        print(dirtyimg.list_all())

def type_handler(unk_type):# validate file is supported image type
    # PNG - very common and the current format used
    # GIF - common but not currently used by the bot
    # JPG - very common and a must
    # WebP (Cloudflare Images does not support uploading animated WebP files) - considering dropping this as it is not a common user format
    # SVG - supported but more work is needed to incorporate svghush to clean metadata
    supportedtypes = ("png", "jpg")
    if unk_type:
        file_guess = filetype.guess(unk_type)
        if file_guess and file_guess.extension and file_guess.extension in supportedtypes:
            return True
    return False

def img_handler(input):# validate image against cloudflare requirements
    input_name = os.path.splitext(os.path.basename(input))
    input_abspath = os.path.abspath(input)
    input_bytes = os.path.getsize(input_abspath)
    input_size = int(input_bytes/(1048576))
    maxsize = 10
    input_w, input_h = (PILImage.open(input_abspath)).size
    maxdimension = 12000
    maxpizel = 100000000
    # check GIF pixel size. Animated GIFs, including all frames, are limited to 50 megapixels (MP).
    
    if os.path.isfile(input) == False:# validate access
        print(f'The image {input_name} is not available. Please check the path and filename and try again.')
    elif (type_handler(input_abspath)) == False:# validate type
        print(f'The file type for {input_name[0]} is currently not supported')
    elif input_size > maxsize:# check size. Images have a 10 megabyte size limit.
        print(f'The file {input_name[0]+input_name[1]} is {input_size} Megabytes and the max size is {maxsize}')
    elif (input_w*input_h) > maxpizel:# check image area. Maximum image area is limited to 100 megapixels (for example, 10,000×10,000 pixels).
        print(f'The file {input_name[0]} is {input_w*input_h} pixels and the max pixel count is {maxpizel}')
    elif (input_w or input_h) > maxdimension:# check file dimensions. Maximum image single dimension is 12,000 pixels.
        print(f'The file {input_name[0]} is {input_w} by {input_h} pixels and the max single dimension is {maxdimension}')
    else:
        cleanimgabspath = os.path.abspath(meta_scrubber(input_abspath))
        cf_upload(input_name[0], cleanimgabspath)

def directory_handler(input_dir: Path):
    # take cli args for directory and validate access and file types and get count
    input_path = Path(os.path.abspath(input_dir))
    # validate access
    if input_dir.is_file():
        raise Exception('This is a file')
    else:
        input_dirfiles = [f for f in os.listdir(input_path) if os.path.isfile(f)]
        for input_dirfile in input_dirfiles:
            input_dirfileabspath = os.path.abspath(input_dirfile)
            input_dirfilename = os.path.splitext(os.path.basename(input_dirfileabspath))
            if (type_handler(input_dirfileabspath)) == False:# validate type
                print(f'The file type for {input_dirfilename[0]} is currently not supported')

        #gather file count of images

    # create file count

# define cloudflare upload function
def cf_upload(filename, abspath):
    cftoken = args.cftoken
    cfid = args.cfid
    resp = requests.post(
        f'https://api.cloudflare.com/client/v4/accounts/{cfid}/images/v1',
        headers={'Authorization': f'Bearer {cftoken}'},
        files={'file': (filename, open(abspath, 'rb'))}
        )
    if resp.status_code != 200:
        print(resp.status_code, resp.raise_for_status, resp.text)
    else:
        respjson = json.loads(resp.text)
        print(respjson)

def cloudflare_upload(fpath: Path,
                      cf_token: str,
                      cf_account: str,
                      ):
    """
    """
    if fpath.is_dir():
        raise Exception('This is a directory')
    fext = fpath.name.split('.')[-1]
    fname = '.'.join(fpath.name.split('.')[:-1])
    resp = requests.post(
        f'https://api.cloudflare.com/client/v4/accounts/{cf_account}/images/v1',
        headers={'Authorization': f'Bearer {cf_token}'},
        files={'file': (fname, fpath.open('rb'))}
    )


if args.input_directory and args.input:
    print(f'Input image and input directory were both provided. Only one input can be specified at a time.')
elif (not args.input_directory) and (not args.input):
    print(f'No image or directory inputs specified. Please provide one input.')
elif args.input_directory and not args.input:
    directory_handler(args.input_directory)
elif args.input and not args.input_directory:
    img_handler(args.input)