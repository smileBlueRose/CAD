from psycopg import Connection

from dependencies import Pagination
from schemas import AuthorIn


def create_author(conn: Connection, author: AuthorIn) -> dict:
    return conn.execute(
        "INSERT INTO authors (name, country) VALUES (%s, %s) RETURNING *",
        (author.name, author.country),
    ).fetchone()


def list_authors(conn: Connection, page: Pagination) -> list[dict]:
    return conn.execute(
        "SELECT * FROM authors ORDER BY id LIMIT %s OFFSET %s",
        (page.limit, page.offset),
    ).fetchall()


def get_author(conn: Connection, author_id: int) -> dict | None:
    return conn.execute("SELECT * FROM authors WHERE id = %s", (author_id,)).fetchone()


def update_author(conn: Connection, author_id: int, author: AuthorIn) -> dict | None:
    return conn.execute(
        "UPDATE authors SET name = %s, country = %s WHERE id = %s RETURNING *",
        (author.name, author.country, author_id),
    ).fetchone()


def delete_author(conn: Connection, author_id: int) -> bool:
    return conn.execute("DELETE FROM authors WHERE id = %s", (author_id,)).rowcount > 0