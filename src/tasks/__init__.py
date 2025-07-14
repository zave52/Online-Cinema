"""Tasks module for the Online Cinema application.

This module provides background task functionality for the application,
including Celery task management and scheduled operations.

The module includes:
- Celery application configuration and setup
- Background task decorators for async operations
- Scheduled tasks for token cleanup and maintenance
- Task execution and monitoring functions

The module supports asynchronous task processing through Celery
with Redis as the message broker and result backend.
"""
