# mysoc-mailchimp

CLI for common mailchimp functions.


Requires `MAILCHIMP_API_KEY` to be set as an environmental variable.


## To run

Install the package:

```
pip install git+https://github.com/mysociety/mysoc-mailchimp
```

To see options:
```
python -m mysoc_mailchimp --help
```
## Uploading wordpress blog

```
python -m mysoc_mailchimp wordpress-upload --url https://docs.google.com/document/d/19mOtaP1dXKjpRTJsRAPnLBhcw7c3Q0gB_Ig1uB9W624/edit?tab=t.0 --config blank
```

## Sending blog campaign

Can be used to automate moving a mySociety blog post into mailchimp.

```
python -m mysoc_mailchimp convert-blog --url 'https://www.mysociety.org/2025/03/27/devolved-parliamentary-registers-of-interest-now-on-theyworkforyou/' \
                                       --list "mySociety Newsletters" \
                                       --segment "Interest: Democracy" \
                                       --template "mySociety auto-blog" \
                                       --from-name "mySociety" \
                                       --test-email "alex@mysociety.org" \
                                       --add-campaign
```

You can then send after review (which will be scheduled for roughly 10-20 minutes later so it can be reversed):

```
msmc send --campaign-id [new_campaign_id]
```

## Using the GitHub Action workflow

You can also use the "Move Blog to Mailchimp" GitHub Action workflow to create a campaign without having to set up the local environment:

1. Go to the "Actions" tab in your GitHub repository
2. Select the "Move Blog to Mailchimp" workflow
3. Click "Run workflow" 
4. Fill in the form:
   - Blog post URL: The URL of the blog post to convert (required)
   - Mailchimp list name: Name of the Mailchimp list (default: "mySociety Newsletters")
   - Segment name: Name of the list segment (default: "Interest: Democracy")
   - Template name: Name of the template to use (default: "mySociety auto-blog")
   - From name: Name to show in the "From" field (default: "mySociety", leave empty to use blog author)
   - Test email: Email address to send the preview to (required)
   - Add UTM campaign parameters: Whether to add tracking parameters to the URL (default: true)
5. Click "Run workflow" to execute the action

The workflow will:
- Create a Mailchimp campaign based on the blog post
- Send a test email to the specified address
- Output the campaign ID and instructions for sending after review

This gives you the same functionality as the CLI command but through the GitHub interface, making it easier to use for team members without local development setups.

## Create TWFY config

```
python -m mysoc_mailchimp twfy-config --blog-url https://www.mysociety.org/2024/10/02/and-were-off-our-whofundsthem-project-has-restarted/ > config.txt

```