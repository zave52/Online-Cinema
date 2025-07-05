"""Payments module for the Online Cinema application.

This module provides payment processing functionality for the application,
including payment interfaces, Stripe integration, and payment-related
exceptions.

The module includes:
- PaymentServiceInterface: Abstract interface for payment services
- StripePaymentService: Stripe implementation of the payment interface
- Payment exceptions for error handling
- Payment processing, refunds, and webhook handling

The module supports multiple payment providers through the interface
pattern, with Stripe as the primary implementation.
"""
