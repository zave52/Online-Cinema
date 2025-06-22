class BaseS3Error(Exception):
    def __init__(self, message: str = None) -> None:
        if message is None:
            message = "An S3 storage error occurred."
        super().__init__(message)


class S3ConnectionError(BaseS3Error):
    def __init__(
        self,
        message: str = "Failed to connect to S3 storage."
    ) -> None:
        super().__init__(message)


class S3BucketNotFoundError(BaseS3Error):
    def __init__(self, message: str = "S3 bucket not found.") -> None:
        super().__init__(message)


class S3FileUploadError(BaseS3Error):
    def __init__(self, message: str = "Failed to upload file to S3.") -> None:
        super().__init__(message)


class S3FileNotFoundError(BaseS3Error):
    def __init__(
        self, message: str = "Requested file not found in S3."
    ) -> None:
        super().__init__(message)


class S3PermissionError(BaseS3Error):
    def __init__(
        self, message: str = "Insufficient permissions to access S3 resources."
    ) -> None:
        super().__init__(message)
