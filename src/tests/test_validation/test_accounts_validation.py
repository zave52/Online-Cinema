import pytest
from pydantic import ValidationError

from database.models.accounts import UserGroupEnum
from schemas.accounts import (
    PasswordChangeRequestSchema,
    PasswordResetCompleteRequestSchema,
    PasswordResetRequestSchema,
    ResendActivationTokenRequestSchema,
    UserActivationRequestSchema,
    UserGroupUpdateRequestSchema,
    UserManualActivationSchema,
    UserRegistrationRequestSchema
)


class TestAccountValidation:
    """Test account-related validation logic."""

    def test_valid_user_registration(self):
        """Test valid user registration data."""
        valid_data = {
            "email": "user@example.com",
            "password": "SecurePassword123!",
        }
        user = UserRegistrationRequestSchema(**valid_data)
        assert user.email == "user@example.com"
        assert user.password == "SecurePassword123!"

    def test_invalid_email_formats(self):
        """Test various invalid email formats."""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user..user@example.com",
            "user@.com",
            "",
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError):
                UserRegistrationRequestSchema(
                    email=email, password="SecurePassword123!"
                )

    def test_password_validation_rules(self):
        """Test password strength validation."""
        weak_passwords = [
            "short",
            "nouppercase1!",
            "NOLOWERCASE1!",
            "NoDigit!",
            "NoSpecial1",
            "",
        ]

        for password in weak_passwords:
            with pytest.raises(ValidationError):
                UserRegistrationRequestSchema(
                    email="user@example.com", password=password
                )


class TestPasswordChangeValidation:
    """Test password change validation logic."""

    def test_valid_password_change(self):
        """Test valid password change data."""
        valid_data = {
            "old_password": "OldSecurePassword123!",
            "new_password": "NewSecurePassword123!",
        }
        password_change = PasswordChangeRequestSchema(**valid_data)
        assert password_change.old_password == "OldSecurePassword123!"
        assert password_change.new_password == "NewSecurePassword123!"

    def test_invalid_new_password(self):
        """Test invalid new password formats."""
        weak_passwords = [
            "short",
            "nouppercase1!",
            "NOLOWERCASE1!",
            "NoDigit!",
            "NoSpecial1",
            "",
        ]
        for password in weak_passwords:
            with pytest.raises(ValidationError):
                PasswordChangeRequestSchema(
                    old_password="OldSecurePassword123!", new_password=password
                )


class TestPasswordResetValidation:
    """Test password reset request validation logic."""

    def test_valid_password_reset_request(self):
        """Test valid password reset request data."""
        valid_data = {"email": "user@example.com"}
        request = PasswordResetRequestSchema(**valid_data)
        assert request.email == "user@example.com"

    def test_invalid_email_password_reset_request(self):
        """Test invalid email for password reset request."""
        with pytest.raises(ValidationError):
            PasswordResetRequestSchema(email="not-an-email")


class TestResendActivationTokenValidation:
    """Test resend activation token request validation logic."""

    def test_valid_resend_activation_token_request(self):
        """Test valid resend activation token request data."""
        valid_data = {"email": "user@example.com"}
        request = ResendActivationTokenRequestSchema(**valid_data)
        assert request.email == "user@example.com"

    def test_invalid_email_resend_activation_token_request(self):
        """Test invalid email for resend activation token request."""
        with pytest.raises(ValidationError):
            ResendActivationTokenRequestSchema(email="not-an-email")


class TestPasswordResetCompleteValidation:
    """Test password reset complete validation logic."""

    def test_valid_password_reset_complete(self):
        """Test valid password reset complete data."""
        valid_data = {
            "email": "user@example.com",
            "password": "NewSecurePassword123!",
            "token": "valid-token",
        }
        request = PasswordResetCompleteRequestSchema(**valid_data)
        assert request.email == "user@example.com"
        assert request.password == "NewSecurePassword123!"

    def test_invalid_password_reset_complete(self):
        """Test invalid password for password reset complete."""
        with pytest.raises(ValidationError):
            PasswordResetCompleteRequestSchema(
                email="user@example.com",
                password="weak",
                token="valid-token",
            )


class TestUserActivationValidation:
    """Test user activation validation logic."""

    def test_valid_user_activation(self):
        """Test valid user activation data."""
        valid_data = {"email": "user@example.com", "token": "valid-token"}
        request = UserActivationRequestSchema(**valid_data)
        assert request.email == "user@example.com"

    def test_invalid_email_user_activation(self):
        """Test invalid email for user activation."""
        with pytest.raises(ValidationError):
            UserActivationRequestSchema(
                email="not-an-email",
                token="valid-token"
            )


class TestUserGroupUpdateValidation:
    """Test user group update validation logic."""

    def test_valid_user_group_update(self):
        """Test valid user group update data."""
        valid_data = {"group_name": UserGroupEnum.ADMIN}
        request = UserGroupUpdateRequestSchema(**valid_data)
        assert request.group_name == UserGroupEnum.ADMIN

    def test_invalid_user_group_update(self):
        """Test invalid user group for update."""
        with pytest.raises(ValidationError):
            UserGroupUpdateRequestSchema(group_name="invalid-group")


class TestUserManualActivationValidation:
    """Test user manual activation validation logic."""

    def test_valid_user_manual_activation(self):
        """Test valid user manual activation data."""
        valid_data = {"email": "user@example.com"}
        request = UserManualActivationSchema(**valid_data)
        assert request.email == "user@example.com"

    def test_invalid_email_user_manual_activation(self):
        """Test invalid email for user manual activation."""
        with pytest.raises(ValidationError):
            UserManualActivationSchema(email="not-an-email")
