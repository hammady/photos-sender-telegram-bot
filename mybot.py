import os
import asyncio
import random
from csv import DictReader
import telegram
import dotenv
import boto3
import click

class MyBot(telegram.Bot):
    def __init__(
            self, token: str, chat_id: str, s3_bucket: str, s3_prefix: str = "",
            caption_signature: str = ""):
        super().__init__(token=token)
        self._chat_id = chat_id
        self._s3_bucket = s3_bucket
        self._s3_prefix = s3_prefix
        self._s3_client = boto3.client('s3')
        self._caption_signature = caption_signature
    
    def _generate_presigned_url(self, object_name, expiration=60):
        return self._s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self._s3_bucket, 'Key': object_name},
            ExpiresIn=expiration
        )

    def _get_photo_url(self, page_id: int):
        # Generate images from a single PDF using poppler command: pdfimages -png mybook.pdf page
        object_name = f"{self._s3_prefix}page-{page_id:03d}.png"
        return self._generate_presigned_url(object_name)

    def _get_signed_caption(self, caption: str):
        if caption is None:
            return self._caption_signature
        else:
            return f"{caption}\n\n{self._caption_signature}"
    
    async def send_page(self, page_id: int, caption: str = None):
        return await self.send_photo(
            photo=self._get_photo_url(page_id),
            chat_id=self._chat_id,
            caption=self._get_signed_caption(caption)
        )

    async def send_pages(self, from_page: int, to_page: int, caption: str = None):        
        return await self.sendMediaGroup(
            media=[
                telegram.InputMediaPhoto(media=self._get_photo_url(page_id))
                for page_id in range(from_page, to_page + 1)
            ],
            chat_id=self._chat_id,
            caption=self._get_signed_caption(caption)
        )
    
    def _download_pages_file(self):
        local_file = '/tmp/pages.csv'
        self._s3_client.download_file(
            self._s3_bucket,
            f"{self._s3_prefix}pages.csv",
            local_file
        )
        return local_file

    def _read_pages_file(self, file_path):
        with open(file_path, 'rb') as file_path:
            csv_data = file_path.readlines()
            csv_data = [line.decode('utf-8-sig') for line in csv_data] # utf-8-sig removes BOM
            csv_reader = DictReader(csv_data)
            return [
                {
                    'caption': row['caption'],
                    'from_page': int(row['from']),
                    'to_page': int(row['to'] or row['from']),
                    'total_pages': int(row['to'] or row['from']) - int(row['from']) + 1,
                }
                for row in csv_reader
            ]

    def get_random_post(self, min_pages: int = 1, max_pages: int = 20):
        csv_file = self._download_pages_file()
        posts = self._read_pages_file(csv_file)
        posts = [
            post for post in posts
            if post['total_pages'] >= min_pages and post['total_pages'] <= max_pages
        ]
        if len(posts) == 0:
            raise Exception("No posts found")
        return random.choice(posts)

def run(min_pages: int, max_pages: int):
    if min_pages < 1:
        raise ValueError("min_pages should be greater than 0")
    if max_pages < min_pages:
        raise ValueError("max_pages should be greater than or equal to min_pages")
    dotenv.load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    s3_bucket = os.environ.get("AWS_S3_BUCKET_NAME")
    s3_prefix = os.environ.get("AWS_S3_PREFIX")
    caption_signature = os.environ.get("CAPTION_SIGNATURE")
    bot = MyBot(
        token=token, chat_id=chat_id, s3_bucket=s3_bucket, s3_prefix=s3_prefix,
        caption_signature=caption_signature)
    asyncio.run(bot_run(bot=bot, min_pages=min_pages, max_pages=max_pages))

async def bot_run(bot: MyBot, min_pages: int, max_pages: int):
    random_post = bot.get_random_post(min_pages=min_pages, max_pages=max_pages)
    caption = random_post['caption']
    from_page, to_page = random_post['from_page'], random_post['to_page']
    total_pages = to_page - from_page + 1
    async with bot:
        if total_pages == 1:
            await bot.send_page(page_id=from_page, caption=caption)
        else:
            await bot.send_pages(from_page=from_page, to_page=to_page, caption=caption)

def lambda_run(event, _):
    min_pages = int(event.get('min_pages', 1))
    max_pages = int(event.get('max_pages', 20))
    run(min_pages=min_pages, max_pages=max_pages)

@click.command()
@click.option('--min_pages', help='Minimum number of pages per post to send', default=1)
@click.option('--max_pages', help='Maximum number of pages per post to send', default=20)
def cli_run(min_pages: int, max_pages: int):
    run(min_pages=min_pages, max_pages=max_pages)

if __name__ == '__main__':
    cli_run()
