from psycopg import Connection

from dependencies import Pagination
from schemas import MemberIn


def create_member(conn: Connection, member: MemberIn) -> dict:
    return conn.execute(
        "INSERT INTO members (name, email) VALUES (%s, %s) RETURNING *",
        (member.name, member.email),
    ).fetchone()


def list_members(conn: Connection, page: Pagination) -> list[dict]:
    return conn.execute(
        "SELECT * FROM members ORDER BY id LIMIT %s OFFSET %s",
        (page.limit, page.offset),
    ).fetchall()


def get_member(conn: Connection, member_id: int) -> dict | None:
    return conn.execute("SELECT * FROM members WHERE id = %s", (member_id,)).fetchone()


def update_member(conn: Connection, member_id: int, member: MemberIn) -> dict | None:
    return conn.execute(
        "UPDATE members SET name = %s, email = %s WHERE id = %s RETURNING *",
        (member.name, member.email, member_id),
    ).fetchone()


def delete_member(conn: Connection, member_id: int) -> bool:
    return conn.execute("DELETE FROM members WHERE id = %s", (member_id,)).rowcount > 0