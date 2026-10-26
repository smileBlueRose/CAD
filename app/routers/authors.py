from fastapi import APIRouter, Depends, Response
from psycopg import Connection

from db import get_connection
from dependencies import Pagination, get_pagination
from errors import NotFoundError
from repositories import authors as repository
from schemas import Author, AuthorIn

router = APIRouter(prefix="/authors", tags=["authors"])


@router.post("", response_model=Author, status_code=201)
def create_author(author: AuthorIn, conn: Connection = Depends(get_connection)):
    return repository.create_author(conn, author)


@router.get("", response_model=list[Author])
def list_authors(
    page: Pagination = Depends(get_pagination),
    conn: Connection = Depends(get_connection),
):
    return repository.list_authors(conn, page)


@router.get("/{author_id}", response_model=Author)
def get_author(author_id: int, conn: Connection = Depends(get_connection)):
    row = repository.get_author(conn, author_id)
    if row is None:
        raise NotFoundError("Author")
    return row


@router.put("/{author_id}", response_model=Author)
def update_author(
    author_id: int, author: AuthorIn, conn: Connection = Depends(get_connection)
):
    row = repository.update_author(conn, author_id, author)
    if row is None:
        raise NotFoundError("Author")
    return row


@router.delete("/{author_id}", status_code=204)
def delete_author(author_id: int, conn: Connection = Depends(get_connection)):
    if not repository.delete_author(conn, author_id):
        raise NotFoundError("Author")
    return Response(status_code=204)