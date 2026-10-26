import json
import os
import uuid

import boto3
from botocore.config import Config

REGION = os.environ["AWS_REGION"]
BUCKET_NAME = os.environ["BUCKET_NAME"]
URL_TTL_SECONDS = 300
ALLOWED_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

s3 = boto3.client(
    "s3",
    region_name=REGION,
    endpoint_url=f"https://s3.{REGION}.amazonaws.com",
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)


def response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    try:
        book_id = int(event["pathParameters"]["id"])
    except (KeyError, TypeError, ValueError):
        return response(400, {"detail": "Invalid book id"})
    if book_id <= 0:
        return response(400, {"detail": "Invalid book id"})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"detail": "Invalid JSON body"})

    content_type = body.get("content_type")
    extension = ALLOWED_TYPES.get(content_type)
    if extension is None:
        return response(400, {"detail": f"content_type must be one of {list(ALLOWED_TYPES)}"})

    key = f"covers/original/{book_id}/{uuid.uuid4().hex}.{extension}"
    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": BUCKET_NAME, "Key": key, "ContentType": content_type},
        ExpiresIn=URL_TTL_SECONDS,
    )
    return response(200, {"url": url, "key": key, "expires_in": URL_TTL_SECONDS})