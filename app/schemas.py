from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class AuthorIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    country: str | None = Field(default=None, max_length=100)


class Author(AuthorIn):
    id: int
    created_at: datetime


class BookIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author_id: int = Field(gt=0)
    year: int | None = Field(default=None, ge=0, le=2100)
    total_copies: int = Field(default=1, ge=0)


class Book(BookIn):
    id: int
    available_copies: int
    created_at: datetime


class MemberIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr


class Member(MemberIn):
    id: int
    created_at: datetime


class LoanIn(BaseModel):
    book_id: int = Field(gt=0)
    member_id: int = Field(gt=0)


class Loan(LoanIn):
    id: int
    status: Literal["active", "returned", "overdue"]
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None
