# photos-sender-telegram-bot

A Telegram Bot to send random photos from an S3 bucket.

## Requirements

- Serverless Framework
- Python 3.11

## Setup

Fill in the `.env` file with the following variables:

```bash
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
AWS_S3_PREFIX=
CAPTION_SIGNATURE=
```

## Deploy

```bash
sls deploy --aws-profile <profile_name> --stage foobar
```

This will create all necessary resources in AWS and output the name of the
created S3 bucket. You must upload the photos to this bucket under the prefix
specified in the `.env` file.
Photo names must have the pattern page-001.png, page-002.png, etc.
A post consists of at least one photo and a caption.
To define posts, upload a new file called `pages.csv` to the bucket under the
same prefix with the following format:

```csv
caption,from,to
Caption 1,1,3
Caption 2,4,
```

This will create two posts. The first one will have the caption "Caption 1" and
will include photos from page-001.png to page-003.png. The second one will have
the caption "Caption 2" and will include one photo with page-004.png.

Caption signatures are optional and can be used to add a signature to the end of
each caption. The signature is defined in the `.env` file.

To generate a token for the bot and identify the chat id, check the
official docs for [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Introduction-to-the-API).