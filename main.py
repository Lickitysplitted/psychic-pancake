import os, requests, json, argparse
from PIL import Image
from pathlib import Path
from rich import print as rprint
from rich.console import console

#Initialize parser and cli arguments
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output", required=False, help = "Output file")# might be able to specifiy file type
parser.add_argument("-i", "--input", help = "Input image")# might be able to specifiy file type
parser.add_argument("-T", "--cftoken", required=False, help = "Cloudflare token")
parser.add_argument("-I", "--cfid", required=False, help = "Cloudflare account ID")
args = parser.parse_args()

def output(outfile: Path, cf_data: dict):
    if outfile:
        outfile = Path.resolve(outfile)
        # create outfile if it doesn't exist
        # add cloudflare image data dict to output csv file

def type_check(unk_type):# validate file is desired image type
    image_types = ("PNG", "JPEG")
    if unk_type:
        type_guess = Image.open(unk_type)
        if type_guess and type_guess.format and type_guess.format in image_types:
            return True
    return False

def img_handler(img: Path):# validate image against cloudflare requirements
    img = Path(img).resolve()
    img_name = img.name()
    img_bytes = img.stat().st_size
    img_w, img_h = (Image.open(img.resolve())).size

    # Cloudflare restrictions
    cf_maxbytes = 10485760
    cf_maxdimension = 12000
    cf_maxpixel = 100000000

    if img.is_file() == False:# validate access
        rprint(
            f'The image {img_name} is not available. Please check the path and filename and try again.'
            )
    elif (type_check(img.resolve())) == False:# validate type
        rprint(
            f'The file type for {img_name} is currently not supported'
            )
    elif img_bytes > cf_maxbytes:# check size. Images have a 10 megabyte size limit.
        rprint(
            f'The file {img_name} is {img_bytes} Megabytes and the max size is {cf_maxbytes}'
            )
    elif (img_w*img_h) > cf_maxpixel:# check image area. Maximum image area is limited to 100 megapixels (for example, 10,000×10,000 pixels).
        rprint(
            f'The file {img_name} is {img_w*img_h} pixels and the max pixel count is {cf_maxpixel}'
            )
    elif (img_w or img_h) > cf_maxdimension:# check file dimensions. Maximum image single dimension is 12,000 pixels.
        rprint(
            f'The file {img_name} is {img_w} by {img_h} pixels and the max single dimension is {cf_maxdimension}'
            )
    else:
        return True

def input_handler(input: Path):
    if input:
        # check if exists
        # if file then run file then run file handler
        # if directory then run directory handler

    # take cli args for directory and validate access and file type and get count
    input_path = Path(Path.resolve(input))
    # validate access
    if input.is_file():
        raise Exception('This is a file')
    else:
        input_dirfiles = [f for f in os.listdir(input_path) if os.path.isfile(f)]
        for input_dirfile in input_dirfiles:
            input_dirfileabspath = Path.resolve(input_dirfile)
            input_dirfilename = os.path.splitext(os.path.basename(input_dirfileabspath))
            if (type_check(input_dirfileabspath)) == False:# validate type
                rprint(f'The file type for {input_dirfilename[0]} is currently not supported')

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
        rprint(resp.status_code, resp.raise_for_status, resp.text)
    else:
        resp_json = json.loads(resp.text)
        rprint(resp_json)

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
    rprint(f'Input image and input directory were both provided. Only one input can be specified at a time.')
elif (not args.input_directory) and (not args.input):
    rprint(f'No image or directory inputs specified. Please provide one input.')
elif args.input_directory and not args.input:
    directory_handler(args.input_directory)
elif args.input and not args.input_directory:
    img_handler(args.input)

def main():
    input = args.input
    if input:
        input = Path(input).resolve
        if input.is_dir:
            for item in input.iterdir():
                if item.is_file:
                    if type_check(unk_type=item) is False:
                        # raise Warning and move to next item
                        rprint("error")
                    elif img_handler(img=item) is False:
                        # raise Warning and move to next item
                        rprint("error")
                    else:
                        img_data = cf_upload(img=item)
                        output(img_data)
        elif input.is_file:
            if type_check(input):
                if type_check(unk_type=input) is False:
                    # raise Warning and move to next item
                    rprint("error")
                elif img_handler(img=input) is False:
                    # raise Warning and move to next item
                    rprint("error")
                else:
                    img_data = cf_upload(img=input)
                    output(img_data)
        else:
            # raise Warning and move to next item
            rprint("error")

if __name__ == "__main__":
    main()