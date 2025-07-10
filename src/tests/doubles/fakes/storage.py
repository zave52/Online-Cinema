from storages.interfaces import S3StorageInterface


class FakeStorage(S3StorageInterface):
    """Fake S3 storage for testing."""

    def __init__(self):
        self.files = {}

    async def upload_file(self, file_name: str, file_data: bytes) -> None:
        """Simulate file upload."""
        self.files[file_name] = file_data

    async def get_file_url(self, file_name: str) -> str:
        """Return a fake URL for the file."""
        return f"https://fake-bucket.s3.amazonaws.com/{file_name}"
