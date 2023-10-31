from pathlib import Path

import argparse
import csv
import json
import requests
from PIL import Image
from rich import print

"""
Todo
replace prints with warnings and/or exceptions where appropriate
enable logging along with rich
"""

# Initialize parser and cli arguments
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output", required=False, help="Output CSV file")  # might be able to require file type
parser.add_argument("-i", "--input", required=True,
                    help="Input image or directory")  # might be able to require file type
parser.add_argument("-T", "--cftoken", required=False, help="Cloudflare token")
parser.add_argument("-I", "--cfid", required=False, help="Cloudflare account ID")
args = parser.parse_args()


def output_handler(out_file: Path, cf_data: list) -> bool:  # create output file and append image data to csv
    if out_file and cf_data:
        toprow = [
            "name",
            "id",
            "uploaded",
            "variants"
        ]
        if out_file.exists():
            writemode = 'a'
            row_list = []
        else:
            writemode = 'w'
            row_list = [toprow]
        with open(out_file, writemode, newline='') as f:
            writer = csv.writer(f)
            for entry in cf_data:
                images = entry["result"]["images"]
                images_filename = images["filename"]
                images_id = images["id"]
                images_upload = images["uploaded"]
                images_variants = images["variants"]
                row_list.append(
                    [
                        images_filename,
                        images_id,
                        images_upload,
                        images_variants
                    ]
                )
            writer.writerows(row_list)
            f.close()
            return True
    return False


def type_check(unk_type: Path) -> bool:  # validate file is desired image type
    image_types = ("PNG", "JPEG")
    if unk_type:
        type_guess = Image.open(unk_type)
        if type_guess and type_guess.format and type_guess.format in image_types:
            return True
    return False


def img_handler(img: Path) -> bool:  # validate image against cloudflare restrictions
    if img:
        img_name = img.name
        img_bytes = img.stat().st_size
        img_w, img_h = (Image.open(img)).size

        # Cloudflare restrictions
        cf_maxbytes = 10485760
        cf_maxdimension = 12000
        cf_maxpixel = 100000000

        if (type_check(img)) is False:  # validate type
            print(f'The file type for {img_name} is currently not supported')
        elif img_bytes > cf_maxbytes:  # check size. Images have a 10 megabyte size limit.
            print(f'The file {img_name} is {img_bytes} Megabytes and the max size is {cf_maxbytes}')
        elif (
                img_w * img_h) > cf_maxpixel:  # check image area. Maximum image area is limited to 100 megapixels (for example, 10,000×10,000 pixels).
            print(f'The file {img_name} is {img_w * img_h} pixels and the max pixel count is {cf_maxpixel}')
        elif (
                img_w or img_h) > cf_maxdimension:  # check file dimensions. Maximum image single dimension is 12,000 pixels.
            print(f'The file {img_name} is {img_w} by {img_h} pixels and the max single dimension is {cf_maxdimension}')
        else:
            return True
    raise Exception


def input_handler(input_arg: Path) -> list:  # determine file or directory and return list of files
    if input_arg:
        if input_arg.is_dir():
            input_list = [f for f in input_arg.iterdir() if f.is_file()]
            return input_list
        elif input_arg.is_file():
            return [input_arg]
    raise Exception


def cf_upload(img: Path):  # define cloudflare upload function and return json data
    cftoken = args.cftoken
    cfid = args.cfid
    if img and cftoken and cfid:
        resp = requests.post(
            f'https://api.cloudflare.com/client/v4/accounts/{cfid}/images/v1',
            headers={'Authorization': f'Bearer {cftoken}'},
            files={'file': (img.stem, open(img, 'rb'))}
        )
        if resp.status_code != 200:
            print(
                resp.status_code,
                resp.raise_for_status,
                resp.text
            )
        else:
            resp_json = json.loads(resp.text)
            if resp_json["success"] is "true":
                return resp_json
    raise Exception


def main():
    input_args = args.input
    output = args.output
    if input_args and output:
        input_args = Path.resolve(input_args)
        output = Path.resolve(output)
        img_json_list = []
        input_list = input_handler(input_arg=input_args)
        for item in input_list:
            item = Path.resolve(item)
            if type_check(unk_type=item) is False:
                # raise Warning and move to next item
                print("error")
            elif img_handler(img=item) is False:
                # raise Warning and move to next item
                print("error")
            else:
                img_json = cf_upload(img=item)
                img_json_list.append(img_json)
        if output_handler(out_file=output, cf_data=img_json_list):
            print("Success")
        else:
            raise Exception
    else:
        raise Exception


if __name__ == "__main__":
    main()
