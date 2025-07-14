from typing import Dict, Any

profile_create_request_schema_example: Dict[str, Any] = {
    "first_name": "John",
    "last_name": "Doe",
    "gender": "man",
    "date_of_birth": "1990-05-15",
    "info": "Movie enthusiast and film critic. Love watching sci-fi and action movies.",
    "avatar": "avatar_file_upload"
}

profile_update_request_schema_example: Dict[str, Any] = {
    "first_name": "John",
    "last_name": "Smith",
    "gender": "man",
    "date_of_birth": "1990-05-15",
    "info": "Updated bio: Movie enthusiast and film critic. Love watching "
            "sci-fi and action movies. Also enjoy documentaries.",
    "avatar": "new_avatar_file_upload"
}

profile_patch_request_schema_example: Dict[str, Any] = {
    "first_name": "John",
    "last_name": "Smith",
    "info": "Updated bio information only"
}

profile_response_schema_example: Dict[str, Any] = {
    "id": 1,
    "user_id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "gender": "man",
    "date_of_birth": "1990-05-15",
    "info": "Movie enthusiast and film critic. Love watching sci-fi and action movies.",
    "avatar": "https://example.com/avatars/john_doe_avatar.jpg"
}

profile_retrieve_schema_example: Dict[str, Any] = {
    "id": 1,
    "user_id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "gender": "man",
    "date_of_birth": "1990-05-15",
    "info": "Movie enthusiast and film critic. Love watching sci-fi and action movies.",
    "avatar": "https://example.com/avatars/john_doe_avatar.jpg",
    "email": "john.doe@example.com"
}

message_response_schema_example: Dict[str, Any] = {
    "message": "Profile created successfully"
}
