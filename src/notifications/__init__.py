"""Notifications module for the Online Cinema application.

This module provides email notification functionality for the application,
including email sending interfaces, template management, and various
notification types.

The module includes:
- EmailSenderInterface: Abstract interface for email services
- EmailSender: FastAPI-Mail implementation of the email interface
- Email templates for various notification types
- Support for HTML email templates with Jinja2

The module supports multiple email providers through the interface
pattern, with FastAPI-Mail as the primary implementation.
"""
