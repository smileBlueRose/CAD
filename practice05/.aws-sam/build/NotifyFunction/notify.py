import json
import logging
import os
import time
from pathlib import PurePosixPath

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

WATCHERS_TABLE = os.environ["WATCHERS_TABLE"]
PROCESSED_EVENTS_TABLE = os.environ["PROCESSED_EVENTS_TABLE"]
SENDER_EMAIL = os.environ["SENDER_EMAIL"]
PROCESSED_EVENT_TTL_SECONDS = 7 * 24 * 60 * 60

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
watchers_table = dynamodb.Table(WATCHERS_TABLE)
processed_events_table = dynamodb.Table(PROCESSED_EVENTS_TABLE)
ses = boto3.client("sesv2")


def parse_episode_key(key: str) -> tuple[str, int, int] | None:
    parts = PurePosixPath(key).parts
    if len(parts) != 3:
        return None
    title_name, season, episode_file = parts
    episode = PurePosixPath(episode_file).stem
    if not season.isdigit() or not episode.isdigit():
        return None
    return title_name, int(season), int(episode)


def is_processed(event_key: str) -> bool:
    response = processed_events_table.get_item(Key={"event_key": event_key})
    return "Item" in response


def mark_processed(event_key: str) -> None:
    try:
        processed_events_table.put_item(
            Item={
                "event_key": event_key,
                "expires_at": int(time.time()) + PROCESSED_EVENT_TTL_SECONDS,
            },
            ConditionExpression="attribute_not_exists(event_key)",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        logger.info("Event already marked as processed by another invocation: %s", event_key)


def get_watcher_emails(title_name: str) -> list[str]:
    emails = []
    query_kwargs = {"KeyConditionExpression": Key("title_name").eq(title_name)}
    while True:
        response = watchers_table.query(**query_kwargs)
        emails.extend(item["email"] for item in response["Items"])
        last_evaluated_key = response.get("LastEvaluatedKey")
        if last_evaluated_key is None:
            return emails
        query_kwargs["ExclusiveStartKey"] = last_evaluated_key


def send_notification(email: str, title_name: str, season: int, episode: int) -> None:
    ses.send_email(
        FromEmailAddress=SENDER_EMAIL,
        Destination={"ToAddresses": [email]},
        Content={
            "Simple": {
                "Subject": {"Data": f"New episode of {title_name}"},
                "Body": {
                    "Text": {
                        "Data": f"Episode {episode} of season {season} of {title_name} is out."
                    }
                },
            }
        },
    )


def process_record(record: dict) -> None:
    body = json.loads(record["body"])
    s3_object = body["detail"]["object"]
    key = s3_object["key"]
    event_key = f"{key}#{s3_object['etag']}"
    logger.info("Processing message %s with event key %s", record["messageId"], event_key)
    if is_processed(event_key):
        logger.info("Duplicate event, skipping notifications: %s", event_key)
        return
    parsed_key = parse_episode_key(key)
    if parsed_key is None:
        logger.warning("Key does not match <title>/<season>/<episode>.mp4, skipping: %s", key)
    else:
        title_name, season, episode = parsed_key
        emails = get_watcher_emails(title_name)
        logger.info(
            "Title %s season %d episode %d has %d watchers",
            title_name,
            season,
            episode,
            len(emails),
        )
        for email in emails:
            send_notification(email, title_name, season, episode)
        logger.info("Sent %d notifications for %s", len(emails), event_key)
    mark_processed(event_key)
    logger.info("Marked as processed: %s", event_key)


def handler(event: dict, context: object) -> dict:
    records = event["Records"]
    logger.info("Received batch of %d messages", len(records))
    failures = []
    for record in records:
        try:
            process_record(record)
        except Exception:
            logger.exception("Failed to process message %s", record["messageId"])
            failures.append({"itemIdentifier": record["messageId"]})
    logger.info("Batch finished with %d failures", len(failures))
    return {"batchItemFailures": failures}