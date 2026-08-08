"""
Supabase storage service layer.

All file upload/download/delete operations against Supabase Storage
should go through this module. Views and business logic must never
call the Supabase client libraries directly.

The Supabase service role key is server-side only — it must never
be exposed to any client-facing response or log.
"""

from django.conf import settings


def upload_file(bucket: str, path: str, file_data: bytes, content_type: str = "application/octet-stream") -> dict:
    """
    Upload a file to the specified Supabase Storage bucket.

    Args:
        bucket: The name of the Supabase Storage bucket.
        path: The destination path/key within the bucket.
        file_data: Raw file bytes to upload.
        content_type: MIME type of the file.

    Returns:
        A dict with upload metadata (e.g. key, url).

    Raises:
        NotImplementedError: Stub — not yet implemented.
    """
    raise NotImplementedError("Supabase storage upload is not yet implemented.")


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
        A signed URL string.

    Raises:
        NotImplementedError: Stub — not yet implemented.
    """
    raise NotImplementedError("Supabase signed URL generation is not yet implemented.")


def delete_file(bucket: str, path: str) -> None:
    """
    Delete a file from the specified Supabase Storage bucket.

    Args:
        bucket: The name of the Supabase Storage bucket.
        path: The file path/key within the bucket.

    Raises:
        NotImplementedError: Stub — not yet implemented.
    """
    raise NotImplementedError("Supabase storage delete is not yet implemented.")
