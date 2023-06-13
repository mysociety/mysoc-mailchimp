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


## Sending blog campaign

Can be used to automate moving a mySociety blog post into mailchimp.

```
python -m mysoc_mailchimp convert-blog --url https://www.mysociety.org/2023/04/27/climate-monthnotes-mar-apr-2023/ \
                                       --list "mySociety Newsletters" \
                                       --segment "Literally just Alex" \
                                       --template "mySociety auto-blog" \
                                       --from-name "mySociety \
                                       --test-email "alex@mysociety.org"
```

You can then send after review (which will be scheduled for roughly 10-20 minutes later sso it can be reversed):

```
msmc send --campaign-id [new_campaign_id]
```
