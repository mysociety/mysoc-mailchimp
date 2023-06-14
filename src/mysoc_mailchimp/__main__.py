import datetime
import json
import os
from typing import Optional

import pandas as pd
import rich_click as click
from rich import box, print
from rich.console import Console
from rich.table import Table
from trogon import tui

from . import mailchimp
from .send_mailing_list import create_campaign_from_blog

console = Console()


order_by_option = click.option(
    "--order-by", "-o", default="name", help="column to order table by"
)
desc_option = click.option(
    "--desc", is_flag=True, default=False, help="flag to set to descending order"
)
json_option = click.option(
    "--json", "is_json", is_flag=True, default=False, help="output as json"
)


def df_to_table(
    pandas_dataframe: pd.DataFrame,
    rich_table: Table,
    show_index: bool = False,
    index_name: Optional[str] = None,
) -> Table:

    if show_index:
        index_name = str(index_name) if index_name else ""
        rich_table.add_column(index_name)

    for column in pandas_dataframe.columns:
        rich_table.add_column(str(column))  # type:ignore

    for index, value_list in enumerate(pandas_dataframe.values.tolist()):
        row = [str(index)] if show_index else []
        row += [str(x) for x in value_list]
        rich_table.add_row(*row)

    return rich_table


def assert_mailchimp_api_key_exists():
    """
    We should fail if the MAILCHIMP_API_KEY environment variable is not set
    """
    if not os.environ.get("MAILCHIMP_API_KEY"):
        raise click.UsageError("MAILCHIMP_API_KEY environment variable is not set")


def output_df(
    df: pd.DataFrame, order_by: str, desc: bool, is_json: bool, data_item: str
):
    """
    Print the dataframe nicely, or as a json
    """
    if df[order_by].dtype == "object":
        df["sort_lower"] = df[order_by].str.lower()  # type: ignore
    else:
        df["sort_lower"] = df[order_by]

    df = df.sort_values("sort_lower", ascending=not desc)
    df = df.drop(columns=["sort_lower"])

    if is_json:
        data = {data_item: df.to_dict(orient="records")}
        print(json.dumps(data, indent=4))
    else:
        table = df_to_table(df, Table(box=box.SIMPLE))  # type: ignore
        console.print(table)


@tui()
@click.group()
def cli():
    pass


@cli.command()
@order_by_option
@desc_option
@json_option
def lists(order_by: str, desc: bool, is_json: bool):
    """
    Get all current mySociety mailchimp mailing lists
    """
    df = mailchimp.get_lists()
    df = df.drop(columns=["id"])
    output_df(df, order_by, desc, is_json, "lists")


@cli.command()
@click.option("--list-id", "-l", default="425649", help="web id or name of list")
@click.option("--pattern", "-p", default="", help="pattern to filter segments by")
@order_by_option
@desc_option
@json_option
def segments(list_id: str, pattern: str, order_by: str, desc: bool, is_json: bool):
    """
    Show segments of newsletter
    """
    df = mailchimp.get_segments(list_id)
    # filter by pattern on name
    if pattern:
        df = df[df["name"].str.contains(pattern)]
    output_df(df, order_by, desc, is_json, "segments")


@cli.command()
@click.option("--order-by", "-o", default="web_id", help="column to order table by")
@click.option("--desc/--asc", is_flag=True, default=True, help="asc or desc")
@json_option
def campaigns(order_by: str, desc: bool, is_json: bool):
    """
    Show recent campaigns
    """
    df = mailchimp.get_recent_campaigns()
    output_df(df, order_by, desc, is_json, "campaigns")


@cli.command()
@click.option("--order-by", "-o", default="id", help="column to order table by")
@click.option("--desc/--asc", is_flag=True, default=True, help="asc or desc")
@json_option
def templates(order_by: str, desc: bool, is_json: bool):
    """
    Show current user templates
    """
    df = mailchimp.get_templates()
    output_df(df, order_by, desc, is_json, "templates")


@cli.command()
@click.option("--campaign-web-id", "-c", help="web id of campaign")
def edit_campaign(campaign_id: str):
    """
    Edit a campaign - just returns URL
    """
    url = f"https://us9.admin.mailchimp.com/campaigns/edit?id={campaign_id}"
    click.launch(url)


@cli.command(name="test_email")
@click.option("--campaign-id", "-c", help="web id of campaign")
@click.option("--email", "-e", help="email address to send test email to")
def test_email_func(campaign_id: str, email: str):
    """
    Send a test email
    """
    print(f"Sending test email to {email} from campaign {campaign_id}")
    result = mailchimp.send_test_email(campaign_id, [email])
    if result:
        print(f"[green]Test email sent to {email} [/green]")
    else:
        click.echo("[red]Test email failed[/red]")


@cli.command()
@click.option("--url", "-u", help="Url of mysociety.org blog post")
@click.option("--list-id", "--list", "-l", help="Web id or name of list")
@click.option("--segment-id", "--segment", "-s", help="Web id or name of segment")
@click.option("--template-id", "--template", "-s", help="Web id or name of template")
@click.option(
    "--from-name",
    "-f",
    help="Name to use as the from details. If blank, uses the name in the blog post",
    default="",
)
@click.option(
    "--test-email", "-e", default="", help="Email address to send test email to"
)
def convert_blog(
    url: str,
    list_id: str,
    segment_id: str,
    template_id: str,
    test_email: str,
    from_name: str,
):
    """
    Create a campaign from the latest blog post
    """

    if not list_id.isdigit():
        unique_list_id = mailchimp.list_name_to_unique_id(list_id)
    else:
        unique_list_id = mailchimp.list_web_id_to_unique_id(list_id)

    # if segment_id contains only digits
    if not segment_id.isdigit():
        unique_segment_id = mailchimp.segment_name_to_unique_id(list_id, segment_id)
    else:
        unique_segment_id = int(segment_id)

    if not template_id.isdigit():
        unique_template_id = mailchimp.template_name_to_unique_id(template_id)
    else:
        unique_template_id = int(template_id)

    unique_campaign_id, new_campaign_id = create_campaign_from_blog(
        url, unique_list_id, unique_segment_id, unique_template_id, from_name
    )

    print(
        f"[green]Created {new_campaign_id} (internal id: {unique_campaign_id})[/green]"
    )
    print(f"Url: https://us9.admin.mailchimp.com/campaigns/edit?id={new_campaign_id}")

    if test_email:
        mailchimp.send_test_email(new_campaign_id, [test_email])
        print(f"[green]Test email sent to {test_email} [/green]")


@cli.command()
@click.option("--campaign-id", "--campaign", "-c", help="web id of campaign")
def send(campaign_id: str):
    """
    Actually schedule for 10 minutes time, so there's time for second thoughts.
    """
    ten_minutes_time = datetime.datetime.now() + datetime.timedelta(minutes=10)

    # get campaign info to get recpient_count
    df = mailchimp.get_recent_campaigns().set_index("web_id")
    recipient_count = df.loc[int(campaign_id), "recipient_count"]

    print(f"This campaign will be sent to {recipient_count} people.")

    result = mailchimp.schedule_campaign(campaign_id, ten_minutes_time)

    base_url = "https://us9.admin.mailchimp.com/campaigns/edit?id="
    if result:
        print("[green]Campaign scheduled[/green]")
        print(f"Goto: {base_url}{campaign_id} to change")
    else:
        click.echo("[red]Campaign scheduling failed[/red]")


def main():
    """
    Run main CLI
    """
    assert_mailchimp_api_key_exists()
    cli()


if __name__ == "__main__":
    main()
