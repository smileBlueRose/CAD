from typing import Literal

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from db import get_connection
from dependencies import Pagination, get_pagination
from errors import NotFoundError
from repositories import loans as repository
from schemas import Loan, LoanIn

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("", response_model=Loan, status_code=201)
def borrow_book(loan: LoanIn, conn: Connection = Depends(get_connection)):
    return repository.borrow_book(conn, loan)


@router.get("", response_model=list[Loan])
def list_loans(
    member_id: int | None = Query(default=None, gt=0),
    status: Literal["active", "returned", "overdue"] | None = None,
    page: Pagination = Depends(get_pagination),
    conn: Connection = Depends(get_connection),
):
    return repository.list_loans(conn, page, member_id, status)


@router.get("/{loan_id}", response_model=Loan)
def get_loan(loan_id: int, conn: Connection = Depends(get_connection)):
    row = repository.get_loan(conn, loan_id)
    if row is None:
        raise NotFoundError("Loan")
    return row


@router.post("/{loan_id}/return", response_model=Loan)
def return_book(loan_id: int, conn: Connection = Depends(get_connection)):
    return repository.return_book(conn, loan_id)