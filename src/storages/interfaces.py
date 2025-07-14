from abc import ABC, abstractmethod


class S3StorageInterface(ABC):
    """Abstract interface for S3 storage operations.

    This interface defines the contract for file storage operations including
    file upload and URL generation for cloud storage services.
    """

    @abstractmethod
    async def upload_file(
        self,
        file_name: str,
        file_data: bytes | bytearray
    ) -> None:
        """Upload a file to S3 storage.

        Args:
            file_name (str): Name of the file to upload.
            file_data (bytes | bytearray): File data to upload.
        """
        pass

    @abstractmethod
    async def get_file_url(self, file_name: str) -> str:
        """Get the public URL for a file in S3 storage.

        Args:
            file_name (str): Name of the file.

        Returns:
            str: Public URL for the file.
        """
        pass
