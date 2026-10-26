import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    db_host: str
    db_port: int
    db_name: str
    db_secret_arn: str
    aws_region: str
    cors_origins: tuple[str, ...]


settings = Settings(
    host="0.0.0.0",
    port=8000,
    db_host=os.environ["DB_HOST"],
    db_port=int(os.environ.get("DB_PORT", "5432")),
    db_name=os.environ["DB_NAME"],
    db_secret_arn=os.environ["DB_SECRET_ARN"],
    aws_region=os.environ.get("AWS_REGION", "us-east-1"),
    cors_origins=tuple(
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ),
)
