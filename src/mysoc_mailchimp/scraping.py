import requests
from bs4 import BeautifulSoup, Tag, NavigableString
from dataclasses import dataclass


@dataclass
class BlogPost:
    title: str = ""
    author: str = ""
    content: str = ""
    image_url: str = ""


def enforce_tag(item: Tag | None | NavigableString) -> Tag:
    """
    Typing assistant that throws an error if bs4 hasn't found a tag
    """
    if isinstance(item, Tag):
        return item
    else:
        raise TypeError(f"Expected Tag, got {type(item)}")


def get_details_from_blog(blog_url: str) -> BlogPost:
    """
    From a mySociety blog post, extract properties to put in the email
    """

    # check the url is a mySociety blog
    if not blog_url.startswith("https://www.mysociety.org"):
        raise ValueError("Not a mySociety blog post")

    r = requests.get(blog_url, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    blog = BlogPost()

    blog.title = enforce_tag(soup.find("h1", class_="mid-heading")).text

    blog.content = str(soup.find("div", class_="wordpress-editor-content"))

    blog.author = enforce_tag(
        soup.find("a", class_="blog-post-meta__author-name")
    ).text.strip()

    image_item = enforce_tag(
        soup.find("div", class_="photo-topper photo-topper--cover-image")
    )
    image_style: str = image_item["style"]  # type: ignore
    blog.image_url = image_style.split("url('")[1].split("')")[0]

    return blog
