import datetime
import os
from functools import lru_cache
from typing import Any

import mailchimp_marketing
import pandas as pd
import requests


def get_client() -> mailchimp_marketing.Client:
    """
    Get the mailchimp api client
    """
    client = mailchimp_marketing.Client()
    client.set_config({"api_key": os.environ.get("MAILCHIMP_API_KEY"), "server": "us9"})
    return client


@lru_cache
def get_lists() -> pd.DataFrame:
    """
    Get dataframe of all lists in the account.
    """
    client = get_client()
    response: dict[str, Any] = client.lists.get_all_lists(count=1000)
    df = pd.DataFrame(response["lists"])

    # explode the list of dictionaries
    # in the 'stats' column into columns in their own right
    df = pd.concat([df.drop(["stats"], axis=1), df["stats"].apply(pd.Series)], axis=1)
    df = df[["id", "web_id", "name", "member_count"]]
    df = df.sort_values("name")

    return df


def get_segments(list_web_id: str) -> pd.DataFrame:
    """
    Get segements of a list as a dataframe
    """
    client = get_client()
    # if list_web_id can be converted to an int, it's a webid, otherwise it's a name
    try:
        list_id = int(list_web_id)
        is_web_id = True
    except ValueError:
        is_web_id = False
    if is_web_id:
        list_id = list_web_id_to_unique_id(list_web_id)
    else:
        list_id = list_name_to_unique_id(list_web_id)
    response: dict[str, Any] = client.lists.list_segments(list_id, count=1000)
    df = pd.DataFrame(response["segments"])
    df = df[["id", "name", "member_count"]]
    df["id"] = list_web_id + ":" + df["id"].astype(str)
    return df


@lru_cache
def get_recent_campaigns(count: int = 20) -> pd.DataFrame:
    """
    Get latest campaigns as a dataframe
    """
    client = get_client()
    response: dict[str, Any] = client.campaigns.list(
        count=count, sort_field="create_time", sort_dir="DESC"
    )
    df = pd.DataFrame(response["campaigns"])
    df["subject_line"] = df["settings"].apply(lambda x: x.get("subject_line", ""))
    df["title"] = df["settings"].apply(lambda x: x["title"])
    df["recipient_count"] = df["recipients"].apply(lambda x: x["recipient_count"])
    df = df[
        [
            "id",
            "web_id",
            "type",
            "content_type",
            "title",
            "status",
            "send_time",
            "recipient_count",
        ]
    ]

    return df


def get_templates() -> pd.DataFrame:
    """
    Get templates as a dataframe
    """
    client = get_client()
    response: dict[str, Any] = client.templates.list(count=1000)
    df = pd.DataFrame(response["templates"])
    df = df[
        [
            "id",
            "type",
            "name",
            "date_created",
            "drag_and_drop",
        ]
    ]
    # limit to type user
    df = df[df["type"] == "user"]
    return df


def campaign_web_id_to_unique_id(web_id: str) -> str:
    """
    Convert a campaign web id to a campaign id
    """
    df = get_recent_campaigns(1000)
    # convert to web_id, id column dict
    lookup = df.set_index("web_id")["id"].to_dict()
    return lookup[int(web_id)]


def list_web_id_to_unique_id(web_id: str) -> str:
    """
    Convert a list web id to a list id
    """
    df = get_lists()
    # convert to web_id, id column dict
    df["web_id"] = df["web_id"].astype(str)
    lookup = df.set_index("web_id")["id"].to_dict()
    return lookup[web_id]


def list_name_to_unique_id(name: str) -> str:
    """
    Convert a list's human name to a unique list id
    """
    df = get_lists()
    # convert to web_id, id column dict
    df["name"] = df["name"].astype(str)
    lookup = df.set_index("name")["id"].to_dict()
    return lookup[name]


def segment_name_to_unique_id(list_id: str, name: str) -> int:
    """
    Convert a segment's human name to a unique segment id
    """
    df = get_segments(list_id)
    # convert to web_id, id column dict
    df["name"] = df["name"].astype(str)
    lookup = df.set_index("name")["id"].to_dict()
    return lookup[name].split(":")[1]


def template_name_to_unique_id(name: str) -> int:
    """
    Convert a template's human name to a unique template id
    """
    df = get_templates()
    # convert to web_id, id column dict
    df["name"] = df["name"].astype(str)
    lookup = df.set_index("name")["id"].to_dict()
    return lookup[name]


def send_test_email(campaign_web_id: str, emails: list[str]) -> bool:
    """
    send a test email
    """
    client = get_client()
    campaign_id = campaign_web_id_to_unique_id(campaign_web_id)
    response: requests.models.Response = client.campaigns.send_test_email(
        campaign_id, {"test_emails": emails, "send_type": "html"}
    )
    # if response code is 200 or 204
    return response.ok


def schedule_campaign(camapign_web_id: str, schedule_time: datetime.datetime) -> bool:
    """
    Schedule a campaign
    """
    client = get_client()
    campaign_id = campaign_web_id_to_unique_id(camapign_web_id)

    # round to next round 15 minutes (e.g. 15, 30, 45, 60) past hour.
    current_minute = schedule_time.minute
    if current_minute % 15 != 0:
        schedule_time += datetime.timedelta(minutes=15 - (current_minute % 15))
    # delete any seconds or microseconds
    schedule_time = schedule_time.replace(second=0, microsecond=0)

    print(f"Scheduling for {schedule_time} for campaign {campaign_id}")

    str_time = schedule_time.isoformat()
    response: requests.models.Response = client.campaigns.schedule(
        campaign_id,
        {
            "schedule_time": str_time,
            "batch_delivery": False,
        },
    )
    return response.ok
