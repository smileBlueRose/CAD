import httpx

METADATA_URL = "http://169.254.169.254/latest"
METADATA_FIELDS = {
    "instance_id": "instance-id",
    "instance_type": "instance-type",
    "availability_zone": "placement/availability-zone",
    "private_ip": "local-ipv4",
}


def get_instance_metadata() -> dict:
    try:
        token = httpx.put(
            f"{METADATA_URL}/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=1,
        ).text
        headers = {"X-aws-ec2-metadata-token": token}
        return {
            key: httpx.get(
                f"{METADATA_URL}/meta-data/{path}", headers=headers, timeout=1
            ).text
            for key, path in METADATA_FIELDS.items()
        }
    except httpx.HTTPError:
        return {key: "unknown" for key in METADATA_FIELDS}
