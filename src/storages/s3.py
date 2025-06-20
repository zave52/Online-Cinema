import aioboto3
from botocore.exceptions import (
    HTTPClientError,
    NoCredentialsError,
    BotoCoreError
)

from exceptions.storages import S3ConnectionError, S3FileUploadError
from storages.interfaces import S3StorageInterface


class S3Storage(S3StorageInterface):
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        endpoint_url: str,
        bucket_name: str
    ) -> None:
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
        return f"{self._endpoint_url}/{self._bucket_name}/{file_name}"
