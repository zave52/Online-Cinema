"""Storages module for the Online Cinema application.

This module provides file storage functionality for the application,
including S3-compatible storage operations and file management.

The module includes:
- S3StorageInterface: Abstract interface for storage operations
- S3Storage: S3-compatible storage implementation
- File upload and URL generation functions
- Storage configuration and management

The module supports multiple storage providers through the interface
pattern, with S3-compatible storage as the primary implementation.
"""
