from pathlib import Path
from uuid import uuid4

from app.config import AWS_ENDPOINT_URL, LOCAL_STORAGE_DIR, S3_BUCKET, STORAGE_BACKEND


class PrivateStorage:
    def __init__(self) -> None:
        if STORAGE_BACKEND not in {"local", "s3"}:
            raise RuntimeError("STORAGE_BACKEND must be 'local' or 's3'.")
        if STORAGE_BACKEND == "s3" and not S3_BUCKET:
            raise RuntimeError("S3_BUCKET is required when STORAGE_BACKEND=s3.")
        self.backend = STORAGE_BACKEND
        if self.backend == "local":
            LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        else:
            import boto3

            self.client = boto3.client("s3", endpoint_url=AWS_ENDPOINT_URL or None)

    def save(self, assignment_id: int, student_id: int, filename: str, content: bytes, content_type: str) -> str:
        key = f"submissions/{assignment_id}/{student_id}/{uuid4().hex}/{Path(filename).name}"
        if self.backend == "local":
            destination = LOCAL_STORAGE_DIR / key
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        else:
            self.client.put_object(Bucket=S3_BUCKET, Key=key, Body=content, ContentType=content_type)
        return key

    def read(self, key: str) -> bytes:
        if self.backend == "local":
            return (LOCAL_STORAGE_DIR / key).read_bytes()
        return self.client.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()


storage = PrivateStorage()