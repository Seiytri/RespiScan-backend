"""
Supabase storage service layer.

All file upload/download/delete operations against Supabase Storage
should go through this module. Views and business logic must never
call the Supabase client libraries directly.

The Supabase service role key is server-side only — it must never
be exposed to any client-facing response or log.
"""

import time
import httpx
from django.conf import settings
from supabase import create_client, Client, ClientOptions


_client: Client | None = None
_signed_url_cache: dict[str, tuple[str, float]] = {}


def _get_client() -> Client:
    """
    Lazily initialize and return the Supabase client.

    Uses HTTP/1.1 and explicit socket timeouts to avoid Windows non-blocking
    socket issues ([WinError 10035]) and HTTP/2 stream multiplexing bugs.
    """
    global _client
    if _client is None:
        url: str = settings.SUPABASE_URL
        key: str = settings.SUPABASE_SERVICE_ROLE_KEY
        if not url or not key:
            raise ValueError("Supabase credentials not configured in settings.")
        
        # Disable http2 to eliminate Windows WSAEWOULDBLOCK / WinError 10035 errors
        http_client = httpx.Client(
            http2=False,
            timeout=httpx.Timeout(60.0, connect=15.0),
            follow_redirects=True,
        )
        options = ClientOptions(httpx_client=http_client)
        _client = create_client(url, key, options=options)
    return _client


def upload_file(bucket: str, path: str, file_data: bytes, content_type: str = "application/octet-stream") -> dict:
    """
    Upload a file to the specified Supabase Storage bucket with retry on stale connection.

    Args:
        bucket: The name of the Supabase Storage bucket.
        path: The destination path/key within the bucket.
        file_data: Raw file bytes to upload.
        content_type: MIME type of the file.

    Returns:
        A dict with upload metadata (e.g. path).
    """
    global _client
    for attempt in range(2):
        try:
            client = _get_client()
            client.storage.from_(bucket).upload(
                file=file_data,
                path=path,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            return {"path": path, "bucket": bucket}
        except Exception as e:
            # Stale connection or socket drop: reset client to reconnect on retry
            _client = None
            if attempt == 1:
                raise e
            time.sleep(0.5)


def get_signed_url(bucket: str, path: str, expires_in: int = 3600) -> str:
    """
    Generate a time-limited signed URL for a stored file.
    Caches the signed URL in memory so subsequent requests return instantly without network overhead.
    """
    global _client
    cache_key = f"{bucket}:{path}"
    cached = _signed_url_cache.get(cache_key)
    if cached:
        url, exp = cached
        if time.time() < exp - 60:
            return url

    try:
        client = _get_client()
        response = client.storage.from_(bucket).create_signed_url(path, expires_in)
        if "signedURL" in response and response["signedURL"]:
            url = response["signedURL"]
            _signed_url_cache[cache_key] = (url, time.time() + expires_in)
            return url
    except Exception:
        _client = None
    return ""


def delete_file(bucket: str, path: str) -> None:
    """
    Delete a file from the specified Supabase Storage bucket.
    """
    global _client
    cache_key = f"{bucket}:{path}"
    _signed_url_cache.pop(cache_key, None)
    try:
        client = _get_client()
        client.storage.from_(bucket).remove([path])
    except Exception:
        _client = None

