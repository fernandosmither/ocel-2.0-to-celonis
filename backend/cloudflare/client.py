import asyncio
import uuid
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import HTTPException

from .config import settings


class R2Client:
    """Client for interacting with Cloudflare R2 storage."""

    def __init__(self):
        """Initialize the R2 client with settings."""
        self._s3_resource = None
        self._bucket = None

    def _get_s3_resource(self):
        """Get or create S3 resource for R2."""
        if self._s3_resource is None:
            try:
                self._s3_resource = boto3.resource(
                    "s3",
                    endpoint_url=settings.R2_ENDPOINT_URL,
                    aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
                )
            except NoCredentialsError:
                raise HTTPException(
                    status_code=500, detail="Cloudflare R2 credentials not configured"
                )
        return self._s3_resource

    def _get_bucket(self):
        """Get or create bucket object."""
        if self._bucket is None:
            s3 = self._get_s3_resource()
            self._bucket = s3.Bucket(settings.R2_BUCKET_NAME)  # type: ignore
        return self._bucket

    async def upload_file(
        self, file_content: bytes, filename: str | None = None
    ) -> str:
        """
        Upload a file to R2 and return the UUID filename.

        Args:
            file_content: The file content as bytes
            filename: Optional original filename (for reference only)

        Returns:
            str: The UUID4 filename (without extension)

        Raises:
            HTTPException: If upload fails
        """
        try:
            file_uuid = str(uuid.uuid4())
            object_key = f"{file_uuid}.jsonocel"

            bucket = self._get_bucket()

            def _upload():
                bucket.put_object(Key=object_key, Body=file_content)

            await asyncio.get_event_loop().run_in_executor(None, _upload)

            return file_uuid

        except ClientError as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to upload file to R2: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Unexpected error during upload: {str(e)}"
            )

    async def download_file(self, file_uuid: str) -> bytes:
        """
        Download a file from R2 by UUID.

        Args:
            file_uuid: The UUID4 of the file

        Returns:
            bytes: The file content

        Raises:
            HTTPException: If file doesn't exist or download fails
        """
        try:
            object_key = f"{file_uuid}.jsonocel"
            bucket = self._get_bucket()

            def _download():
                obj = bucket.Object(object_key)
                return obj.get()["Body"].read()

            file_content = await asyncio.get_event_loop().run_in_executor(
                None, _download
            )
            return file_content

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise HTTPException(
                    status_code=404,
                    detail=f"File with UUID {file_uuid} not found in R2",
                )
            else:
                raise HTTPException(
                    status_code=500, detail=f"Failed to download file from R2: {str(e)}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Unexpected error during download: {str(e)}"
            )

    async def file_exists(self, file_uuid: str) -> bool:
        """
        Check if a file exists in R2.

        Args:
            file_uuid: The UUID4 of the file

        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            object_key = f"{file_uuid}.jsonocel"
            bucket = self._get_bucket()

            def _check_exists():
                try:
                    bucket.Object(object_key).head()
                    return True
                except ClientError as e:
                    if e.response["Error"]["Code"] == "404":
                        return False
                    raise

            return await asyncio.get_event_loop().run_in_executor(None, _check_exists)

        except Exception:
            return False
