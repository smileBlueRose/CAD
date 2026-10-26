from psycopg import Connection

from dependencies import Pagination
from errors import ConflictError, NotFoundError
from schemas import LoanIn


def list_loans(
    conn: Connection,
    page: Pagination,
    member_id: int | None,
    status: str | None,
) -> list[dict]:
    return conn.execute(
        """
        SELECT * FROM loans
        WHERE (%(member_id)s::int IS NULL OR member_id = %(member_id)s)
          AND (%(status)s::text IS NULL OR status = %(status)s)
        ORDER BY id
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {
            "member_id": member_id,
            "status": status,
            "limit": page.limit,
            "offset": page.offset,
        },
    ).fetchall()


def get_loan(conn: Connection, loan_id: int) -> dict | None:
    return conn.execute("SELECT * FROM loans WHERE id = %s", (loan_id,)).fetchone()


def borrow_book(conn: Connection, loan: LoanIn) -> dict:
    with conn.transaction():
        member = conn.execute(
            "SELECT id FROM members WHERE id = %s", (loan.member_id,)
        ).fetchone()
        if member is None:
            raise NotFoundError("Member")

        book = conn.execute(
            "SELECT available_copies FROM books WHERE id = %s FOR UPDATE",
            (loan.book_id,),
        ).fetchone()
        if book is None:
            raise NotFoundError("Book")
        if book["available_copies"] == 0:
            raise ConflictError("No available copies of this book")

        existing = conn.execute(
            """
            SELECT 1 FROM loans
            WHERE member_id = %s AND book_id = %s AND status IN ('active', 'overdue')
            """,
            (loan.member_id, loan.book_id),
        ).fetchone()
        if existing is not None:
            raise ConflictError("Member already has this book")

        conn.execute(
            "UPDATE books SET available_copies = available_copies - 1 WHERE id = %s",
            (loan.book_id,),
        )
        return conn.execute(
            "INSERT INTO loans (book_id, member_id) VALUES (%s, %s) RETURNING *",
            (loan.book_id, loan.member_id),
        ).fetchone()


def return_book(conn: Connection, loan_id: int) -> dict:
    with conn.transaction():
        loan = conn.execute(
            "SELECT * FROM loans WHERE id = %s FOR UPDATE", (loan_id,)
        ).fetchone()
        if loan is None:
            raise NotFoundError("Loan")
        if loan["status"] == "returned":
            raise ConflictError("Loan is already returned")

        conn.execute(
            "UPDATE books SET available_copies = available_copies + 1 WHERE id = %s",
            (loan["book_id"],),
        )
        return conn.execute(
            """
            UPDATE loans SET status = 'returned', returned_at = now()
            WHERE id = %s
            RETURNING *
            """,
            (loan_id,),
        ).fetchone()