"""Domain exceptions for DOCX processing.

@author lliqa
@course Wuhan University Open Source Software and Technology 2026
"""

from __future__ import annotations


class DocxStyleTreeError(Exception):
    """@brief Base exception for expected DOCX style tree failures."""


class InvalidDocxError(DocxStyleTreeError):
    """@brief Raised when an input package is not a valid DOCX document."""


class InvalidStyleMapError(DocxStyleTreeError, ValueError):
    """@brief Raised when a style mapping is missing or malformed."""
