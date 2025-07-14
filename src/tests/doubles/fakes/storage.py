from storages.interfaces import S3StorageInterface


class FakeStorage(S3StorageInterface):
    """Fake S3 storage for testing purposes.

    This class simulates the behavior of an S3 storage service, storing files
    in-memory. It is intended to be used as a substitute for the real S3 storage
    in tests.

    Attributes:
        files (dict[str, bytes]): A dictionary to store file data, where keys
            are file names and values are file content in bytes.
    """

    def __init__(self):
        """Initializes the FakeStorage with an empty file dictionary."""
        self.files = {}

    async def upload_file(self, file_name: str, file_data: bytes) -> None:
        """Simulates uploading a file to the storage.

        Args:
            file_name: The name of the file to upload.
            file_data: The content of the file in bytes.
        """
        self.files[file_name] = file_data

    async def get_file_url(self, file_name: str) -> str:
        """Generates a fake URL for a given file name.

        Args:
            file_name: The name of the file.

        Returns:
            A string representing the fake URL for the file.
        """
        return f"https://fake-bucket.local/{file_name}"
