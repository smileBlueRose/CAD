import json
import os
import socket
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import lru_cache

import boto3
import httpx
import psycopg
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from psycopg.rows import dict_row
from pydantic import BaseModel

DB_HOST = os.environ["DB_HOST"]
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ["DB_NAME"]
DB_SECRET_ARN = os.environ["DB_SECRET_ARN"]
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

METADATA_URL = "http://169.254.169.254/latest"
METADATA_FIELDS = {
    "instance_id": "instance-id",
    "instance_type": "instance-type",
    "availability_zone": "placement/availability-zone",
    "private_ip": "local-ipv4",
}


class BookIn(BaseModel):
    title: str
    author: str
    year: int | None = None


class Book(BookIn):
    id: int
    created_at: datetime


@lru_cache
def get_db_credentials() -> dict:
    client = boto3.client("secretsmanager", region_name=AWS_REGION)
    secret = client.get_secret_value(SecretId=DB_SECRET_ARN)
    return json.loads(secret["SecretString"])


def connect() -> psycopg.Connection:
    for attempt in range(2):
        credentials = get_db_credentials()
        try:
            return psycopg.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=credentials["username"],
                password=credentials["password"],
                sslmode="require",
                connect_timeout=5,
                row_factory=dict_row,
            )
        except psycopg.OperationalError:
            if attempt == 1:
                raise
            get_db_credentials.cache_clear()


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Cloud Practice App", lifespan=lifespan)


@lru_cache
def get_instance_metadata() -> dict:
    try:
        token = httpx.put(
            f"{METADATA_URL}/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=1,
        ).text
        headers = {"X-aws-ec2-metadata-token": token}
        return {
            key: httpx.get(f"{METADATA_URL}/meta-data/{path}", headers=headers, timeout=1).text
            for key, path in METADATA_FIELDS.items()
        }
    except httpx.HTTPError:
        return {key: "unknown" for key in METADATA_FIELDS}


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.get("/")
def root():
    return {
        "message": "Hello from Cloud Practice App",
        "hostname": socket.gethostname(),
        "instance": get_instance_metadata(),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    with connect() as conn:
        row = conn.execute("SELECT version() AS version, inet_server_addr() AS server_ip").fetchone()
    return {"status": "ok", "db_host": DB_HOST, **row}


@app.get("/client")
def client_info(request: Request):
    return {
        "ip": get_client_ip(request),
        "port": request.client.port if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "accept_language": request.headers.get("accept-language"),
        "referer": request.headers.get("referer"),
        "protocol": request.headers.get("x-forwarded-proto", request.url.scheme),
        "method": request.method,
        "url": str(request.url),
        "query_params": dict(request.query_params),
        "headers": dict(request.headers),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "served_by": get_instance_metadata()["instance_id"],
    }


@app.post("/books", response_model=Book, status_code=201)
def create_book(book: BookIn):
    with connect() as conn:
        return conn.execute(
            "INSERT INTO books (title, author, year) VALUES (%s, %s, %s) RETURNING *",
            (book.title, book.author, book.year),
        ).fetchone()


@app.get("/books", response_model=list[Book])
def list_books():
    with connect() as conn:
        return conn.execute("SELECT * FROM books ORDER BY id").fetchall()


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int):
    with connect() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = %s", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return row


@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, book: BookIn):
    with connect() as conn:
        row = conn.execute(
            "UPDATE books SET title = %s, author = %s, year = %s WHERE id = %s RETURNING *",
            (book.title, book.author, book.year, book_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return row


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    with connect() as conn:
        deleted = conn.execute("DELETE FROM books WHERE id = %s", (book_id,)).rowcount
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Book not found")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)