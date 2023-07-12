from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from typing_extensions import assert_never


@dataclass
class BlogPost:
    """
    Data structure for information retrieved from a mySociety blog post
    """

    url: str = ""
    desc: str = ""
    title: str = ""
    author: str = ""
    content: str = ""
    image_url: str = ""


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


def get_details_from_blog(blog_url: str) -> BlogPost:
    """
    From a mySociety blog post, extract properties to put in the email
    """
    banned_phrases = [
        "<p>You can sign up here and you’ll get an email every time we post:</p>"
    ]

    # check the url is a mySociety blog
    if not blog_url.startswith("https://www.mysociety.org"):
        raise ValueError("Not a mySociety blog post")

    r = requests.get(blog_url, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    blog = BlogPost(url=blog_url)

    blog.title = enforce_tag(soup.find("h1", class_="mid-heading")).text

    # extract social description
    content = enforce_tag(soup.find("meta", property="og:description"))["content"]

    match content:
        case str():
            blog.desc = content
        case list():
            blog.desc = content[0]

    contents = enforce_tag(soup.find("div", class_="wordpress-editor-content"))

    # remove any divs with the class "mailchimp-signup"
    for item in contents.find_all("div", class_="mailchimp-signup"):
        item.decompose()

    # remove any items with the class "web-only"
    for item in contents.find_all(class_="web-only"):
        item.decompose()

    # remove donate box
    for item in contents.find_all(class_="blog-post-donate"):
        item.decompose()

    # remove any paragraphs that contain the banned phrases
    for phrase in banned_phrases:
        for item in contents.find_all("p"):
            if phrase in item.text:
                item.decompose()

    blog.content = str(contents)

    # remove any double new lines
    while "\n\n" in blog.content:
        blog.content = blog.content.replace("\n\n", "\n")

    blog.author = enforce_tag(
        soup.find("a", class_="blog-post-meta__author-name")
    ).text.strip()

    image_item = enforce_tag(
        soup.find("div", class_="photo-topper photo-topper--cover-image")
    )
    image_style: str = image_item["style"]  # type: ignore
    blog.image_url = image_style.split("url('")[1].split("')")[0]

    return blog
