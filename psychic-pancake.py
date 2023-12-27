import requests
import asyncio
import json
import logging
from csv import DictWriter
from sys import exception
from pathlib import Path
from typing import Optional, List, Tuple

import aiohttp
import typer
from PIL import Image
from rich.progress import track


"""
Todo
replace prints with warnings and/or exceptions where appropriate
enable logging along with rich
"""
app = typer.Typer()
logger = logging.getLogger(__name__)


def reporter(out_file: Path, cf_data: list) -> bool:
    """Creates report of URLs of uploaded images"""
    if out_file and cf_data:
        toprow = [
            "name",
            "id",
            "uploaded",
            "variants"
            ]
        if out_file.exists():
            row_list = []
        else:
            row_list = [toprow]
        with open(out_file, 'a', newline='') as f:
            writer = csv.writer(f)
            for entry in cf_data:
                result = entry['result']
                result_filename = result["filename"]
                result_id = result["id"]
                result_upload = result["uploaded"]
                result_variants = result["variants"]
                row_list.append(
                    [result_filename,
                     result_id,
                     result_upload,
                     result_variants]
                     )
            writer.writerows(row_list)
            f.close()
            return True
    return False

def type_check(unk: Path) -> bool:
    """Validates file is supported image type"""

    img_types = ("PNG", "JPEG")
    if unk:
        try:
            type_guess = Image.open(unk)
        except Exception:
            return False
        if type_guess and type_guess.format and type_guess.format in img_types:
            return True
    return False


def img_checker(
        img: Path,
        max_bytes: int = 10485760,
        max_dim: int = 12000,
        max_pixels: int = 100000000,
    ) -> bool:
    """Validate image against cloudflare restrictions"""

    if img:
        img_name = img.name
        img_bytes = img.stat().st_size
        img_w, img_h = (Image.open(img)).size
        if img_bytes > max_bytes: # check size. Images have a 10 megabyte size limit.
            logger.critical(
                f'{img_name} is {img_bytes} Megabytes and the max size is {max_bytes}'
            )
        elif (img_w*img_h) > max_pixels:# check image area. Maximum image area is limited to 100 megapixels (for example, 10,000×10,000 pixels).
            logger.critical(
                f'The file {img_name} is {img_w*img_h} pixels and the max pixel count is {max_pixels}'
            )
        elif (img_w or img_h) > max_dim:# check file dimensions. Maximum image single dimension is 12,000 pixels.
            logger.critical(
                f'The file {img_name} is {img_w} by {img_h} pixels and the max single dimension is {max_dim}'
            )
        else:
            return True
    return False


def input_handler(input: Path) -> list[Path]:
    """Accepts image/directory input and returns list"""
    if input:
        input_list = [f for f in input.iterdir() if f.is_file()]
        return input_list
    logger.critical("CHECK-FAIL: Image input missing")

def cf_upload(img: Path, token: str, id: str) -> json:
    """Upload image to Cloudflare and return json data"""
    if img and token and id:
        resp = requests.post(
            f'https://api.cloudflare.com/client/v4/accounts/{id}/images/v1',
            headers={'Authorization': f'Bearer {token}'},
            files={'file': (img.stem, open(img, 'rb'))}
            )
        if resp.status_code != 200:
            logger.critical(f'ERROR:
                {resp.status_code},
                {resp.raise_for_status},
                {resp.text}'
                )
        else:
            resp_json = json.loads(resp.text)
            if resp_json["success"] is True:
                return resp_json

@app.command()
def psychicpancake(
    input: Path = typer.Option(
        None,
        "-i",
        help="Image or directory of images to be uploaded"
    ),
    report: Optional(Path) = typer.Option(
        "upload_report.csv",
        "-r",
        help="Report of URLs of the uploaded images"
    ),
    token: str = typer.Option(
        None,
        "-t",
        help="Cloudflare token for image API"
    ),
    id: str = typer.Option(
        None,
        help="Cloudflare account ID"
    ),
    verbose: Optional[int] = typer.Option(
        0,
        "-v",
        count=True,
        max=4,
        help="Log verbosity level"
    )
):
    logging.basicConfig(level=(((verbose + 5) * 10) - (verbose * 20)))
    if input and token and id:
        img_list = input_handler(input=input.resolve())
        for item in img_list:
            if type_check(unk=item) is False:
                logger.critical(f'CHECK-FAIL: {item} is not a supported file type')
            elif img_checker(img=item) is False:
                logger.critical(f'CHECK-FAIL: {item} does not meet requirements')
            else:
                img_json_list = []
                img_json_list.append(cf_upload(img=item, token=token, id=id))
        if reporter(out_file=report, cf_data=img_json_list):
            logger.info(f'Success')
        else:
            raise Exception
    else:
        raise Exception

if __name__ == "__main__":
    app()