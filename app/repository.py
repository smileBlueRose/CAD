from psycopg import Connection

from schemas import BookIn


def create_book(conn: Connection, book: BookIn) -> dict:
    return conn.execute(
        "INSERT INTO books (title, author, year) VALUES (%s, %s, %s) RETURNING *",
        (book.title, book.author, book.year),
    ).fetchone()


def list_books(conn: Connection, limit: int, offset: int) -> list[dict]:
    return conn.execute(
        "SELECT * FROM books ORDER BY id LIMIT %s OFFSET %s",
        (limit, offset),
    ).fetchall()


def get_book(conn: Connection, book_id: int) -> dict | None:
    return conn.execute("SELECT * FROM books WHERE id = %s", (book_id,)).fetchone()


def update_book(conn: Connection, book_id: int, book: BookIn) -> dict | None:
    return conn.execute(
        "UPDATE books SET title = %s, author = %s, year = %s WHERE id = %s RETURNING *",
        (book.title, book.author, book.year, book_id),
    ).fetchone()


def delete_book(conn: Connection, book_id: int) -> bool:
    return conn.execute("DELETE FROM books WHERE id = %s", (book_id,)).rowcount > 0
