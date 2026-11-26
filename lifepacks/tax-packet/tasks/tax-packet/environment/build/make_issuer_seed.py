#!/usr/bin/env python3
"""Build the Bayview Bank document page seed for the task-owned issuer-docs App.

Writes the same seed to the App's fixtures (for app:verify and business tests) and to
environment/workspace/issuer-docs/seed.json (the task's starting state).
Run after make_documents.py:  python3 -I environment/build/make_issuer_seed.py
"""
import base64
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_documents import OUT as DOCS, TASK, pdf_bytes  # noqa: E402

APP_DIR = os.path.join(TASK, "environment", "apps", "issuer-docs")
WORKSPACE = os.path.join(TASK, "environment", "workspace", "issuer-docs")


def doc(document_id, kind, title, tax_year, issued_at, available_from, filename, data):
    return {
        "document_id": document_id, "account_ref": "bayview-savings-4410", "kind": kind, "title": title,
        "tax_year": tax_year, "issued_at": issued_at, "available_from": available_from, "filename": filename,
        "mime_type": "application/pdf", "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        "base64": base64.b64encode(data).decode(),
    }


def build():
    with open(os.path.join(DOCS, "D10-bayview-1099-int-2025.pdf"), "rb") as fh:
        form = fh.read()
    statement = pdf_bytes("Bayview Bank Savings Statement, July 2025", [
        "Account holder: Rowan Ellis", "Account: savings, last four 4410", "Period: 2025-07-01 to 2025-07-31",
        "Opening balance: 6,412.90", "Interest paid: 11.48", "Closing balance: 6,424.38"])
    closure = pdf_bytes("Bayview Bank Account Closure Confirmation", [
        "Account holder: Rowan Ellis", "Account: savings, last four 4410", "Closed: 2025-08-29",
        "Final balance transferred by check: 6,431.07", "A Form 1099-INT for 2025 will be made available on this page if interest paid in 2025 is reportable."])
    seed = {
        "account_id": "issuer-docs-rowan", "owner_person_id": "person-rowan",
        "institution": {"institution_id": "bayview-bank", "name": "Bayview Bank", "time_zone": "America/Los_Angeles"},
        "accounts": [{"account_ref": "bayview-savings-4410", "label": "Savings", "last_four": "4410", "status": "closed", "closed_on": "2025-08-29"}],
        "documents": [
            doc("bv-stmt-2025-07", "statement", "Savings statement, July 2025", None, "2025-08-04T08:00:00-07:00", "2025-08-04T08:00:00-07:00", "bayview-savings-2025-07.pdf", statement),
            doc("bv-closure-2025", "letter", "Account closure confirmation", None, "2025-08-29T15:00:00-07:00", "2025-08-29T15:00:00-07:00", "bayview-closure-2025-08-29.pdf", closure),
            doc("bv-1099int-2025", "tax_form", "Form 1099-INT, tax year 2025", 2025, "2026-03-10T06:00:00-07:00", "2026-03-10T06:00:00-07:00", "bayview-1099-int-2025.pdf", form),
        ],
    }
    for target in (os.path.join(APP_DIR, "fixtures", "minimal.json"), os.path.join(WORKSPACE, "seed.json")):
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w") as fh:
            json.dump(seed, fh, indent=2)
            fh.write("\n")
    print("wrote issuer-docs seed with", len(seed["documents"]), "documents")


if __name__ == "__main__":
    sys.exit(build())
