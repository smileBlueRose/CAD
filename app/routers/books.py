from fastapi import APIRouter, Depends, HTTPException, Query, Response
from psycopg import Connection

import repository
from db import get_connection
from schemas import Book, BookIn

router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=Book, status_code=201)
def create_book(book: BookIn, conn: Connection = Depends(get_connection)):
    return repository.create_book(conn, book)


@router.get("", response_model=list[Book])
def list_books(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: Connection = Depends(get_connection),
):
    return repository.list_books(conn, limit, offset)


@router.get("/{book_id}", response_model=Book)
def get_book(book_id: int, conn: Connection = Depends(get_connection)):
    row = repository.get_book(conn, book_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return row


@router.put("/{book_id}", response_model=Book)
def update_book(book_id: int, book: BookIn, conn: Connection = Depends(get_connection)):
    row = repository.update_book(conn, book_id, book)
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return row


@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: int, conn: Connection = Depends(get_connection)):
    if not repository.delete_book(conn, book_id):
        raise HTTPException(status_code=404, detail="Book not found")
    return Response(status_code=204)
