class PaymentError(Exception):
    """Base exception class for payment-related errors.
    
    This is the parent class for all payment exceptions in the application.
    It provides a common interface for payment error handling.
    """
    pass


class WebhookError(PaymentError):
    """Exception raised when there's an error processing payment webhooks.
    
    This exception is raised when webhook events from payment providers
    cannot be processed or validated properly.
    """
    pass


class PaymentValidationError(PaymentError):
    """Exception raised when payment data validation fails.
    
    This exception is raised when payment information (amount, currency,
    payment method, etc.) fails validation checks.
    """
    pass


class PaymentProcessingError(PaymentError):
    """Exception raised when payment processing fails.
    
    This exception is raised when there's an error during the actual
    payment processing with the payment provider (e.g., Stripe).
    """
    pass
