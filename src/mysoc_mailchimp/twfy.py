"""
Helper functions given a blog, to get the annoucement config in the json

This is an example of the json format expected for annoucements:

   {
      "title":"Repowering democracy",
      "content":"A new series on democracy and technology, in your inbox weekly.",
      "url":"https://www.mysociety.org/2023/06/09/repowering-democracy-new-ideas-straight-to-your-inbox/",
      "thumbnail_image_url":"https://www.mysociety.org/files/2023/06/marek-piwnicki-jFukTjphXbI-unsplash-1.jpg",
      "thumbnail_image_alt_text":"Mountains against an orange sunset",
      "format":"link",
      "button_text": "Read more",
      "button_class":"",
      "published":true,
      "lang": "en",
      "weight":1,
      "location":[
         "homepage"
      ]
   },

and for banners:

   {
      "id":"senedd-launch",
      "content":"TheyWorkForYou now covers the Senedd",
      "button_text":"Learn more",
      "button_link":"https://www.mysociety.org/mysociety/?p=52330&utm_source=theyworkforyou&utm_medium=website&utm_campaign=banner/",
      "button_class":"button--negative",
      "weight":1,
      "lang":"en",
      "published":true,
      "start_time":"2023-06-14"
   },

"""

from __future__ import annotations

import datetime
import json
from typing import Literal

import rich

from .scraping import BlogPost, get_details_from_blog

DateOptions = Literal["today", "tomorrow"]


def print_json_config(
    blog_url: str, start: DateOptions = "tomorrow", days_up: int = 14
):
    """
    Given a blog url, print the json config for an announcement
    """

    blog = get_details_from_blog(blog_url)

    base_admin_url = "https://www.theyworkforyou.com/admin/banner.php?editorial_option="

    annoucement_text = convert_blog_to_announcement(blog, start, days_up)
    banner_text = convert_blog_to_banner(blog, start, days_up)

    rich.print(
        f"[blue] Add this here: {base_admin_url}announcements [/blue]",
    )

    rich.print_json(annoucement_text)

    rich.print(
        f"[blue] Add this here: {base_admin_url}banner [/blue]",
    )

    rich.print_json(banner_text)


def convert_blog_to_announcement(
    blog: BlogPost, start: DateOptions = "tomorrow", days_up: int = 14
) -> str:
    """
    Given a blog url, return the json for an announcement
    """

    blog_url = blog.url

    # add utm campaign info to url if there's not already a utm_campaign
    if "utm_campaign" not in blog_url and "?" not in blog_url:
        blog_url += (
            "?utm_source=theyworkforyou&utm_medium=website&utm_campaign=announcement"
        )

    today = datetime.datetime.now()
    tomorrow = today + datetime.timedelta(days=1)

    if start == "today":
        start_time = today.strftime("%Y-%m-%d")
    elif start == "tomorrow":
        start_time = tomorrow.strftime("%Y-%m-%d")
    else:
        raise ValueError("start must be 'today' or 'tomorrow'")

    end_time = (tomorrow + datetime.timedelta(days=days_up)).strftime("%Y-%m-%d")

    announcement = {
        "title": blog.title,
        "content": blog.desc,
        "url": blog_url,
        "thumbnail_image_url": blog.image_url,
        "thumbnail_image_alt_text": "",
        "format": "link",
        "button_text": "Read more",
        "button_class": "",
        "published": True,
        "lang": "en",
        "weight": 1,
        "location": ["homepage", "sidebar"],
        "start_time": start_time,
        "end_time": end_time,
    }

    return json.dumps(announcement)


def convert_blog_to_banner(
    blog: BlogPost, start: DateOptions = "tomorrow", days_up: int = 14
) -> str:
    """
    Given a blog url, return the json for a banner
    """

    blog_url = blog.url

    if "utm_campaign" not in blog_url and "?" not in blog_url:
        blog_url += "?utm_source=theyworkforyou&utm_medium=website&utm_campaign=banner"

    today = datetime.datetime.now()
    tomorrow = today + datetime.timedelta(days=1)

    if start == "today":
        start_time = today.strftime("%Y-%m-%d")
    elif start == "tomorrow":
        start_time = tomorrow.strftime("%Y-%m-%d")
    else:
        raise ValueError("start must be 'today' or 'tomorrow'")

    end_time = (tomorrow + datetime.timedelta(days=days_up)).strftime("%Y-%m-%d")

    banner = {
        "id": "blog-" + blog_url.split("/")[-2],
        "content": blog.title,
        "button_text": "Read more",
        "button_link": blog_url,
        "button_class": "button--negative",
        "weight": 1,
        "lang": "en",
        "published": True,
        "start_time": start_time,
        "end_time": end_time,
    }

    return json.dumps(banner)
