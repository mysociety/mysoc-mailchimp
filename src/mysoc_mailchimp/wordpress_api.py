import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import requests
from typing_extensions import Self

# WordPress API configuration
# Application password (5 four letter words seperated by spaces, get from profile page)
WORDPRESS_URL = os.environ.get("WORDPRESS_URL")
USERNAME = os.environ.get("WORDPRESS_USERNAME")
PASSWORD = os.environ.get("WORDPRESS_PASSWORD")


DraftOptions = Literal["draft", "publish", "future", "pending", "private"]


def get_category_id_from_name(category_names: list[str]) -> list[int]:
    """
    convert a list of category slugs to a list of category IDs
    """
    api_url = f"{WORDPRESS_URL}wp-json/wp/v2/categories"
    data = {
        "per_page": 50,
    }
    response = requests.get(api_url, auth=(USERNAME, PASSWORD), params=data, timeout=60)
    result = response.json()
    category_ids = []
    for category in result:
        if category["name"] in category_names:
            category_ids.append(category["id"])
    return category_ids


def get_author_id_from_username(username: str) -> int:
    """
    Get the author ID from the username.

    Args:
        username (str): The username to get the ID for.

    Returns:
        int: The author ID.
    """
    api_url = f"{WORDPRESS_URL}wp-json/wp/v2/users"
    data = {
        "per_page": 50,
    }
    response = requests.get(api_url, auth=(USERNAME, PASSWORD), params=data, timeout=60)
    result = response.json()
    for user in result:
        if user["slug"] == username:
            return user["id"]
    raise ValueError(f"User {username} not found")


@dataclass
class BlogImage:
    image_path: Path
    title: str = ""
    alt_text: str = ""
    caption: str = ""
    description: str = ""
    id: int = -1
    media_url: str = ""

    def upload_image(self) -> Self:
        """
        Upload an image to WordPress.
        """

        api_url = f"{WORDPRESS_URL}wp-json/wp/v2/media"
        image_file = self.image_path.read_bytes()
        # construct headers based on path type time and extension
        filename = self.image_path.name
        headers = {}
        match self.image_path.suffix:
            case ".png":
                headers["Content-Type"] = "image/png"
            case ".jpg" | ".jpeg":
                headers["Content-Type"] = "image/jpeg"
            case _:
                raise ValueError(f"File type {self.image_path.suffix} not supported")

        headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        json_data = {
            "title": self.title or self.image_path.name,
            "alt_text": self.alt_text or self.image_path.name,
        }
        response = requests.post(
            api_url,
            auth=(USERNAME, PASSWORD),
            headers=headers,
            data=image_file,
            timeout=60,
        )
        result = response.json()
        self.id = result["id"]

        # update the image with the rest of the data
        api_url = f"{WORDPRESS_URL}wp-json/wp/v2/media/{self.id}"
        response = requests.post(
            api_url,
            auth=(USERNAME, PASSWORD),
            json=json_data,
            timeout=60,
        )

        self.media_url = result["source_url"]
        return self


@dataclass
class BlogPost:
    title: str
    content: str
    categories: list[str] = field(default_factory=list)
    status: DraftOptions = "draft"
    author_username: str = "admin"
    featured_media: BlogImage | None = None

    def publish(self) -> int:

        username_id = get_author_id_from_username(self.author_username)
        category_ids = get_category_id_from_name(self.categories)

        # convert cateogires to comma seperated string
        category_ids = ",".join([str(i) for i in category_ids])
        api_url = f"{WORDPRESS_URL}wp-json/wp/v2/posts"
        data = {
            "title": self.title,
            "content": self.content,
            "status": self.status,
            "author": username_id,
            "categories": category_ids,
        }

        if self.featured_media:
            if self.featured_media.id == -1:
                self.featured_media.upload_image()
            data["featured_media"] = self.featured_media.id

        response = requests.post(
            api_url, auth=(USERNAME, PASSWORD), json=data, timeout=60
        )
        result = response.json()
        return result["id"]
