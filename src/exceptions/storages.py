class BaseS3Error(Exception):
    """Base exception class for S3 storage-related errors.

    This is the parent class for all S3 storage exceptions in the application.
    It provides a common interface for S3 error handling.
    """

    def __init__(self, message: str | None = None) -> None:
        """Initialize the base S3 error.

        Args:
            message (str, optional): Custom error message. Defaults to generic message.
        """
        if message is None:
            message = "An S3 storage error occurred."
        super().__init__(message)


class S3ConnectionError(BaseS3Error):
    """Exception raised when connection to S3 storage fails.

    This exception is raised when the application cannot establish a
    connection to the S3-compatible storage service.
    """

    def __init__(
        self,
        message: str = "Failed to connect to S3 storage."
    ) -> None:
        """Initialize the S3 connection error.

        Args:
            message (str): Error message. Defaults to "Failed to connect to S3 storage."
        """
        super().__init__(message)


class S3BucketNotFoundError(BaseS3Error):
    """Exception raised when the specified S3 bucket is not found.

    This exception is raised when the application tries to access a bucket
    that doesn't exist or is not accessible.
    """

    def __init__(self, message: str = "S3 bucket not found.") -> None:
        """Initialize the S3 bucket not found error.

        Args:
            message (str): Error message. Defaults to "S3 bucket not found."
        """
        super().__init__(message)


class S3FileUploadError(BaseS3Error):
    """Exception raised when file upload to S3 fails.

    This exception is raised when there's an error during file upload
    operations to S3 storage.
    """

    def __init__(self, message: str = "Failed to upload file to S3.") -> None:
        """Initialize the S3 file upload error.

        Args:
            message (str): Error message. Defaults to "Failed to upload file to S3."
        """
        super().__init__(message)


class S3FileNotFoundError(BaseS3Error):
    """Exception raised when a requested file is not found in S3.

    This exception is raised when trying to access a file that doesn't
    exist in the S3 storage bucket.
    """

    def __init__(
        self, message: str = "Requested file not found in S3."
    ) -> None:
        """Initialize the S3 file not found error.

        Args:
            message (str): Error message. Defaults to "Requested file not found in S3."
        """
        super().__init__(message)


class S3PermissionError(BaseS3Error):
    """Exception raised when there are insufficient permissions for S3 operations.

    This exception is raised when the application doesn't have the required
    permissions to perform operations on S3 resources.
    """

    def __init__(
        self, message: str = "Insufficient permissions to access S3 resources."
    ) -> None:
        """Initialize the S3 permission error.

        Args:
            message (str): Error message. Defaults to
                            "Insufficient permissions to access S3 resources."
        """
        super().__init__(message)
