"""
Example: how to use BankStatementParser.

Run from project root:
  python -m examples.use_bank_statement_parser [path/to/statement.pdf]

Or from code:

  from backend.services.bank_statement_parser import BankStatementParser
  parser = BankStatementParser()
  result = parser.parse("statement.pdf")
  print(result["statement_summary"])
  print(result["transactions"][:3])
"""
import argparse
import json
import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from backend.services.bank_statement_parser import BankStatementParser
    from backend.services.parser_exceptions import (
        PasswordProtectedPDFError,
        ScannedPDFError,
        UnrecognizedFormatError,
        MalformedDataError,
    )

    parser = argparse.ArgumentParser(description="Parse a bank statement PDF")
    parser.add_argument("pdf_path", nargs="?", help="Path to bank statement PDF")
    args = parser.parse_args()

    if not args.pdf_path:
        print("Usage: python -m examples.use_bank_statement_parser <path/to/statement.pdf>")
        print("\nOutput structure:")
        print("  account_holder: { name, address }")
        print("  account_details: { account_number, currency }")
        print("  statement_summary: { opening_balance, closing_balance, total_debit, total_credit }")
        print("  transactions: [ { date, description, debit, credit, balance }, ... ]")
        return 0

    path = os.path.abspath(args.pdf_path)
    if not os.path.isfile(path):
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    bank_parser = BankStatementParser()
    try:
        result = bank_parser.parse(path)
        print(json.dumps(result, indent=2))
        return 0
    except PasswordProtectedPDFError as e:
        print(f"Error: PDF is password-protected. {e}", file=sys.stderr)
        return 1
    except ScannedPDFError as e:
        print(f"Error: Scanned PDF; OCR failed or unavailable. {e}", file=sys.stderr)
        return 1
    except UnrecognizedFormatError as e:
        print(f"Error: Bank format not recognized. {e}", file=sys.stderr)
        return 1
    except MalformedDataError as e:
        print(f"Error: Invalid or missing data. {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
