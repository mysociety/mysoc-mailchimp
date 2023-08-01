import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from PIL import Image
from ruamel.yaml import YAML
from typing_extensions import Self
from unsplash.api import Api as unsplash_api
from unsplash.auth import Auth

from .gdoc import gdoc_to_html
from .wordpress_api import BlogImage, BlogPost

# Unsplash API configuration
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_CLIENT_ID")


@dataclass
class WordpressConfig:
    """
    Dataclass for storing the injection phrases.
    """

    before_first_h2: str
    before_h2: str
    end_of_document: str
    categories: list[str]
    author: str

    @classmethod
    def from_yaml(cls, path: Path) -> Self:
        # check file is yaml file
        if path.suffix != ".yaml":
            raise ValueError("File must be a YAML file")
        yaml = YAML(typ="safe")
        data = yaml.load(path)
        return cls(**data)


@dataclass
class UnsplashData:
    """
    Dataclass for storing Unsplash image details.
    """

    url: str
    title: str
    author: str
    path: Path
    alt_text: str


def download_image(image_url: str, image_ext: str) -> Path:
    """
    Download the image from the given URL.

    Write to a temporary file and return the path to the file.
    """
    response = requests.get(image_url)
    # get filename from response

    # write to temporary file that includes the filename - do not delete
    # the file when it is closed
    temp_file = tempfile.NamedTemporaryFile(suffix=image_ext, delete=False)
    temp_file.write(response.content)
    temp_file.close()
    return Path(temp_file.name)


def inject_content(
    soup: BeautifulSoup, config: WordpressConfig, unsplash_data: UnsplashData
) -> BeautifulSoup:
    """ """
    # Custom content to be injected
    before_first_h2 = config.before_first_h2
    before_h2 = config.before_h2
    end_of_document = config.end_of_document

    unsplash_url = unsplash_data.url
    unsplash_author = unsplash_data.author

    html = str(soup)

    # inject before first h2
    html = re.sub(
        r"<h2>(.*?)</h2>",
        before_first_h2 + r"\n\n<h2 pos=1>\1</h2>",
        html,
        count=1,
    )

    # inject before each h2 that isn't the first one
    html = re.sub(
        r"<h2>(.*?)</h2>",
        before_h2 + r"\n\n<h2>\1</h2>\n\n",
        html,
    )

    # Create footer content with Unsplash image details
    footer_content = (
        f'<p>Image: <a href="{unsplash_url}">{unsplash_author}</a> on Unsplash.</p>'
    )

    # inject at end of document
    html += "\n\n" + end_of_document
    html += "\n\n" + footer_content

    soup = BeautifulSoup(html, "html.parser")

    return soup


def get_unsplash_image(url: str) -> UnsplashData:

    # Extract photo ID from the Unsplash URL
    photo_id = url.split("/")[-1]

    # Authenticate with the Unsplash API
    auth = Auth(UNSPLASH_ACCESS_KEY, "", "", "")
    api = unsplash_api(auth)

    # Fetch photo details from the Unsplash API
    photo = api.photo.get(photo_id)

    if not photo:
        raise ValueError("Invalid Unsplash URL")

    temp_path = download_image(photo.urls.raw, ".jpg")  # type: ignore

    # todo: resize image here
    image = Image.open(temp_path)
    # resize so never wider than 1200px, preserve aspect ratio, use anti-aliasing
    if image.width > 1200:
        image.thumbnail((1200, 1200), Image.BICUBIC)

    image.save(temp_path)

    return UnsplashData(
        url=url,
        author=photo.user.name,  # type: ignore
        path=temp_path,
        title=photo.description or "",  # type: ignore
        alt_text=photo.alt_description or "",  # type: ignore
    )


def load_blog_to_wordpress(
    google_url: str, unsplash_url: str | None, config_path: Path
):
    """
    Main function to download a Google Doc, extract images,
    and upload them as a new post to WordPress.
    """

    config = WordpressConfig.from_yaml(config_path)

    # get document_id from google_url
    document_id = google_url.split("/")[-2]

    working_folder = Path("temp")

    html_content = gdoc_to_html(document_id, working_folder)

    # Parse HTML content
    soup = BeautifulSoup(html_content, "html.parser")

    # check if any a tags in the document are a link to unsplash
    # if so, assume this is the unsplash_url we want, capture that
    # and decompose the tag
    for a in soup.find_all("a"):
        if a.get("href", "").startswith("https://unsplash.com/photos/"):
            unsplash_url = a["href"]
            a.decompose()
            break

    if not unsplash_url:
        raise ValueError("No Unsplash URL found in arguments or document")

    # Get Unsplash image and its details
    unsplash_data = get_unsplash_image(unsplash_url)

    # Inject custom content
    soup = inject_content(
        soup,
        config,
        unsplash_data,
    )

    html = str(soup)
    html = re.sub(r"(</h\d>|</p>|</img>)", r"\1\n\n", html)

    # Extract images and upload them to WordPress
    images = []
    for image_tag in soup.find_all("img"):
        image_path = Path(image_tag["src"])

        # get extention from image url
        i = BlogImage(
            image_path=image_path,
            title=image_tag.get("title") or "",
            alt_text=image_tag.get("alt") or "",
        ).upload_image()
        images.append(i)

        # Modify image source to point to the newly uploaded image
        image_tag["src"] = i.media_url
        # if the image is wider than 800 set the image width to 800,
        # and the height to auto
        image = Image.open(i.image_path)
        width, _ = image.size
        if width > 800:
            image_tag["width"] = "800"
            image_tag["height"] = "auto"
        image.close()

    # get first h1 as title
    title = "Placeholder title"
    for h1 in soup.find_all("h1"):
        title = h1.text
        h1.decompose()
        break

    # Prepare post content
    content = str(soup)

    html = re.sub(r"(</h\d>|</p>|</img>|</div>)", r"\1\n\n", html)

    # Create new post on WordPress
    categories = config.categories
    author_username = config.author

    featured_image = BlogImage(
        image_path=unsplash_data.path,
        title=unsplash_data.title,
        alt_text=unsplash_data.alt_text,
    )

    blog = BlogPost(
        title=title,
        content=content,
        categories=categories,
        author_username=author_username,
        featured_media=featured_image,
    )

    post_id = blog.publish()

    print("New post created with ID:", post_id)
    url = f"https://blogs.mysociety.org/mysociety/wp-admin/post.php?post={post_id}&action=edit&classic-editor__forget&classic-editor"
    print("Edit post at:", url)
