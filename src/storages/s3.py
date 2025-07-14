import aioboto3  # type: ignore
from botocore.exceptions import (  # type: ignore
    HTTPClientError,
    NoCredentialsError,
    BotoCoreError
)

from exceptions.storages import S3ConnectionError, S3FileUploadError
from storages.interfaces import S3StorageInterface


class S3Storage(S3StorageInterface):
    """S3-compatible storage implementation for file operations.

    This class provides asynchronous file upload and URL generation
    capabilities for S3-compatible storage services. It handles
    connection management, error handling, and file operations.

    Attributes:
        _access_key (str): S3 access key for authentication
        _secret_key (str): S3 secret key for authentication
        _endpoint_url (str): S3 endpoint URL
        _bucket_name (str): S3 bucket name for file storage
        _session (aioboto3.Session): Boto3 session for S3 operations
    """

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        endpoint_url: str,
        bucket_name: str
    ) -> None:
        """Initialize S3 storage with connection parameters.

        Args:
            access_key: S3 access key for authentication
            secret_key: S3 secret key for authentication
            endpoint_url: S3 endpoint URL (e.g., https://s3.amazonaws.com)
            bucket_name: S3 bucket name where files will be stored

        Example:
            ```python
            storage = S3Storage(
                access_key="AKIAIOSFODNN7EXAMPLE",
                secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                endpoint_url="https://s3.amazonaws.com",
                bucket_name="my-cinema-bucket"
            )
            ```
        """
        self._access_key = access_key
        self._secret_key = secret_key
        self._endpoint_url = endpoint_url
        self._bucket_name = bucket_name

        self._session = aioboto3.Session(
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key
        )

    async def upload_file(
        self,
        file_name: str,
        file_data: bytes | bytearray
    ) -> None:
        """Upload a file to S3 storage.

        This method uploads file data to the configured S3 bucket with
        the specified file name. It handles connection errors and upload
        failures with appropriate exception handling.

        Args:
            file_name: Name of the file to upload (e.g., "movie_poster.jpg")
            file_data: Binary data of the file to upload

        Raises:
            S3ConnectionError: When connection to S3 storage fails
            S3FileUploadError: When file upload operation fails

        Example:
            ```python
            with open("poster.jpg", "rb") as f:
                image_data = f.read()

            await storage.upload_file("movies/poster_123.jpg", image_data)
            ```

        Note:
            Files are uploaded with Content-Type "image/jpeg" by default.
            For other file types, consider extending this method to accept
            content type as a parameter.
        """
        try:
            async with self._session.client(
                "s3", endpoint_url=self._endpoint_url
            ) as client:
                await client.put_object(
                    Bucket=self._bucket_name,
                    Key=file_name,
                    Body=file_data,
                    ContentType="image/jpeg"
                )
        except (ConnectionError, HTTPClientError, NoCredentialsError) as e:
            raise S3ConnectionError(
                f"Failed to connect to S3 storage: {str(e)}"
            ) from e
        except BotoCoreError as e:
            raise S3FileUploadError(
                f"Failed to upload to S3 storage: {str(e)}"
            ) from e

    async def get_file_url(self, file_name: str) -> str:
        """Generate a URL for accessing an uploaded file.

        This method constructs a direct URL to access a file stored
        in the S3 bucket. The URL format follows the pattern:
        {endpoint_url}/{bucket_name}/{file_name}

        Args:
            file_name: Name of the file to generate URL for

        Returns:
            Complete URL string for accessing the file

        Example:
            ```python
            url = await storage.get_file_url("movies/poster_123.jpg")
            # Returns: "https://s3.amazonaws.com/my-bucket/movies/poster_123.jpg"
            ```

        Note:
            This method generates direct URLs. For production use,
            consider implementing signed URLs for security or using
            CloudFront distribution URLs for better performance.
        """
        return f"{self._endpoint_url}/{self._bucket_name}/{file_name}"
