import socket
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from metadata import get_instance_metadata

router = APIRouter(tags=["info"])


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/")
def root():
    return {
        "message": "Hello from Cloud Practice App",
        "hostname": socket.gethostname(),
        "instance": get_instance_metadata(),
    }


@router.get("/client")
def client_info(request: Request):
    return {
        "ip": get_client_ip(request),
        "port": request.client.port if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "accept_language": request.headers.get("accept-language"),
        "referer": request.headers.get("referer"),
        "protocol": request.headers.get("x-forwarded-proto", request.url.scheme),
        "method": request.method,
        "url": str(request.url),
        "query_params": dict(request.query_params),
        "headers": dict(request.headers),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "served_by": get_instance_metadata()["instance_id"],
    }
