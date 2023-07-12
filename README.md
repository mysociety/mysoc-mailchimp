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
python -m mysoc_mailchimp wordpress-upload --url https://docs.google.com/document/d/1CYfTKBwP2PgPcV0HasjbuXuh599GbATKUMVFBnfV_gk/edit
```

## Sending blog campaign

Can be used to automate moving a mySociety blog post into mailchimp.

```
python -m mysoc_mailchimp convert-blog --url 'https://www.mysociety.org/2023/07/12/guest-post-does-watching-mps-make-them-behave-better/' \
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

## Create TWFY config

```
python -m mysoc_mailchimp --blog-url https://www.mysociety.org/2023/07/12/guest-post-does-watching-mps-make-them-behave-better/ > config.txt

```