import logging
import os

import boto3
import uvicorn
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, EmailStr

WATCHERS_TABLE = os.environ["WATCHERS_TABLE"]
PORT = int(os.environ.get("PORT", "8000"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dynamodb = boto3.resource("dynamodb")
watchers_table = dynamodb.Table(WATCHERS_TABLE)
ses = boto3.client("sesv2")

app = FastAPI()


class SubscribeRequest(BaseModel):
    email: EmailStr


def normalize_email(email: str) -> str:
    return email.strip().lower()


def ensure_email_identity(email: str) -> str:
    try:
        response = ses.get_email_identity(EmailIdentity=email)
    except ClientError as error:
        if error.response["Error"]["Code"] != "NotFoundException":
            raise
    else:
        return "verified" if response["VerifiedForSendingStatus"] else "pending"
    try:
        ses.create_email_identity(EmailIdentity=email)
    except ClientError as error:
        if error.response["Error"]["Code"] != "AlreadyExistsException":
            raise
        return "pending"
    logger.info("Verification email sent to %s", email)
    return "verification_sent"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/titles/{title_name}/watchers", status_code=status.HTTP_201_CREATED)
def subscribe(title_name: str, request: SubscribeRequest) -> dict:
    email = normalize_email(request.email)
    verification_status = ensure_email_identity(email)
    watchers_table.put_item(Item={"title_name": title_name, "email": email})
    logger.info("Subscribed %s to %s with status %s", email, title_name, verification_status)
    return {
        "title_name": title_name,
        "email": email,
        "verification_status": verification_status,
    }


@app.get("/titles/{title_name}/watchers")
def list_watchers(title_name: str) -> dict:
    emails = []
    query_kwargs = {"KeyConditionExpression": Key("title_name").eq(title_name)}
    while True:
        response = watchers_table.query(**query_kwargs)
        emails.extend(item["email"] for item in response["Items"])
        last_evaluated_key = response.get("LastEvaluatedKey")
        if last_evaluated_key is None:
            return {"title_name": title_name, "watchers": emails}
        query_kwargs["ExclusiveStartKey"] = last_evaluated_key


@app.delete(
    "/titles/{title_name}/watchers/{email}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unsubscribe(title_name: str, email: str) -> Response:
    email = normalize_email(email)
    try:
        watchers_table.delete_item(
            Key={"title_name": title_name, "email": email},
            ConditionExpression="attribute_exists(email)",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        raise HTTPException(status_code=404, detail="Subscription not found") from error
    logger.info("Unsubscribed %s from %s", email, title_name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)