import logging
import shlex
import subprocess
import sys
from argparse import ArgumentParser
from argparse import Namespace
from asyncio import Semaphore
from asyncio import TaskGroup
from asyncio import run
from asyncio import to_thread
from pathlib import Path
from shutil import copyfileobj
from subprocess import CalledProcessError
from typing import Any
from urllib.parse import urljoin
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

work_dir = Path("work")

download_semaphore = Semaphore(2)
convert_semaphore = Semaphore(5)


class UserError(Exception):
    pass


def download_file(url: str, dest_path: Any) -> None:
    logging.info(f"Downloading to {dest_path}.")

    temp_download_path = dest_path.with_stem(f"{dest_path.stem}~")
    temp_download_path.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True) as response:
        with open(temp_download_path, "wb") as fp:
            copyfileobj(response.raw, fp)

    temp_download_path.rename(dest_path)


def convert_file(source_file: Any, dest_path: Any, track_nr: int) -> None:
    logging.info(f"Converting to {dest_path}.")

    temp_output_path = dest_path.with_stem(f"{dest_path.stem}~")
    temp_output_path.parent.mkdir(parents=True, exist_ok=True)

    # In the published files, not all chapters have exactly the
    # same metadata. This leads to Books.app on iOS ignoring some
    # files. The easiest solution is to just overwrite or remove
    # all metadata that looks like it could trigger this.
    metadata = dict(
        artist="Evan Doorbell",
        album="Telephone Tapes — Group 1 Playlist",
        track=f"{track_nr}",
        date="",
        comment="",
        genre="",
    )

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                # Mixing status output of parallel invocations of ffmpeg is not helpful.
                "-nostats",
                *("-i", f"{source_file}"),
                *("-c:a", "aac_at"),
                *("-q:a", "2"),
                # Drop cover art.
                "-vn",
                *(j for k, v in metadata.items() for j in ["-metadata", f"{k}={v}"]),
                f"{temp_output_path}",
            ],
            # Prevent ffmpeg from changing TTY settings.
            input=b"",
            check=True,
        )
    except CalledProcessError as e:
        raise UserError(f"Command failed: {shlex.join(e.cmd)}")

    temp_output_path.rename(dest_path)


async def process_episode(index: int, url: str) -> None:
    _, _, file_name = urlsplit(url).path.rpartition("/")
    download_path = (work_dir / "downloads" / file_name).with_suffix(".flac")
    output_path = (work_dir / "output" / file_name).with_suffix(".m4b")

    if not download_path.exists():
        async with download_semaphore:
            await to_thread(lambda: download_file(url, download_path))

    if not output_path.exists():
        async with convert_semaphore:
            await to_thread(lambda: convert_file(download_path, output_path, index))


def parse_args() -> Namespace:
    parser = ArgumentParser()

    return parser.parse_args()


async def main() -> None:
    page_url = "https://evan-doorbell.com/group-1-playlist/"
    soup = BeautifulSoup(requests.get(page_url).content, "html.parser")

    async with TaskGroup() as tg:
        for i, link_elem in enumerate(soup.select('a[title="FLAC"]'), 1):
            href = link_elem["href"]
            assert isinstance(href, str)
            file_url = urljoin(page_url, href)

            _ = tg.create_task(process_episode(i, file_url))


def entry_point() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        run(main(**vars(parse_args())))
    except UserError as e:
        logging.error(f"error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.error("Operation interrupted.")
        sys.exit(130)
