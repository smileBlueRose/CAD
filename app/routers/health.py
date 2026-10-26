from fastapi import APIRouter, Depends
from psycopg import Connection

from config import settings
from db import get_connection

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    return {"status": "ok"}


@router.get("/db")
def health_db(conn: Connection = Depends(get_connection)):
    row = conn.execute(
        "SELECT version() AS version, inet_server_addr() AS server_ip"
    ).fetchone()
    return {"status": "ok", "db_host": settings.db_host, **row}
