# mysoc-mailchimp

CLI for common mailchimp functions.


Requires `MAILCHIMP_API_KEY` to be set as an environmental variable.

See options with `msmc --help`.


## Sending blog campaign

Can be used to automate moving a mySociety blog post into mailchimp.

```
msmc convert-blog --url https://www.mysociety.org/2023/04/27/climate-monthnotes-mar-apr-2023/ \
                  --list "mySociety Newsletters"
                  --segment "Literally just Alex"
                  --template "mySociety auto-blog"
                  --test-email "alex@mysociety.org"
```

You can then send after review (which will be scheduled for roughly 10-20 minutes later sso it can be reversed):

```
msmc send --campaign-id [new_campaign_id]
```
