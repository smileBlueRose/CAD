from fastapi import APIRouter, Depends, Query, Response
from psycopg import Connection

from db import get_connection
from dependencies import Pagination, get_pagination
from errors import NotFoundError
from repositories import books as repository
from schemas import Book, BookIn

router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=Book, status_code=201)
def create_book(book: BookIn, conn: Connection = Depends(get_connection)):
    return repository.create_book(conn, book)


@router.get("", response_model=list[Book])
def list_books(
    author_id: int | None = Query(default=None, gt=0),
    page: Pagination = Depends(get_pagination),
    conn: Connection = Depends(get_connection),
):
    return repository.list_books(conn, page, author_id)


@router.get("/{book_id}", response_model=Book)
def get_book(book_id: int, conn: Connection = Depends(get_connection)):
    row = repository.get_book(conn, book_id)
    if row is None:
        raise NotFoundError("Book")
    return row


@router.put("/{book_id}", response_model=Book)
def update_book(book_id: int, book: BookIn, conn: Connection = Depends(get_connection)):
    row = repository.update_book(conn, book_id, book)
    if row is None:
        raise NotFoundError("Book")
    return row


@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: int, conn: Connection = Depends(get_connection)):
    if not repository.delete_book(conn, book_id):
        raise NotFoundError("Book")
    return Response(status_code=204)