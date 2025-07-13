from typing import Dict, Any

user_registration_request_schema_example: Dict[str, Any] = {
    "email": "john.doe@example.com",
    "password": "SecurePassword123!"
}

user_registration_response_schema_example: Dict[str, Any] = {
    "id": 1,
    "email": "john.doe@example.com",
    "is_active": False,
    "created_at": "2024-01-15T10:30:00Z",
    "group": {
        "id": 1,
        "name": "user"
    }
}

user_login_request_schema_example: Dict[str, Any] = {
    "email": "john.doe@example.com",
    "password": "SecurePassword123!"
}

user_login_response_schema_example: Dict[str, Any] = {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcl9pZCI6MSwiZW1haW"
                    "wiOiJqb2huLmRvZUBleGFtcGxlLmNvbSIsImdyb3VwIjoiIn0.Ej8Ej8Ej8Ej8Ej8Ej8Ej8Ej8E"
                    "j8Ej8Ej8Ej8Ej8",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcl9pZCI6MSwiZW1ha"
                     "WwiOiJqb2huLmRvZUBleGFtcGxlLmNvbSIsImdyb3VwIjoiIn0.Ej8Ej8Ej8Ej8Ej8Ej8Ej8Ej"
                     "8Ej8Ej8Ej8Ej8Ej8",
    "token_type": "bearer",
    "user": {
        "id": 1,
        "email": "john.doe@example.com",
        "is_active": True,
        "created_at": "2024-01-15T10:30:00Z",
        "group": {
            "id": 1,
            "name": "user"
        }
    }
}

password_reset_request_schema_example: Dict[str, Any] = {
    "email": "john.doe@example.com"
}

resend_activation_token_request_schema_example: Dict[str, Any] = {
    "email": "john.doe@example.com"
}

password_reset_complete_request_schema_example: Dict[str, Any] = {
    "email": "john.doe@example.com",
    "password": "NewSecurePassword123!",
    "token": "reset_token_123456789"
}

password_change_request_schema_example: Dict[str, Any] = {
    "old_password": "SecurePassword123!",
    "new_password": "NewSecurePassword123!"
}

token_refresh_request_schema_example: Dict[str, Any] = {
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcl9pZCI6MSwiZW1h"
                     "aWwiOiJqb2huLmRvZUBleGFtcGxlLmNvbSIsImdyb3VwIjoiIn0.Ej8Ej8Ej8Ej8Ej8Ej8Ej8"
                     "Ej8Ej8Ej8Ej8Ej8Ej8"
}

token_refresh_response_schema_example: Dict[str, Any] = {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcl9pZCI6MSwiZW1ha"
                    "WwiOiJqb2huLmRvZUBleGFtcGxlLmNvbSIsImdyb3VwIjoiIn0.Ej8Ej8Ej8Ej8Ej8Ej8Ej8Ej"
                    "8Ej8Ej8Ej8Ej8Ej8",
    "token_type": "bearer"
}

token_verify_request_schema_example: Dict[str, Any] = {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcl9pZCI6MSwiZW1ha"
                    "WwiOiJqb2huLmRvZUBleGFtcGxlLmNvbSIsImdyb3VwIjoiIn0.Ej8Ej8Ej8Ej8Ej8Ej8Ej8Ej"
                    "8Ej8Ej8Ej8Ej8Ej8"
}

user_activation_request_schema_example: Dict[str, Any] = {
    "email": "john.doe@example.com",
    "token": "activation_token_123456789"
}

user_group_update_request_schema_example: Dict[str, Any] = {
    "group_name": "moderator"
}

user_manual_activation_schema_example: Dict[str, Any] = {
    "email": "john.doe@example.com"
}

message_response_schema_example: Dict[str, Any] = {
    "message": "Operation completed successfully"
}
