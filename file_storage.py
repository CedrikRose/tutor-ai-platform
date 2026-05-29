"""
File Storage Module

Handles file uploads with support for:
- Local filesystem storage (development)
- AWS S3 storage (production)
"""
import os
import uuid
import logging
import zipfile
import tempfile
from pathlib import Path
from typing import Optional, BinaryIO, List, Tuple
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from config import settings

logger = logging.getLogger(__name__)


class FileStorage:
    """
    Abstract file storage interface.

    Supports both local filesystem and S3 storage.
    """

    def __init__(self):
        """Initialize storage based on settings."""
        self.storage_type = settings.file_storage_type

        if self.storage_type == "s3":
            self.s3_client = boto3.client('s3', region_name=settings.aws_region)
            self.bucket_name = settings.aws_s3_bucket
            logger.info(f"Initialized S3 storage: {self.bucket_name}")
        else:
            self.local_path = Path(settings.file_storage_path)
            self.local_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Initialized local storage: {self.local_path}")

    def generate_unique_filename(self, original_filename: str) -> str:
        """
        Generate unique filename preserving extension.

        Args:
            original_filename: Original file name

        Returns:
            Unique filename with timestamp and UUID
        """
        # Extract extension
        file_ext = Path(original_filename).suffix

        # Generate unique name
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        return f"{timestamp}_{unique_id}{file_ext}"

    def save_file(
        self,
        file_content: BinaryIO,
        original_filename: str,
        course_id: Optional[str] = None
    ) -> str:
        """
        Save file to storage.

        Args:
            file_content: File content (binary)
            original_filename: Original filename
            course_id: Optional course ID for organization

        Returns:
            Storage path/key
        """
        unique_filename = self.generate_unique_filename(original_filename)

        # Build path with course organization
        if course_id:
            storage_path = f"courses/{course_id}/{unique_filename}"
        else:
            storage_path = f"uploads/{unique_filename}"

        if self.storage_type == "s3":
            return self._save_to_s3(file_content, storage_path)
        else:
            return self._save_to_local(file_content, storage_path)

    def _save_to_s3(self, file_content: BinaryIO, s3_key: str) -> str:
        """Save file to S3."""
        try:
            self.s3_client.upload_fileobj(
                file_content,
                self.bucket_name,
                s3_key
            )

            logger.info(f"File uploaded to S3: s3://{self.bucket_name}/{s3_key}")
            return f"s3://{self.bucket_name}/{s3_key}"

        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise

    def _save_to_local(self, file_content: BinaryIO, relative_path: str) -> str:
        """Save file to local filesystem."""
        full_path = self.local_path / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, 'wb') as f:
            f.write(file_content.read())

        logger.info(f"File saved locally: {full_path}")
        return str(full_path)

    def get_file(self, storage_path: str) -> bytes:
        """
        Retrieve file from storage.

        Args:
            storage_path: Storage path/key

        Returns:
            File content as bytes
        """
        if storage_path.startswith("s3://"):
            return self._get_from_s3(storage_path)
        else:
            return self._get_from_local(storage_path)

    def _get_from_s3(self, s3_path: str) -> bytes:
        """Retrieve file from S3."""
        # Parse s3://bucket/key
        parts = s3_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1]

        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"S3 download failed: {e}")
            raise

    def _get_from_local(self, local_path: str) -> bytes:
        """Retrieve file from local filesystem."""
        with open(local_path, 'rb') as f:
            return f.read()

    def delete_file(self, storage_path: str) -> bool:
        """
        Delete file from storage.

        Args:
            storage_path: Storage path/key

        Returns:
            True if deleted
        """
        if storage_path.startswith("s3://"):
            return self._delete_from_s3(storage_path)
        else:
            return self._delete_from_local(storage_path)

    def _delete_from_s3(self, s3_path: str) -> bool:
        """Delete file from S3."""
        parts = s3_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1]

        try:
            self.s3_client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"File deleted from S3: {s3_path}")
            return True
        except ClientError as e:
            logger.error(f"S3 delete failed: {e}")
            return False

    def _delete_from_local(self, local_path: str) -> bool:
        """Delete file from local filesystem."""
        try:
            os.remove(local_path)
            logger.info(f"File deleted locally: {local_path}")
            return True
        except OSError as e:
            logger.error(f"Local delete failed: {e}")
            return False

    def get_file_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get temporary URL for file access.

        Args:
            storage_path: Storage path/key
            expires_in: URL expiry in seconds (default 1 hour)

        Returns:
            Pre-signed URL (S3) or local path
        """
        if storage_path.startswith("s3://"):
            return self._get_s3_presigned_url(storage_path, expires_in)
        else:
            # For local files, return path (frontend needs to handle this)
            return storage_path

    def _get_s3_presigned_url(self, s3_path: str, expires_in: int) -> str:
        """Generate pre-signed URL for S3 object."""
        parts = s3_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1]

        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    def validate_file(
        self,
        filename: str,
        file_size: int,
        allowed_extensions: Optional[list] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate file before upload.

        Args:
            filename: Original filename
            file_size: File size in bytes
            allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.py'])

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        max_size = settings.max_file_size_mb * 1024 * 1024  # Convert MB to bytes
        if file_size > max_size:
            return False, f"File size exceeds {settings.max_file_size_mb} MB"

        # Check extension
        if allowed_extensions:
            file_ext = Path(filename).suffix.lower()
            if file_ext not in allowed_extensions:
                return False, f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"

        return True, None

    def extract_zip(self, zip_path: str, course_id: str) -> List[Tuple[str, str]]:
        """
        Extract ZIP file and save contents to storage.

        Args:
            zip_path: Path to ZIP file
            course_id: Course ID for organization

        Returns:
            List of tuples (filename, storage_path) for extracted files
        """
        extracted_files = []

        try:
            # Get ZIP content
            zip_content = self.get_file(zip_path)

            # Create temporary file for ZIP
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
                tmp_zip.write(zip_content)
                tmp_zip_path = tmp_zip.name

            # Extract ZIP
            with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    # Skip directories and hidden files
                    if file_info.is_dir() or file_info.filename.startswith('__MACOSX'):
                        continue

                    # Extract file content
                    file_content = zip_ref.read(file_info.filename)

                    # Save to storage with preserved path structure
                    relative_path = file_info.filename
                    unique_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{Path(relative_path).name}"

                    if course_id:
                        storage_path = f"courses/{course_id}/{unique_filename}"
                    else:
                        storage_path = f"uploads/{unique_filename}"

                    if self.storage_type == "s3":
                        # Save to S3
                        import io
                        file_obj = io.BytesIO(file_content)
                        stored_path = self._save_to_s3(file_obj, storage_path)
                    else:
                        # Save to local filesystem
                        full_path = self.local_path / storage_path
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(full_path, 'wb') as f:
                            f.write(file_content)
                        stored_path = str(full_path)

                    extracted_files.append((relative_path, stored_path))
                    logger.info(f"Extracted from ZIP: {relative_path} -> {stored_path}")

            # Clean up temporary ZIP file
            os.remove(tmp_zip_path)

            logger.info(f"Extracted {len(extracted_files)} files from ZIP")
            return extracted_files

        except zipfile.BadZipFile as e:
            logger.error(f"Invalid ZIP file: {e}")
            raise ValueError("Invalid ZIP file")
        except Exception as e:
            logger.error(f"ZIP extraction failed: {e}")
            raise


# Global storage instance
_storage_instance = None


def get_storage() -> FileStorage:
    """Get global file storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = FileStorage()
    return _storage_instance


if __name__ == "__main__":
    # Test storage
    storage = get_storage()
    print(f"Storage type: {storage.storage_type}")

    # Test filename generation
    unique = storage.generate_unique_filename("test.pdf")
    print(f"Unique filename: {unique}")

    # Test validation
    valid, error = storage.validate_file("test.pdf", 1024 * 1024, ['.pdf', '.txt'])
    print(f"Validation: {valid}, Error: {error}")
