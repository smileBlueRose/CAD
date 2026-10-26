from fastapi import APIRouter, Depends, Response
from psycopg import Connection

from db import get_connection
from dependencies import Pagination, get_pagination
from errors import NotFoundError
from repositories import members as repository
from schemas import Member, MemberIn

router = APIRouter(prefix="/members", tags=["members"])


@router.post("", response_model=Member, status_code=201)
def create_member(member: MemberIn, conn: Connection = Depends(get_connection)):
    return repository.create_member(conn, member)


@router.get("", response_model=list[Member])
def list_members(
    page: Pagination = Depends(get_pagination),
    conn: Connection = Depends(get_connection),
):
    return repository.list_members(conn, page)


@router.get("/{member_id}", response_model=Member)
def get_member(member_id: int, conn: Connection = Depends(get_connection)):
    row = repository.get_member(conn, member_id)
    if row is None:
        raise NotFoundError("Member")
    return row


@router.put("/{member_id}", response_model=Member)
def update_member(
    member_id: int, member: MemberIn, conn: Connection = Depends(get_connection)
):
    row = repository.update_member(conn, member_id, member)
    if row is None:
        raise NotFoundError("Member")
    return row


@router.delete("/{member_id}", status_code=204)
def delete_member(member_id: int, conn: Connection = Depends(get_connection)):
    if not repository.delete_member(conn, member_id):
        raise NotFoundError("Member")
    return Response(status_code=204)