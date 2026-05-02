"""Storage backend abstraction — Local filesystem or Cloudflare R2 (S3-compatible).

키(key) 구조는 두 백엔드가 동일:
  videos/{kind}/{form_id}/{uuid}.{ext}
  poses/{kind}/{form_id}/{uuid}.json
  renders/{kind}/{form_id}/{uuid}.mp4

DB의 video_path / pose_path / overlay_path 컬럼은 백엔드 무관하게 '키'를 저장.
실제 사용 시 storage.url(key)로 재생용 URL을, storage.local_path(key)로
임시 로컬 경로를 얻음.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol

from .paths import DATA_DIR, ensure_dirs


# ---------- Protocol ----------

class StorageBackend(Protocol):
    """Common interface — keys are POSIX-style relative paths (e.g. 'videos/refs/abc.mp4')."""

    backend_name: str

    def upload(self, local_path: Path, key: str) -> None: ...
    def download(self, key: str, local_path: Path) -> None: ...
    def url(self, key: str) -> str: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...

    @contextmanager
    def open_local(self, key: str):
        """Yield a local Path that contains the object's bytes for reading.
        For LocalStorage this is the canonical file; for R2 it's a temp file."""
        ...


# ---------- Local filesystem ----------

class LocalStorage:
    backend_name = "local"

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _abs(self, key: str) -> Path:
        # Treat key as POSIX relative path under root
        return self.root / Path(key)

    def upload(self, local_path: Path, key: str) -> None:
        target = self._abs(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if Path(local_path).resolve() != target.resolve():
            shutil.copy2(local_path, target)

    def download(self, key: str, local_path: Path) -> None:
        src = self._abs(key)
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != local_path.resolve():
            shutil.copy2(src, local_path)

    def url(self, key: str) -> str:
        # st.video accepts a local file path string
        return str(self._abs(key))

    def delete(self, key: str) -> None:
        path = self._abs(key)
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass

    def exists(self, key: str) -> bool:
        return self._abs(key).exists()

    @contextmanager
    def open_local(self, key: str):
        # For local backend, the file IS the canonical path
        yield self._abs(key)


# ---------- Cloudflare R2 (S3-compatible) ----------

class R2Storage:
    backend_name = "r2"

    def __init__(
        self,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        url_ttl: int = 3600,
    ):
        # Lazy import boto3 so local-only environments don't need it
        import boto3
        from botocore.client import Config

        self.endpoint = endpoint
        self.bucket = bucket
        self.url_ttl = url_ttl
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )

    def upload(self, local_path: Path, key: str) -> None:
        self.client.upload_file(str(local_path), self.bucket, key)

    def download(self, key: str, local_path: Path) -> None:
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key, str(local_path))

    def url(self, key: str) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=self.url_ttl,
        )

    def delete(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            pass

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    @contextmanager
    def open_local(self, key: str):
        """Download to a temp file, yield path, then clean up."""
        suffix = Path(key).suffix or ""
        tmp_dir = Path(tempfile.mkdtemp(prefix="wushu-r2-"))
        tmp_path = tmp_dir / f"obj{suffix}"
        try:
            self.download(key, tmp_path)
            yield tmp_path
        finally:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
                tmp_dir.rmdir()
            except OSError:
                pass


# ---------- Factory ----------

_STORAGE: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Return singleton storage backend chosen via STORAGE_BACKEND env var."""
    global _STORAGE
    if _STORAGE is not None:
        return _STORAGE

    ensure_dirs()
    backend = os.environ.get("STORAGE_BACKEND", "local").lower().strip()

    if backend == "r2":
        endpoint = os.environ.get("R2_ENDPOINT", "").strip()
        bucket = os.environ.get("R2_BUCKET", "").strip()
        access_key = os.environ.get("R2_ACCESS_KEY_ID", "").strip()
        secret_key = os.environ.get("R2_SECRET_ACCESS_KEY", "").strip()
        if not all([endpoint, bucket, access_key, secret_key]):
            raise RuntimeError(
                "STORAGE_BACKEND=r2 but R2_ENDPOINT / R2_BUCKET / "
                "R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY missing in env."
            )
        ttl = int(os.environ.get("R2_URL_TTL", "3600"))
        _STORAGE = R2Storage(
            endpoint=endpoint, bucket=bucket,
            access_key=access_key, secret_key=secret_key, url_ttl=ttl,
        )
    else:
        _STORAGE = LocalStorage(DATA_DIR)

    return _STORAGE


# ---------- Key helpers (used by pages) ----------

def video_key(kind: str, form_id: str, uid: str, ext: str = ".mp4") -> str:
    """e.g. 'videos/references/changquan_1duan/abc123.mp4'"""
    return f"videos/{kind}/{form_id}/{uid}{ext}"


def pose_key(kind: str, form_id: str, uid: str) -> str:
    return f"poses/{kind}/{form_id}/{uid}.json"


def overlay_key(kind: str, form_id: str, uid: str) -> str:
    return f"renders/{kind}/{form_id}/{uid}.mp4"
