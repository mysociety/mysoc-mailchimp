import datetime
import hashlib
import os
from functools import lru_cache
from typing import Any, NamedTuple, NewType, Optional

import mailchimp_marketing
import numpy as np
import pandas as pd
import requests

InternalListID = NewType("InternalListID", str)


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


def get_recent_email_count(list_web_id: str, segment_id: str, days: int = 7) -> int:
    """
    Get the emails and sign up date for a list and segment
    Get the count of the number in the last [x] days
    """
    client = get_client()

    try:
        list_id = int(list_web_id)
        is_web_id = True
    except ValueError:
        is_web_id = False
    if is_web_id:
        list_id = list_web_id_to_unique_id(list_web_id)
    else:
        list_id = list_name_to_unique_id(list_web_id)

    dfs = []
    # paginate until we have all emails
    offset = 0
    while True:
        response: dict[str, Any] = client.lists.get_segment_members_list(
            list_id,
            segment_id,
            count=1000,
            offset=offset,
        )
        df = pd.DataFrame(response["members"])
        dfs.append(df)
        if len(df) < 1000:
            break
        offset += 1000
    df = pd.concat(dfs)  # type: ignore

    # create new timestamp_joined from timestamp_signup and timestamp_opt if timestamp_signup is empty
    df["timestamp_joined"] = np.where(
        df["timestamp_signup"].isna() | df["timestamp_signup"].isin([None, ""]),
        df["timestamp_opt"],  # type: ignore
        df["timestamp_signup"],  # type: ignore
    )
    df["timestamp_joined"] = pd.to_datetime(df["timestamp_joined"]).dt.date
    # get the cutoff date as a date object
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    mask: pd.Series[bool] = df["timestamp_joined"].apply(
        lambda x: x.isoformat() > cutoff  # type: ignore
    )
    df = df[mask]
    return len(df)


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
    df = pd.DataFrame(response["segments"])  # type: ignore
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
    df["subject_line"] = df["settings"].apply(lambda x: x.get("subject_line", ""))  # type: ignore
    df["title"] = df["settings"].apply(lambda x: x["title"])  # type: ignore
    df["recipient_count"] = df["recipients"].apply(lambda x: x["recipient_count"])  # type: ignore
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


def list_name_to_unique_id(name: str) -> InternalListID:
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


def get_user_hash(email: str):
    # Convert the email to lowercase and get its MD5 hash
    return hashlib.md5(email.lower().encode("utf-8")).hexdigest()


class CategoryInfo(NamedTuple):
    group_id: str
    interest_name_to_id: dict[str, str]


def get_interest_group(
    list_id: InternalListID, interest_group_label: str
) -> CategoryInfo:
    client = get_client()
    options = client.lists.get_list_interest_categories(list_id)["categories"]
    options = [option for option in options if option["title"] == interest_group_label][
        0
    ]
    category_id = options["id"]
    # get the interests associated with the category
    interests = client.lists.list_interest_category_interests(
        list_id,
        category_id,  # type: ignore
    )["interests"]
    # make lookup from name to id
    interests_by_name = {interest["name"]: interest["id"] for interest in interests}
    return CategoryInfo(category_id, interests_by_name)


def get_member_from_email(
    internal_list_id: InternalListID, email: str
) -> dict[str, Any]:
    # Get the member from the list
    client = get_client()
    user_hash = get_user_hash(email)
    return client.lists.get_list_member(internal_list_id, user_hash)


def get_donor_tags(internal_list_id: InternalListID, email: str) -> list[str]:
    # Get the tags for the user
    client = get_client()
    user_hash = get_user_hash(email)
    details = client.lists.get_list_member_tags(internal_list_id, user_hash)
    return [x["name"] for x in details["tags"]]


def set_donor_tags(
    internal_list_id: InternalListID,
    email: str,
    tags_to_add: list[str] = [],
    tags_to_remove: list[str] = [],
    disable_automation: bool = False,
):
    client = get_client()
    # Set the donor status on the user
    user_hash = get_user_hash(email)

    existing_tags = get_donor_tags(internal_list_id, email)

    tags_to_add = [x for x in tags_to_add if x not in existing_tags]

    to_add_dict = [{"name": tag, "status": "active"} for tag in tags_to_add]
    to_remove_dict = [{"name": tag, "status": "inactive"} for tag in tags_to_remove]

    details = {
        "tags": to_add_dict + to_remove_dict,
        "is_syncing": disable_automation,
    }
    client.lists.update_list_member_tags(internal_list_id, user_hash, details)


def get_notes(
    internal_list_id: InternalListID,
    email: str,
) -> list[str]:
    client = get_client()
    user_hash = get_user_hash(email)
    data = client.lists.get_list_member_notes(internal_list_id, user_hash, count=1000)
    return [x["note"] for x in data["notes"]]


def add_user_notes(
    internal_list_id: InternalListID,
    email: str,
    notes: list[str],
    check_existing: bool = True,
):
    client = get_client()
    user_hash = get_user_hash(email)

    if check_existing:
        existing_notes = get_notes(internal_list_id, email)
        notes_to_add = [note for note in notes if note not in existing_notes]
    else:
        notes_to_add = notes

    for note in notes_to_add:
        client.lists.create_list_member_note(
            internal_list_id, user_hash, {"note": note}
        )


def set_user_metadata(
    internal_list_id: InternalListID,
    email: str,
    merge_data: dict[str, Any] = {},
    tags: list[str] = [],
    interests: list[str] = [],
    notes: list[str] = [],
):
    """
    A general purpose function to set metadata for a user
    """
    client = get_client()
    user_hash = get_user_hash(email)

    avaliable_list_ids = get_interest_group(
        internal_list_id, "What are you interested in? Select all that apply"
    )

    interests_to_add = [
        avaliable_list_ids.interest_name_to_id[interest] for interest in interests
    ]

    details = {
        "status_if_new": "subscribed",
        "merge_fields": merge_data,
        "interests": {x: True for x in interests_to_add},
    }

    client.lists.update_list_member(internal_list_id, user_hash, details)

    set_donor_tags(internal_list_id, email, tags_to_add=tags)
    add_user_notes(internal_list_id, email, notes=notes)


def get_all_members(
    internal_list_id: InternalListID, cut_off: Optional[int] = None
) -> list[dict[str, Any]]:
    client = get_client()
    # Get all the members of the list
    member_count = 1
    running_members: list[dict[str, Any]] = []
    size = 1000 if not cut_off else cut_off
    offset = 0
    while member_count > 0:
        reply = client.lists.get_list_members_info(
            internal_list_id, count=size, offset=0
        )
        running_members.extend(reply["members"])  # type: ignore
        member_count = len(reply["members"])  # type: ignore
        offset += size
        if cut_off and len(running_members) > cut_off:
            break
    return running_members
