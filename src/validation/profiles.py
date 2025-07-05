import re
from datetime import date
from io import BytesIO

from PIL import Image
from fastapi import UploadFile

from database.models.accounts import GenderEnum


def validate_name(name: str) -> None:
    """Validate that a name contains only English letters.
    
    Args:
        name (str): The name to validate.
        
    Raises:
        ValueError: If the name contains non-English letters.
    """
    if re.search(r"^[A-Za-z]*$", name) is None:
        raise ValueError(f"{name} contains non-english letters")


def validate_image(image: UploadFile) -> None:
    """Validate uploaded image file format and size.
    
    Args:
        image (UploadFile): The uploaded image file to validate.
        
    Raises:
        ValueError: If the image format is unsupported or file size exceeds 1MB.
    """
    supported_image_formats = ["JPG", "JPEG", "PNG"]
    max_file_size = 1 * 1024 * 1024

    contents = image.file.read()
    if len(contents) > max_file_size:
        raise ValueError("Image size exceeds 1 MB")

    try:
        pil_image = Image.open(BytesIO(contents))
        image.file.seek(0)
        image_format = pil_image.format
        if image_format not in supported_image_formats:
            raise ValueError(
                f"Unsupported image format: {image_format}. Use one of next: {supported_image_formats}"
            )
    except IOError:
        raise ValueError("Invalid image format")


def validate_gender(gender: str) -> None:
    """Validate that the gender value is one of the allowed enum values.
    
    Args:
        gender (str): The gender value to validate.
        
    Raises:
        ValueError: If the gender is not one of the allowed values.
    """
    if gender.lower() not in [g.value.lower() for g in GenderEnum]:
        raise ValueError(
            f"Gender must be one of: {', '.join(g.value for g in GenderEnum)}"
        )


def validate_birth_date(birth_date: date) -> None:
    """Validate that the birth date is reasonable and user is at least 18.
    
    Args:
        birth_date (date): The birth date to validate.
        
    Raises:
        ValueError: If the birth date is before 1900 or user is under 18.
    """
    if birth_date.year < 1900:
        raise ValueError("Invalid birth date - year must be greater than 1900.")

    age = (date.today() - birth_date).days // 365
    if age < 18:
        raise ValueError("You must be at least 18 years old to register.")
