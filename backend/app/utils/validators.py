"""
Validation Utilities for Contract Management

Provides validation functions for:
- Contract number generation (format: CON-YYYYMM-XXXX)
- File type validation against allowed types
- File size validation against maximum size limit

All validations use settings from app.core.config.
"""
from datetime import datetime
from typing import List

from app.core.config import settings


def generate_contract_no() -> str:
    """
    Generate a unique contract number in the format CON-YYYYMM-XXXX.

    The format consists of:
    - CON: Prefix indicating contract number
    - YYYYMM: Current year and month
    - XXXX: 4-digit sequence number (padded with zeros)

    Returns:
        Contract number string in format: CON-YYYYMM-XXXX

    Example:
        >>> contract_no = generate_contract_no()
        >>> print(contract_no)
        "CON-202401-0001"
    """
    current_date = datetime.utcnow()
    year_month = current_date.strftime("%Y%m")
    
    # TODO: In a production system, this would query the database
    # to get the next sequence number for the current month
    # For now, we use a placeholder that will need to be replaced
    sequence = 1
    
    contract_no = f"CON-{year_month}-{sequence:04d}"
    return contract_no


def validate_file_type(filename: str) -> bool:
    """
    Validate that a file's extension is in the allowed file types.

    Args:
        filename: The name of the file to validate

    Returns:
        True if the file extension is allowed, False otherwise

    Note:
        File extensions are compared case-insensitively.

    Example:
        >>> validate_file_type("contract.pdf")
        True
        >>> validate_file_type("document.exe")
        False
    """
    if not filename:
        return False
    
    # Extract file extension (without the dot, lowercased)
    if "." in filename:
        extension = filename.rsplit(".", 1)[-1].lower()
    else:
        return False
    
    # Check against allowed file types from settings
    allowed_types = {ft.lower() for ft in settings.ALLOWED_FILE_TYPES}
    return extension in allowed_types


def validate_file_size(file_size: int) -> bool:
    """
    Validate that a file size is within the allowed maximum.

    Args:
        file_size: Size of the file in bytes

    Returns:
        True if file size is within limit, False otherwise

    Example:
        >>> validate_file_size(1024 * 1024)  # 1MB
        True
        >>> validate_file_size(100 * 1024 * 1024)  # 100MB
        False
    """
    max_size = settings.MAX_FILE_SIZE
    return file_size <= max_size


def validate_file_type_with_error(filename: str) -> tuple[bool, str]:
    """
    Validate file type and return a tuple of (is_valid, error_message).

    Args:
        filename: The name of the file to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if file type is allowed
        - error_message: Empty string if valid, error message if invalid

    Example:
        >>> is_valid, error = validate_file_type_with_error("contract.pdf")
        >>> if not is_valid:
        >>>     print(f"Error: {error}")
    """
    if not filename:
        return False, "Filename is empty"
    
    if "." not in filename:
        return False, "File has no extension"
    
    extension = filename.rsplit(".", 1)[-1].lower()
    allowed_types = {ft.lower() for ft in settings.ALLOWED_FILE_TYPES}
    
    if extension not in allowed_types:
        return False, f"Invalid file type. Allowed types: {', '.join(settings.ALLOWED_FILE_TYPES)}"
    
    return True, ""


def validate_file_size_with_error(file_size: int) -> tuple[bool, str]:
    """
    Validate file size and return a tuple of (is_valid, error_message).

    Args:
        file_size: Size of the file in bytes

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if file size is within limit
        - error_message: Empty string if valid, error message if invalid

    Example:
        >>> is_valid, error = validate_file_size_with_error(100 * 1024 * 1024)
        >>> if not is_valid:
        >>>     print(f"Error: {error}")
    """
    max_size = settings.MAX_FILE_SIZE
    
    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        return False, f"File size exceeds maximum limit of {max_size_mb:.1f}MB"
    
    return True, ""


def validate_contract_file(filename: str, file_size: int) -> tuple[bool, str]:
    """
    Validate both file type and size for contract uploads.

    Args:
        filename: The name of the file to validate
        file_size: Size of the file in bytes

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if both validations pass
        - error_message: Empty string if valid, error message if invalid

    Example:
        >>> is_valid, error = validate_contract_file("contract.pdf", 5 * 1024 * 1024)
        >>> if is_valid:
        >>>     # Proceed with upload
    """
    type_valid, type_error = validate_file_type_with_error(filename)
    if not type_valid:
        return False, type_error
    
    size_valid, size_error = validate_file_size_with_error(file_size)
    if not size_valid:
        return False, size_error
    
    return True, ""


__all__ = [
    "generate_contract_no",
    "validate_file_type",
    "validate_file_size",
    "validate_file_type_with_error",
    "validate_file_size_with_error",
    "validate_contract_file",
]
