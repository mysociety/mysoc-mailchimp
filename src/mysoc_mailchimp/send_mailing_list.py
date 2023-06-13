from rich import print

from mysoc_mailchimp.mailchimp import get_client
from mysoc_mailchimp.scraping import get_details_from_blog

# Create campaign from template


def create_campaign_from_blog(
    url: str, list_unique_id: str, segment_id: int, template_id: int
) -> tuple[str, str]:
    """
    Given a mysociety blog url, create a campaign in mailchimp that uses a set template.
    Returns the 'web id' of the campaign, which is the id used in the mailchimp url.
    """

    blog = get_details_from_blog(url)

    campaign_type = "regular"

    settings = {
        "subject_line": blog.title,
        "title": "[auto]" + blog.title,
        "from_name": blog.author,
        "reply_to": "newsletters@mysociety.org",
        "template_id": template_id,
    }

    tracking = {"opens": False, "html_clicks": False, "text_clicks": False}

    recipients = {
        "list_id": list_unique_id,
        "segment_opts": {"saved_segment_id": int(segment_id)},
    }

    client = get_client()

    # first time around we give it a template id so it sets the content

    print("Creating campaign")
    print(settings)
    print(tracking)
    print(recipients)

    response = client.campaigns.create(
        {
            "type": campaign_type,
            "settings": settings,
            "tracking": tracking,
            "recipients": recipients,
        }
    )
    unique_id: str = response["id"]
    # grab the content
    response = client.campaigns.get_content(unique_id)
    known_content: str = response["html"]

    # delete the campaign
    client.campaigns.remove(unique_id)

    # remove template_id from settings
    settings.pop("template_id")

    # create the campaign again, this time without the template_id

    # a *different* horrible way of doing this is described here
    # https://stackoverflow.com/questions/29366766/mailchimp-api-not-replacing-mcedit-content-sections-using-ruby-library
    # my approach has the advantage of keeping the original template drag-and-dropable

    response = client.campaigns.create(
        {
            "type": campaign_type,
            "settings": settings,
            "tracking": tracking,
            "recipients": recipients,
        }
    )
    unique_id = response["id"]
    web_id = str(response["web_id"])  # type: ignore
    
    html = known_content

    # replace placeholders with actual content
    html = html.replace("[content]", blog.content)
    html = html.replace("[main title]", blog.title)
    html = html.replace("http://**blog-url**", url)
    html = html.replace(
        "https://mcusercontent.com/53d0d2026dea615ed488a8834/images/3cb63c42-5b40-2e48-6955-d2fbf9ed99d6.png",
        blog.image_url,
    )

    # send content back
    response = client.campaigns.set_content(
        unique_id, {"html": html, "content_type": "html"}
    )
    return unique_id, web_id
