import os
from django.conf import settings
from supabase import create_client, Client

class SupabaseStorageService:
    def __init__(self):
        url: str = settings.SUPABASE_URL
        key: str = settings.SUPABASE_SERVICE_ROLE_KEY
        if not url or not key:
            raise ValueError("Supabase credentials not configured in settings.")
        self.supabase: Client = create_client(url, key)
        self.bucket_name = 'respiscan-scans' # Default bucket for scans

    def upload_file(self, file_content: bytes, destination_path: str, content_type: str = 'application/octet-stream') -> str:
        """
        Uploads a file to Supabase storage.
        Returns the path to the uploaded file.
        """
        response = self.supabase.storage.from_(self.bucket_name).upload(
            file=file_content,
            path=destination_path,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        return destination_path

    def get_signed_url(self, file_path: str, expires_in_seconds: int = 3600) -> str:
        """
        Generates a signed URL to securely download a file.
        """
        response = self.supabase.storage.from_(self.bucket_name).create_signed_url(file_path, expires_in_seconds)
        if 'signedURL' in response:
             return response['signedURL']
        return ""
