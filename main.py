201~200~from datetime import datetime, timezone
from functools import lru_cache
import socket

import httpx
import uvicorn
from fastapi import FastAPI, Request

app = FastAPI(title="Cloud Practice App")

METADATA_URL = "http://169.254.169.254/latest"
METADATA_FIELDS = {
        "instance_id": "instance-id",
            "instance_type": "instance-type",
                "availability_zone": "placement/availability-zone",
                    "private_ip": "local-ipv4",
                    }


                    @lru_cache
                    def get_instance_metadata() -> dict:
                        try:
                                token = httpx.put(
                                                f"{METADATA_URL}/api/token",
                                                            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
                                                                        timeout=1,
                                                                                ).text
                                                                                        headers = {"X-aws-ec2-metadata-token": token}
                                                                                                return {
                                                                                                                key: httpx.get(f"{METADATA_URL}/meta-data/{path}", headers=headers, timeout=1).text
                                                                                                                            for key, path in METADATA_FIELDS.items()
                                                                                                                                    }
                                                                                                                                        except httpx.HTTPError:
                                                                                                                                                return {key: "unknown" for key in METADATA_FIELDS}


                                                                                                                                                def get_client_ip(request: Request) -> str:
                                                                                                                                                    forwarded_for = request.headers.get("x-forwarded-for")
                                                                                                                                                        if forwarded_for:
                                                                                                                                                                return forwarded_for.split(",")[0].strip()
                                                                                                                                                                    return request.client.host if request.client else "unknown"


                                                                                                                                                                    @app.get("/")
                                                                                                                                                                    def root():
                                                                                                                                                                        return {
                                                                                                                                                                                    "message": "Hello from Cloud Practice App",
                                                                                                                                                                                            "hostname": socket.gethostname(),
                                                                                                                                                                                                    "instance": get_instance_metadata(),
                                                                                                                                                                                                        }


                                                                                                                                                                                                        @app.get("/health")
                                                                                                                                                                                                        def health():
                                                                                                                                                                                                            return {"status": "ok"}


                                                                                                                                                                                                            @app.get("/client")
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


                                                                                                                                                                                                                                                                                                                        if __name__ == "__main__":
                                                                                                                                                                                                                                                                                                                            uvicorn.run(app, host="0.0.0.0", port=80)
                                                                                                                                                                                                                }
                                                                                                                                                                        })
                                                                                                }
                                )
}
