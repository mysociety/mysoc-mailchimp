import base64
import hashlib
import io
import json
import os
import re
from pathlib import Path

import mammoth
from bs4 import BeautifulSoup, NavigableString, Tag
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from typing_extensions import assert_never


def enforce_tag(item: Tag | None | NavigableString) -> Tag:
    """
    Typing assistant that throws an error if bs4 hasn't found a tag
    """
    match item:
        case Tag():
            return item
        case None | NavigableString():
            raise TypeError(f"Expected Tag, got {type(item)}")
        case _ as unreachable:  # type: ignore
            assert_never(unreachable)


def get_docx_from_file_id(file_id: str, working_dir: Path) -> Path:

    creds = json.loads(os.environ["GOOGLE_CLIENT_JSON"])

    credentials = service_account.Credentials.from_service_account_info(creds)
    drive_service = build("drive", "v3", credentials=credentials)

    request = drive_service.files().export_media(
        fileId=file_id,
        mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    # export this drive file to a local file
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)  # type: ignore

    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %d%%." % int(status.progress() * 100))

    fh.seek(0)

    storage_path = working_dir / f"{file_id}.docx"
    with open(storage_path, "wb") as f:
        f.write(fh.read())

    return storage_path


def extract_and_save_images(html: str, temp_dir: Path) -> str:
    """
    In a mammoth generated HTML file,
    the images are encoded and stored directly in the file.
    This function extracts the images and saves them to disk
    and updates the original reference.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Extract all images
    images = soup.find_all("img")

    # Loop through images
    for image in images:
        # extract the encoded image
        src = image["src"]
        # use hashed src as filename
        filename = hashlib.md5(src.encode("utf-8")).hexdigest()[:10]
        if src.startswith("data:"):
            # first comma seperates the metadata from the image data
            #  but we want to include any future commas
            metadata, encoded_image = src.split(",", 1)
            image_find = re.search(r"image/(.*);", metadata)
            if image_find is None:
                raise ValueError(f"Could not extract image type from {metadata}")
            file_ext = image_find.group(1)
            # decode the image
            decoded_image = base64.b64decode(encoded_image)
            # save the image to disk
            image_path = temp_dir / f"{filename}.{file_ext}"
            with open(image_path, "wb") as f:
                f.write(decoded_image)
            # update the image src to point to the new image
            image["src"] = str(image_path)

    # decompose any a tags with an id that starts with an _
    for a in soup.find_all("a"):
        if a.get("id", "").startswith("_"):
            a.decompose()

    return str(soup)


def convert_docx_to_html(docx_path: Path, working_folder: Path) -> str:
    with open(docx_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html: str = result.value  # The generated HTML
        messages = result.messages  # Any messages, such as warnings during conversion
    html = extract_and_save_images(html, working_folder)  # type: ignore
    if messages:
        print(messages)  # type: ignore
    # add newlines after any closing h or p or img tags.
    html = re.sub(r"(</h\d>|</p>|</img>)", r"\1\n\n", html)

    return html


def gdoc_to_html(file_id: str, working_folder: Path) -> str:
    """
    Download a Google Doc and convert it to HTML
    """
    docx_path = get_docx_from_file_id(file_id, working_folder)
    html = convert_docx_to_html(docx_path, working_folder)
    return html


if __name__ == "__main__":
    working_folder = Path("temp")
    working_folder.mkdir(exist_ok=True)
    file_id = "1CYfTKBwP2PgPcV0HasjbuXuh599GbATKUMVFBnfV_gk"
    content = gdoc_to_html(file_id, working_folder)
    Path("test.html").write_text(content)
