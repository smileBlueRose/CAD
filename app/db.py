import json
from collections.abc import Iterator
from functools import lru_cache

import boto3
import psycopg
from loguru import logger
from psycopg.rows import dict_row

from config import settings

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS authors
    (
        id      SERIAL PRIMARY KEY,
        name    TEXT NOT NULL UNIQUE,
        country TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS books
    (
        id               SERIAL PRIMARY KEY,
        title            TEXT    NOT NULL,
        author_id        INTEGER NOT NULL REFERENCES authors (id) ON DELETE RESTRICT,
        year             INTEGER CHECK (year BETWEEN 0 AND 2100),
        total_copies     INTEGER NOT NULL DEFAULT 1 CHECK (total_copies >= 0),
        available_copies INTEGER NOT NULL DEFAULT 1
            CHECK (available_copies >= 0 AND available_copies <= total_copies),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        cover_url TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS members
    (
        id    SERIAL PRIMARY KEY,
        name  TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS loans
    (
        id        SERIAL PRIMARY KEY,
        book_id   INTEGER NOT NULL REFERENCES books (id) ON DELETE RESTRICT,
        member_id INTEGER NOT NULL REFERENCES members (id) ON DELETE RESTRICT,
        status    TEXT    NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'returned', 'overdue')),
        borrowed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        due_at TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '14 days',
        returned_at TIMESTAMPTZ
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_books_author_id ON books (author_id)",
    "CREATE INDEX IF NOT EXISTS idx_loans_member_id ON loans (member_id)",
    "CREATE INDEX IF NOT EXISTS idx_loans_book_id ON loans (book_id)",
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_loans_active_member_book
        ON loans (member_id, book_id) WHERE status = 'active'
    """,
]


@lru_cache
def get_db_credentials() -> dict:
    client = boto3.client("secretsmanager", region_name=settings.aws_region)
    secret = client.get_secret_value(SecretId=settings.db_secret_arn)
    return json.loads(secret["SecretString"])


def connect() -> psycopg.Connection:
    logger.info("Connecting to the database")
    for attempt in range(2):
        credentials = get_db_credentials()
        try:
            return psycopg.connect(
                host=settings.db_host,
                port=settings.db_port,
                dbname=settings.db_name,
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
    raise RuntimeError("Failed to connect to the database")


def get_connection() -> Iterator[psycopg.Connection]:
    with connect() as conn:
        yield conn


def init_db() -> None:
    with connect() as conn:
        for statement in SCHEMA:
            conn.execute(statement)
