"""
Storage service - handles file upload/download to object storage
"""
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
import uuid
from datetime import datetime


class StorageService:
    """
    Service for managing file storage in S3-compatible object storage.
    """

    def __init__(self):
        """Initialize S3 client"""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    def upload_file(self, file, tenant_id, document_guid):
        """
        Upload file to object storage.

        Args:
            file: Django uploaded file object
            tenant_id: UUID of the tenant
            document_guid: UUID of the document

        Returns:
            Storage key (S3 key)
        """
        # Generate unique storage key
        timestamp = datetime.utcnow().strftime('%Y/%m/%d')
        unique_id = uuid.uuid4().hex[:8]
        storage_key = f"tenants/{tenant_id}/documents/{document_guid}/{timestamp}/{unique_id}_{file.name}"

        # Upload to S3
        self.s3_client.upload_fileobj(
            file,
            self.bucket_name,
            storage_key,
            ExtraArgs={
                'ContentType': file.content_type,
                'ACL': 'private'
            }
        )

        return storage_key

    def download_file(self, storage_key):
        """
        Download file from object storage.

        Args:
            storage_key: S3 key of the file

        Returns:
            File-like object
        """
        import io

        # Download from S3
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=storage_key
        )

        # Return file stream
        return io.BytesIO(response['Body'].read())

    def delete_file(self, storage_key):
        """
        Delete file from object storage.

        Args:
            storage_key: S3 key of the file
        """
        self.s3_client.delete_object(
            Bucket=self.bucket_name,
            Key=storage_key
        )

    def get_presigned_url(self, storage_key, expiration=3600):
        """
        Generate presigned URL for temporary access.

        Args:
            storage_key: S3 key of the file
            expiration: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL string
        """
        url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': storage_key
            },
            ExpiresIn=expiration
        )

        return url
