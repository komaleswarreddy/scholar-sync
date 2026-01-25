"""
File Utilities

Utilities for file operations.
"""

# TODO: Implement file utilities
# - File type detection
# - File size validation
# - File reading helpers


def get_file_type(filename: str) -> str:
    """Get file type from filename."""
    # TODO: Implement file type detection
    return filename.split(".")[-1] if "." in filename else ""

