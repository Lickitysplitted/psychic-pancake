import argparse
import logging
from pathlib import Path
from csv import DictWriter

import requests
from PIL import Image
from rich.logging import RichHandler

# Setup rich logging
logging.basicConfig(
    level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)
logger = logging.getLogger("rich")

# Initialize parser and CLI arguments
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output", help="Output CSV file")
parser.add_argument("-i", "--input", required=True, help="Input image or directory")
parser.add_argument("-T", "--cftoken", help="Cloudflare token")
parser.add_argument("-I", "--cfid", help="Cloudflare account ID")
args = parser.parse_args()

# Constants for Cloudflare restrictions
CF_MAX_BYTES = 10485760
CF_MAX_DIMENSION = 12000
CF_MAX_PIXEL = 100000000
SUPPORTED_IMAGE_TYPES = ("PNG", "JPEG")


def output_handler(out_file: Path, cf_data: list) -> bool:
    if not out_file or not cf_data:
        return False

    fieldnames = ["name", "id", "uploaded", "variants"]
    write_mode = 'a' if out_file.exists() else 'w'

    try:
        with open(out_file, write_mode, newline='') as f:
            writer = DictWriter(f, fieldnames=fieldnames)
            if write_mode == 'w':
                writer.writeheader()
            for entry in cf_data:
                result = entry["result"]
                writer.writerow({
                    "name": result["filename"],
                    "id": result["id"],
                    "uploaded": result["uploaded"],
                    "variants": result["variants"]
                })
        return True
    except Exception as e:
        logger.error(f"Error writing to output file: {e}")
        return False


def type_check(unk_type: Path) -> bool:
    if not unk_type:
        return False

    try:
        with Image.open(unk_type) as img:
            return img.format in SUPPORTED_IMAGE_TYPES
    except IOError as e:
        logger.warning(f"Error opening image {unk_type}: {e}")
        return False


def img_handler(img: Path) -> bool:
    if not img:
        return False

    img_name = img.name
    img_bytes = img.stat().st_size
    img_w, img_h = Image.open(img).size

    if not type_check(img):
        logger.warning(f'The file type for {img_name} is currently not supported')
    elif img_bytes > CF_MAX_BYTES:
        logger.warning(
            f'The file {img_name} is {img_bytes} bytes and exceeds the max size limit of {CF_MAX_BYTES} bytes.')
    elif (img_w * img_h) > CF_MAX_PIXEL:
        logger.warning(
            f'The file {img_name} is {img_w * img_h} pixels and exceeds the max pixel count of {CF_MAX_PIXEL}.')
    elif img_w > CF_MAX_DIMENSION or img_h > CF_MAX_DIMENSION:
        logger.warning(
            f'The file {img_name} is {img_w} by {img_h} pixels and exceeds the max single dimension of {CF_MAX_DIMENSION}.')
    else:
        return True

    return False


def input_handler(input_path: Path) -> list:
    if not input_path:
        return []

    if input_path.is_dir():
        return [f for f in input_path.iterdir() if f.is_file()]
    elif input_path.is_file():
        return [input_path]
    else:
        logger.warning(f"Invalid input path: {input_path}")
        return []


def cf_upload(img: Path):
    cftoken = args.cftoken
    cfid = args.cfid

    if not (img and cftoken and cfid):
        return None

    try:
        with open(img, 'rb') as file:
            resp = requests.post(
                f'https://api.cloudflare.com/client/v4/accounts/{cfid}/images/v1',
                headers={'Authorization': f'Bearer {cftoken}'},
                files={'file': (img.stem, file)}
            )

        if resp.status_code != 200:
            logger.error(f"Error in Cloudflare upload: {resp.status_code}, {resp.text}")
            return None

        resp_json = resp.json()
        if resp_json.get("success"):
            return resp_json
        else:
            logger.error(f"Cloudflare upload unsuccessful: {resp_json}")
            return None
    except Exception as e:
        logger.error(f"Error in Cloudflare upload: {e}")
        return None


def main():
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None

    if not input_path:
        logger.error("Input path is required")
        return

    img_json_list = []
    input_list = input_handler(input_path)

    for item in input_list:
        if not img_handler(item):
            continue

        img_json = cf_upload(item)
        if img_json:
            img_json_list.append(img_json)

    if output_path and not output_handler(output_path, img_json_list):
        logger.error("Failed to process output.")

    logger.info("Processing completed.")


if __name__ == "__main__":
    main()
