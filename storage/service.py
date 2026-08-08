"""
Supabase storage service layer.

All file upload/download/delete operations against Supabase Storage
should go through this module. Views and business logic must never
call the Supabase client libraries directly.

The Supabase service role key is server-side only — it must never
be exposed to any client-facing response or log.
"""

from django.conf import settings
from supabase import create_client, Client


_client: Client | None = None


def _get_client() -> Client:
    """
    Lazily initialize and return the Supabase client.

    Uses the service role key from Django settings. Raises ValueError
    if credentials are not configured.
    """
    global _client
    if _client is None:
        url: str = settings.SUPABASE_URL
        key: str = settings.SUPABASE_SERVICE_ROLE_KEY
        if not url or not key:
            raise ValueError("Supabase credentials not configured in settings.")
        _client = create_client(url, key)
    return _client


def upload_file(bucket: str, path: str, file_data: bytes, content_type: str = "application/octet-stream") -> dict:
    """
    Upload a file to the specified Supabase Storage bucket.

    Args:
        bucket: The name of the Supabase Storage bucket.
        path: The destination path/key within the bucket.
        file_data: Raw file bytes to upload.
        content_type: MIME type of the file.

    Returns:
        A dict with upload metadata (e.g. path).
    """
    client = _get_client()
    client.storage.from_(bucket).upload(
        file=file_data,
        path=path,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return {"path": path, "bucket": bucket}


def get_signed_url(bucket: str, path: str, expires_in: int = 3600) -> str:
    """
    Generate a time-limited signed URL for a stored file.

    Use this to give the frontend temporary access to a file
    without exposing the service role key.

    Args:
        bucket: The name of the Supabase Storage bucket.
        path: The file path/key within the bucket.
        expires_in: URL validity in seconds (default 1 hour).

    Returns:
        A signed URL string, or empty string on failure.
    """
    client = _get_client()
    response = client.storage.from_(bucket).create_signed_url(path, expires_in)
    if "signedURL" in response:
        return response["signedURL"]
    return ""


def delete_file(bucket: str, path: str) -> None:
    """
    Delete a file from the specified Supabase Storage bucket.

    Args:
        bucket: The name of the Supabase Storage bucket.
        path: The file path/key within the bucket.
    """
    client = _get_client()
    client.storage.from_(bucket).remove([path])
