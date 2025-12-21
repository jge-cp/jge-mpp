"""
Server-side file upload validation utilities.

This module provides validation functions for file uploads to ensure
only allowed file types are accepted and basic security checks pass.
"""
import os
from django.conf import settings
from django.core.exceptions import ValidationError


# Get allowed extensions from settings, with sensible defaults
ALLOWED_EXTENSIONS = getattr(
    settings, 
    'ALLOWED_FILE_EXTENSIONS', 
    ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif']
)

# Maximum file size (from settings or default 10MB)
MAX_FILE_SIZE = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 10485760)

# Dangerous extensions that should never be allowed
DANGEROUS_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.sh', '.php', '.py', '.rb', '.pl',
    '.js', '.vbs', '.ps1', '.msi', '.jar', '.com', '.scr',
    '.dll', '.so', '.dylib', '.bin', '.app', '.dmg',
    '.html', '.htm', '.svg',  # Can contain scripts
}


class FileValidationError(ValidationError):
    """Custom exception for file validation errors"""
    pass


def validate_file_extension(file):
    """
    Validate that the uploaded file has an allowed extension.
    
    Args:
        file: Django UploadedFile object
        
    Returns:
        The file extension (lowercase, with leading dot)
        
    Raises:
        FileValidationError: If extension is not allowed or is dangerous
    """
    filename = file.name
    if not filename:
        raise FileValidationError("File must have a name.")
    
    # Get extension (lowercase)
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    if not ext:
        raise FileValidationError("File must have an extension.")
    
    # Check for dangerous extensions first
    if ext in DANGEROUS_EXTENSIONS:
        raise FileValidationError(
            f"File type '{ext}' is not allowed for security reasons."
        )
    
    # Check against allowed extensions
    allowed = [e.lower() for e in ALLOWED_EXTENSIONS]
    if ext not in allowed:
        raise FileValidationError(
            f"File type '{ext}' is not allowed. "
            f"Allowed types: {', '.join(allowed)}"
        )
    
    return ext


def validate_file_size(file, max_size=None):
    """
    Validate that the file doesn't exceed the maximum size.
    
    Args:
        file: Django UploadedFile object
        max_size: Maximum size in bytes (defaults to MAX_FILE_SIZE)
        
    Raises:
        FileValidationError: If file is too large
    """
    max_size = max_size or MAX_FILE_SIZE
    
    if file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        file_mb = file.size / (1024 * 1024)
        raise FileValidationError(
            f"File is too large ({file_mb:.1f} MB). "
            f"Maximum allowed size is {max_mb:.1f} MB."
        )


def validate_filename(file):
    """
    Validate that the filename doesn't contain path traversal attempts.
    
    Args:
        file: Django UploadedFile object
        
    Raises:
        FileValidationError: If filename is suspicious
    """
    filename = file.name
    
    # Check for path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        raise FileValidationError(
            "Invalid filename. Filename cannot contain path separators."
        )
    
    # Check for null bytes
    if '\x00' in filename:
        raise FileValidationError("Invalid filename.")


def validate_upload(file, max_size=None, allowed_extensions=None):
    """
    Perform all file validations.
    
    Args:
        file: Django UploadedFile object
        max_size: Optional maximum size in bytes
        allowed_extensions: Optional list of allowed extensions
        
    Returns:
        dict with file info:
            - extension: the file extension
            - size: file size in bytes
            - name: sanitized filename
            
    Raises:
        FileValidationError: If any validation fails
    """
    if file is None:
        raise FileValidationError("No file provided.")
    
    # Filename validation
    validate_filename(file)
    
    # Size validation
    validate_file_size(file, max_size)
    
    # Extension validation (using custom list if provided)
    if allowed_extensions:
        original_allowed = ALLOWED_EXTENSIONS
        try:
            # Temporarily override for this check
            globals()['ALLOWED_EXTENSIONS'] = allowed_extensions
            ext = validate_file_extension(file)
        finally:
            globals()['ALLOWED_EXTENSIONS'] = original_allowed
    else:
        ext = validate_file_extension(file)
    
    return {
        'extension': ext,
        'size': file.size,
        'name': file.name,
    }


def validate_uploads(files, max_size=None, allowed_extensions=None):
    """
    Validate multiple file uploads.
    
    Args:
        files: List of Django UploadedFile objects
        max_size: Optional maximum size per file in bytes
        allowed_extensions: Optional list of allowed extensions
        
    Returns:
        List of file info dicts
        
    Raises:
        FileValidationError: If any file fails validation
    """
    results = []
    for file in files:
        result = validate_upload(file, max_size, allowed_extensions)
        results.append(result)
    return results

