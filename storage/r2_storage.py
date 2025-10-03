"""Utilities for interacting with Cloudflare R2 using the S3-compatible API."""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError
from werkzeug.utils import secure_filename

__all__ = [
    "R2Config",
    "R2ObjectStream",
    "R2Storage",
    "create_r2_storage_from_env",
]

DEFAULT_REGION = "auto"
DEFAULT_UPLOAD_PREFIX = "uploads"
MIN_EXPIRY_SECONDS = 300  # 5 minutes
MAX_EXPIRY_SECONDS = 24 * 3600  # 24 hours


@dataclass(frozen=True)
class R2Config:
    """Configuration payload for wiring the Cloudflare R2 client."""

    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    region: str = DEFAULT_REGION
    public_base_url: str | None = None
    upload_prefix: str = DEFAULT_UPLOAD_PREFIX

    @property
    def endpoint_url(self) -> str:
        return f"https://{self.account_id}.r2.cloudflarestorage.com"


class R2ObjectStream:
    """Thin wrapper around the streaming body returned by R2.

    It exposes a read-only, forward-only stream interface suitable for piping into
    other streaming consumers (e.g., YouTube resumable uploads).
    """

    def __init__(self, *, body, size: int, content_type: str | None) -> None:  # body is botocore.response.StreamingBody
        self._body = body
        self.size = size
        self.content_type = content_type
        self._bytes_read = 0

    def read(self, amt: Optional[int] = None) -> bytes:
        chunk = self._body.read(amt)
        if chunk:
            self._bytes_read += len(chunk)
        return chunk

    def iter_chunks(self, chunk_size: int) -> Iterable[bytes]:
        while True:
            chunk = self.read(chunk_size)
            if not chunk:
                break
            yield chunk

    def close(self) -> None:
        try:
            self._body.close()
        except AttributeError:
            pass

    @property
    def bytes_read(self) -> int:
        return self._bytes_read


class R2Storage:
    """High-level helper around Cloudflare R2 uploads/downloads."""

    def __init__(self, config: R2Config) -> None:
        self._config = config
        session = boto3.session.Session()
        self._client = session.client(
            "s3",
            region_name=config.region,
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            config=BotoConfig(signature_version="s3v4"),
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    @property
    def bucket(self) -> str:
        return self._config.bucket_name

    def public_url(self, object_key: str) -> str | None:
        base = (self._config.public_base_url or "").strip()
        if not base:
            return None
        return f"{base.rstrip('/')}/{object_key.lstrip('/')}"

    def generate_object_key(self, *, filename: str | None = None, prefix: str | None = None) -> str:
        """Create a deterministic object key with a UUID and optional extension."""

        upload_prefix = (prefix or self._config.upload_prefix or DEFAULT_UPLOAD_PREFIX).strip()
        upload_prefix = upload_prefix.replace("..", "").strip("/") or DEFAULT_UPLOAD_PREFIX

        safe_name = secure_filename(filename or "")
        extension = Path(safe_name).suffix.lower() if safe_name else ""
        unique = uuid.uuid4().hex
        return f"{upload_prefix}/{unique}{extension}"

    def create_presigned_upload(
        self,
        *,
        filename: str | None,
        content_type: str | None,
        prefix: str | None = None,
        expires_in: int = 3600,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return data required for clients to PUT directly to R2."""

        expiry = max(MIN_EXPIRY_SECONDS, min(int(expires_in), MAX_EXPIRY_SECONDS))
        object_key = self.generate_object_key(filename=filename, prefix=prefix)

        params: Dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": object_key,
        }
        if content_type:
            params["ContentType"] = content_type

        if metadata:
            meta_filtered: Dict[str, str] = {}
            for key, value in metadata.items():
                if value is None:
                    continue
                meta_filtered[str(key)] = str(value)
            if meta_filtered:
                params["Metadata"] = meta_filtered

        upload_url = self._client.generate_presigned_url(
            ClientMethod="put_object",
            Params=params,
            ExpiresIn=expiry,
        )

        response_payload: Dict[str, Any] = {
            "object_key": object_key,
            "upload_url": upload_url,
            "expires_in": expiry,
            "required_headers": {},
        }
        if content_type:
            response_payload["required_headers"] = {"Content-Type": content_type}
        public_url = self.public_url(object_key)
        if public_url:
            response_payload["public_url"] = public_url
        return response_payload

    def generate_presigned_download(self, object_key: str, *, expires_in: int = 3600) -> str:
        expiry = max(MIN_EXPIRY_SECONDS, min(int(expires_in), MAX_EXPIRY_SECONDS))
        return self._client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=expiry,
        )

    def open_stream(self, object_key: str) -> R2ObjectStream:
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=object_key)
        except (ClientError, BotoCoreError) as exc:  # noqa: PERF203
            raise RuntimeError(f"Unable to fetch {object_key} from R2: {exc}") from exc

        body = response.get("Body")
        if body is None:
            raise RuntimeError(f"Received empty body when fetching {object_key} from R2")

        size = int(response.get("ContentLength") or 0)
        content_type = response.get("ContentType")
        return R2ObjectStream(body=body, size=size, content_type=content_type)


# ----------------------------------------------------------------------
# Bootstrap helpers
# ----------------------------------------------------------------------
REQUIRED_ENV_KEYS = (
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
)


def create_r2_storage_from_env(env: Optional[Mapping[str, str]] = None) -> tuple[Optional[R2Storage], list[str]]:
    """Instantiate an R2Storage client from environment variables.

    Returns the storage instance (or None when misconfigured) and a list of
    missing environment keys to aid diagnostics.
    """

    env_map: Mapping[str, str] = env or os.environ
    missing = [key for key in REQUIRED_ENV_KEYS if not env_map.get(key)]
    if missing:
        return None, missing

    config = R2Config(
        account_id=env_map["R2_ACCOUNT_ID"].strip(),
        access_key_id=env_map["R2_ACCESS_KEY_ID"].strip(),
        secret_access_key=env_map["R2_SECRET_ACCESS_KEY"].strip(),
        bucket_name=env_map["R2_BUCKET_NAME"].strip(),
        region=(env_map.get("R2_REGION") or DEFAULT_REGION).strip(),
        public_base_url=(env_map.get("R2_PUBLIC_BASE_URL") or None),
        upload_prefix=(env_map.get("R2_UPLOAD_PREFIX") or DEFAULT_UPLOAD_PREFIX),
    )

    return R2Storage(config), []
