import os
import asyncio
import random
from csv import DictReader
import telegram
import dotenv
import boto3


class MyBot(telegram.Bot):
    def __init__(self, token: str, chat_id: str, s3_bucket: str, s3_prefix: str = ""):
        super().__init__(token=token)
        self._chat_id = chat_id
        self._s3_bucket = s3_bucket
        self._s3_prefix = s3_prefix
        self._s3_client = boto3.client('s3')
    
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
    
    async def send_page(self, page_id: int, caption: str = None):
        photo = self._get_photo_url(page_id)
        return await self.send_photo(chat_id=self._chat_id, photo=photo, caption=caption)
    
    def _download_pages_file(self):
        local_file = 'pages.csv'
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
                }
                for row in csv_reader
            ]

    def get_random_post(self, min_pages: int = 1, max_pages: int = 20):
        csv_file = self._download_pages_file()
        posts = self._read_pages_file(csv_file)
        return random.choice(posts)
    
async def main():
    dotenv.load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    s3_bucket = os.environ.get("AWS_S3_BUCKET_NAME")
    s3_prefix = os.environ.get("AWS_S3_PREFIX")
    bot = MyBot(token=token, chat_id=chat_id, s3_bucket=s3_bucket, s3_prefix=s3_prefix)

    random_post = bot.get_random_post()
    from_page, to_page = random_post['from_page'], random_post['to_page']
    async with bot:
        for counter, page_id in enumerate(range(from_page, to_page + 1)):
            total_pages = to_page - from_page + 1
            caption = str(random_post['caption'])
            if total_pages > 1:
                caption = f"{caption} ({counter + 1}/{total_pages})"
            await bot.send_page(page_id=page_id, caption=caption)


if __name__ == '__main__':
    asyncio.run(main())
