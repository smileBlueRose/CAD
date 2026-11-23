import io
import json
import logging
import os
import urllib.parse
import uuid

import boto3
import psycopg
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ["AWS_REGION"]
DB_HOST = os.environ["DB_HOST"]
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ["DB_NAME"]
DB_SECRET_ARN = os.environ["DB_SECRET_ARN"]

ORIGINAL_PREFIX = "covers/original/"
THUMB_PREFIX = "covers/thumb/"
THUMB_SIZE = (300, 450)
MAX_ORIGINAL_BYTES = 10 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 40_000_000

s3 = boto3.client("s3", region_name=REGION)
secrets = boto3.client("secretsmanager", region_name=REGION)
_credentials: dict | None = None


class InvalidCoverError(Exception):
    pass


def get_credentials(refresh: bool = False) -> dict:
    global _credentials
    if _credentials is None or refresh:
        secret = secrets.get_secret_value(SecretId=DB_SECRET_ARN)
        _credentials = json.loads(secret["SecretString"])
    return _credentials


def connect() -> psycopg.Connection:
    for attempt in range(2):
        credentials = get_credentials(refresh=attempt == 1)
        try:
            return psycopg.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=credentials["username"],
                password=credentials["password"],
                sslmode="require",
                connect_timeout=5,
            )
        except psycopg.OperationalError:
            if attempt == 1:
                raise
    raise RuntimeError("Failed to connect to the database")


def parse_book_id(key: str) -> int:
    parts = key.removeprefix(ORIGINAL_PREFIX).split("/")
    if len(parts) != 2 or not parts[0].isdigit():
        raise InvalidCoverError(f"Unexpected key format: {key}")
    return int(parts[0])


def make_thumbnail(data: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image = image.convert("RGB")
            image.thumbnail(THUMB_SIZE)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=85, optimize=True)
            return output.getvalue()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as error:
        raise InvalidCoverError(f"Cannot process image: {error}") from error


def process_record(record: dict) -> None:
    bucket = record["s3"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
    size = record["s3"]["object"].get("size", 0)

    if not key.startswith(ORIGINAL_PREFIX):
        raise InvalidCoverError(f"Key outside of {ORIGINAL_PREFIX}: {key}")
    if size > MAX_ORIGINAL_BYTES:
        raise InvalidCoverError(f"Object too large: {size} bytes")

    book_id = parse_book_id(key)
    original = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    thumbnail = make_thumbnail(original)

    thumb_key = f"{THUMB_PREFIX}{book_id}/{uuid.uuid4().hex}.jpg"
    s3.put_object(
        Bucket=bucket,
        Key=thumb_key,
        Body=thumbnail,
        ContentType="image/jpeg",
        CacheControl="public, max-age=31536000, immutable",
    )

    with connect() as conn:
        updated = conn.execute(
            "UPDATE books SET cover_url = %s WHERE id = %s",
            (thumb_key, book_id),
        ).rowcount

    if updated == 0:
        logger.warning("Book %s not found, thumbnail %s is orphaned", book_id, thumb_key)
    else:
        logger.info("Book %s cover set to %s", book_id, thumb_key)


def lambda_handler(event, context):
    for record in event.get("Records", []):
        try:
            process_record(record)
        except InvalidCoverError as error:
            logger.warning("Skipping record: %s", error)
    return {"status": "ok"}