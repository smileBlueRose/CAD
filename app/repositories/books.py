from psycopg import Connection

from dependencies import Pagination
from schemas import BookIn


def create_book(conn: Connection, book: BookIn) -> dict:
    return conn.execute(
        """
        INSERT INTO books (title, author_id, year, total_copies, available_copies)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
        """,
        (book.title, book.author_id, book.year, book.total_copies, book.total_copies),
    ).fetchone()


def list_books(conn: Connection, page: Pagination, author_id: int | None) -> list[dict]:
    return conn.execute(
        """
        SELECT * FROM books
        WHERE (%(author_id)s::int IS NULL OR author_id = %(author_id)s)
        ORDER BY id
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {"author_id": author_id, "limit": page.limit, "offset": page.offset},
    ).fetchall()


def get_book(conn: Connection, book_id: int) -> dict | None:
    return conn.execute("SELECT * FROM books WHERE id = %s", (book_id,)).fetchone()


def update_book(conn: Connection, book_id: int, book: BookIn) -> dict | None:
    return conn.execute(
        """
        UPDATE books
        SET title = %(title)s,
            author_id = %(author_id)s,
            year = %(year)s,
            available_copies = available_copies + (%(total_copies)s - total_copies),
            total_copies = %(total_copies)s
        WHERE id = %(id)s
        RETURNING *
        """,
        {
            "title": book.title,
            "author_id": book.author_id,
            "year": book.year,
            "total_copies": book.total_copies,
            "id": book_id,
        },
    ).fetchone()


def delete_book(conn: Connection, book_id: int) -> bool:
    return conn.execute("DELETE FROM books WHERE id = %s", (book_id,)).rowcount > 0