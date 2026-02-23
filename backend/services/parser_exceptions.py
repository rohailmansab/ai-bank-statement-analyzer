"""
Custom exceptions for the bank statement parser.
Enables callers to handle specific failure modes (password-protected, scanned, etc.).
"""


class BankStatementParserError(Exception):
    """Base exception for all parser errors."""

    pass


class PasswordProtectedPDFError(BankStatementParserError):
    """Raised when the PDF is password-protected and cannot be read."""

    pass


class ScannedPDFError(BankStatementParserError):
    """Raised when the PDF appears to be scanned/image-only and OCR failed or is unavailable."""

    pass


class UnrecognizedFormatError(BankStatementParserError):
    """Raised when the bank statement format could not be identified or has no matching config."""

    pass


class MalformedDataError(BankStatementParserError):
    """Raised when extracted data is missing, inconsistent, or invalid."""

    pass
