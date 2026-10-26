from contextlib import asynccontextmanager

import psycopg
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from db import init_db
from errors import ConflictError, NotFoundError
from routers import authors, books, health, info, loans, members


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="CAD App", lifespan=lifespan)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(NotFoundError)
async def not_found(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(psycopg.IntegrityError)
async def integrity_error(request: Request, exc: psycopg.IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "Constraint violation"})


@app.exception_handler(psycopg.OperationalError)
async def database_unavailable(request: Request, exc: psycopg.OperationalError):
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


for module in (info, health, authors, books, members, loans):
    app.include_router(module.router)


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.host, port=settings.port)