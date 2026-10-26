import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="CAD — App", lifespan=lifespan)

if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)
