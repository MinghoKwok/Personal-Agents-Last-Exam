#!/usr/bin/env python3
"""Build Rowan's Mail and Files workspace seeds and the scheduled Mail events for Task #102.

Writes, under environment/workspace/:
  mail/   seed.json, dataset.json, catalog.json, binding.json, assets/  (state before S1)
  mail/events.json                     (mail deliveries at S2, S3 and S4, in order)
  files/  seed.json, dataset.json, catalog.json, binding.json, assets/  (2024 reference files)

Each workspace directory is the input format of runtime/core/data-cli.cjs `pack`, which
loads it through env.load_seed. Run after make_documents.py:
  python3 -I environment/build/make_mail_files.py
"""
import base64
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_documents import OUT as DOCS, TASK  # noqa: E402

WS = os.path.join(TASK, "environment", "workspace")
ADDRESS = "rowan.ellis@pale.example"
MAIL_ACCOUNT = "mail-rowan"
FILES_ACCOUNT = "files-rowan"


def read_doc(name):
    with open(os.path.join(DOCS, name), "rb") as fh:
        return fh.read()


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(value, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def dataset(dataset_id, description, records, assets):
    return {
        "schema_version": "pale.dataset.v1", "dataset_id": dataset_id, "version": "1.0.0", "description": description,
        "record_source_ids": ["authored"],
        "sources": [{"source_id": "authored", "kind": "synthetic", "description": "Hand-authored synthetic records and generated synthetic PDFs; no external collection.",
                     "uri": None, "license": "MIT", "usage": "permitted", "collection": None,
                     "generation": {"method": "scripted", "tool": "environment/build (Task #102)", "tool_version": "0.1.0", "seed": None, "parameters": {}}}],
        "transformations": ["Generated deterministically by the task's build scripts."],
        "expected_counts": {"records": records, "assets": assets},
        "quality_policy": {"duplicate_records": "reject", "duplicate_assets": "allow", "missing_assets": "allow_declared"},
        "review": {"status": "pending", "reviewer": None, "notes": "Automatic checks do not replace human provenance and realism review."},
    }


def asset(app_id, account_id, object_type, object_id, asset_id, filename, data, dataset_id):
    return {
        "schema_version": "pale.asset-descriptor.v1", "asset_id": asset_id, "scope": {"level": "package", "app_id": app_id},
        "roles": ["content.attachment"],
        "subjects": [{"app_id": app_id, "account_id": account_id, "object_type": object_type, "object_id": object_id}],
        "mime_type": "application/pdf", "availability": {"status": "ready"},
        "storage": {"adapter": "storage.file", "path": f"assets/{filename}", "packaging": "bundled"},
        "integrity": {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()},
        "provenance": {"dataset_id": dataset_id, "source_ids": ["authored"]},
        "publication": "restricted", "access": {"audience": ["agent"], "rule": "parent_object"},
        "extensions": [],
    }


CPA_SHEET = """Hi Rowan,

Thanks for completing the intake call. For your 2025 return, please send me supporting records for these sources from the intake: Atlas Labs (W-2), Brook Systems (W-2), Northfield Brokerage, Ridgeway Invest and Cedar Bank. We agreed you would deliver them by March 10, 2026.

What I need from each form:
- W-2: box 1 (wages) and box 2 (federal income tax withheld).
- 1099-INT: box 1 (interest income).
- 1099-DIV: box 1a (total ordinary dividends) and box 1b (qualified dividends), listed separately. Box 1b is part of 1a; please do not add them together.
- 1099-B: total proceeds and reported cost basis, as printed.

Please deliver the source documents as received, plus a short manifest of what is included, a summary of the fields above by source with totals, and a handoff note with anything still open. Upload everything to your case CP-2025-ROWAN in our client portal. I only work from the current set in the portal, so please do not include last year's files.

I decide filing status, deductions and the tax itself; you do not need to work any of that out.

Best,
Morgan Lee
Morgan Lee Tax Advisory"""


def build():
    for sub in ("mail", "files"):
        shutil.rmtree(os.path.join(WS, sub), ignore_errors=True)

    # ---------------- Mail: state before S1 ----------------
    msgs, assets_, mail_assets = [], [], {}

    def msg(mid, thread, sender, subject, body, at, folder="inbox", read=True, attach=()):
        ids = []
        for name in attach:
            data = read_doc(name)
            aid = f"att-{mid}-{name.split('-')[0].lower()}"
            fname = name.split("-", 1)[1]
            assets_.append(asset("mail", MAIL_ACCOUNT, "message", mid, aid, fname, data, "tax-packet-mail"))
            mail_assets[fname] = data
            ids.append(aid)
        msgs.append({"id": mid, "thread_id": thread, "account_id": MAIL_ACCOUNT, "from": sender, "to": [ADDRESS],
                     "subject": subject, "body": body, "received_at": at, "folder": folder, "read": read, "attachments": ids})

    msg("m-2025-organizer", "lee-2024", "morgan@leetaxadvisory.example", "Your 2024 tax organizer",
        "Hi Rowan, attached to your portal case CP-2024-ROWAN is your 2024 organizer. Best, Morgan", "2025-03-03T11:00:00-08:00", folder="archive")
    msg("m-cpa-sheet", "lee-2025", "morgan@leetaxadvisory.example", "2025 tax intake: records list and how to deliver", CPA_SHEET, "2026-01-20T10:30:00-08:00")
    msg("m-brook-benefits", "brook-hr", "benefits@brooksystems.example", "Reminder: benefits enrollment closes Feb 15",
        "This is a reminder that the 2026 benefits enrollment window closes on February 15.", "2026-01-22T09:00:00-08:00")
    msg("m-atlas-w2", "atlas-w2", "payroll@atlaslabs.example", "Your 2025 Form W-2",
        "Your 2025 Form W-2 from Atlas Labs, Inc. is attached. Please keep it with your tax records.", "2026-01-27T08:15:00-08:00", attach=["D01-atlas-w2-2025.pdf"])
    msg("m-cedar-1099", "cedar-1099", "statements@cedarbank.example", "Your 2025 Form 1099-INT",
        "Your 2025 Form 1099-INT for your checking account ending 0937 is attached.", "2026-01-29T07:40:00-08:00", attach=["D09-cedar-1099-int-2025.pdf"])
    msg("m-northfield-schedule", "northfield-tax", "noreply@northfieldbrokerage.example", "Tax documents: what to expect",
        "Your 2025 consolidated Form 1099 is scheduled to be available by February 14, 2026. We will email you when it is ready.", "2026-01-30T06:00:00-08:00")
    msg("m-newsletter", "newsletter", "news@cityreader.example", "This week in the city",
        "Farmers market hours, a new bike lane and weekend events.", "2026-02-01T07:00:00-08:00")

    mail_seed = {"account_id": MAIL_ACCOUNT, "owner_person_id": "person-rowan", "address": ADDRESS, "messages": msgs}
    mdir = os.path.join(WS, "mail")
    write_json(os.path.join(mdir, "seed.json"), mail_seed)
    write_json(os.path.join(mdir, "dataset.json"), dataset("tax-packet-mail", "Rowan's mailbox before S1 for Task #102.", len(msgs), len(assets_)))
    write_json(os.path.join(mdir, "catalog.json"), {"schema_version": "pale.asset-catalog.v1", "catalog_id": "tax-packet-mail-assets", "app_id": "mail", "dataset_ref": "dataset.json", "assets": assets_, "extensions": []})
    write_json(os.path.join(mdir, "binding.json"), {"people": [{"person_id": "person-rowan", "name": "Rowan"}], "accounts": [{"app_id": "mail", "account_id": MAIL_ACCOUNT, "owner_person_id": "person-rowan"}], "objects": {}})
    os.makedirs(os.path.join(mdir, "assets"), exist_ok=True)
    for fname, data in mail_assets.items():
        with open(os.path.join(mdir, "assets", fname), "wb") as fh:
            fh.write(data)

    # ---------------- Mail: scheduled deliveries ----------------
    events = []

    def with_files(event_id, at, source_app, source_account, title, text, docs, session):
        files = []
        for name in docs:
            data = read_doc(name)
            files.append({"filename": name.split("-", 1)[1], "mime_type": "application/pdf",
                          "base64": base64.b64encode(data).decode(), "sha256": hashlib.sha256(data).hexdigest()})
        events.append({"session": session, "event": {
            "event_id": event_id, "at": at, "operation": "mail.receive_attachments",
            "payload": {"recipient_account_id": MAIL_ACCOUNT, "message": {
                "specversion": "1.0", "id": event_id, "source": f"urn:pale:app:{source_app}:account:{source_account}",
                "type": "org.pale.mail.attachments.v1", "time": at, "datacontenttype": "application/json",
                "dataschema": "urn:pale:email-attachments-payload:1",
                "data": {"channel": "channel.email.attachments", "recipient": {"kind": "person_ref", "id": "person-rowan"},
                         "source_object": {"app_id": source_app, "account_id": source_account, "object_type": "message", "object_id": event_id},
                         "content": {"title": title, "body": {"format": "text/plain", "text": text}, "attachments": files},
                         "extensions": []}}}}})

    def plain(event_id, at, sender, subject, body, session):
        events.append({"session": session, "event": {"event_id": event_id, "at": at, "operation": "mail.deliver", "payload": {
            "id": event_id, "thread_id": event_id, "account_id": MAIL_ACCOUNT, "from": sender, "to": [ADDRESS], "subject": subject,
            "body": body, "received_at": at, "folder": "inbox", "read": False, "attachments": []}}})

    with_files("ev-brook-w2", "2026-02-10T08:20:00-08:00", "brook-payroll", "brook-systems", "Your 2025 Form W-2",
               "Your 2025 Form W-2 from Brook Systems LLC is attached.", ["D02-brook-w2-2025.pdf"], "S2")
    with_files("ev-ridgeway-1099", "2026-02-12T06:30:00-08:00", "ridgeway-invest", "ridgeway-5160", "Your 2025 tax statement is ready",
               "Your 2025 Tax Statement for the account ending 5160 is attached, with supplemental information on your sales.",
               ["D07-ridgeway-1099-2025.pdf", "D08-ridgeway-1099-2025-supplement.pdf"], "S2")
    with_files("ev-northfield-1099", "2026-02-14T06:00:00-08:00", "northfield-brokerage", "northfield-2208", "Your 2025 consolidated Form 1099",
               "Your 2025 consolidated Form 1099 (statement NF-2025-2208-A) for the account ending 2208 is attached.", ["D03-northfield-1099-2025.pdf"], "S2")
    with_files("ev-northfield-export", "2026-02-16T20:05:00-08:00", "mail", "rowan-personal", "Northfield statement (downloaded)",
               "Downloaded this from the Northfield site too, in case the email copy is missing anything.", ["D04-northfield-1099-2025-export.pdf"], "S2")
    with_files("ev-northfield-corrected", "2026-03-02T06:00:00-08:00", "northfield-brokerage", "northfield-2208", "CORRECTED 2025 consolidated Form 1099",
               "A corrected 2025 consolidated Form 1099 (statement NF-2025-2208-B) is attached. It replaces your statement NF-2025-2208-A issued February 14, 2026 in full. "
               "Corrected items: 1099-DIV box 1a and the reported cost basis for two lots. Please use the corrected statement for your 2025 return.",
               ["D05-northfield-1099-2025-corrected.pdf"], "S3")
    plain("ev-bayview-notice", "2026-03-06T16:40:00-08:00", "notices@bayviewbank.example", "Your 2025 tax form",
          "Our records show interest was paid in 2025 on your savings account ending 4410, which you closed on August 29, 2025. "
          "Your 2025 Form 1099-INT will be available to download from the Documents page of your Bayview Bank online account on March 10, 2026.", "S4")
    with_files("ev-northfield-forward", "2026-03-06T17:50:00-08:00", "mail", "rowan-personal", "Fwd: Northfield tax statement",
               "Found this in my other inbox, forwarding in case you need it.", ["D06-northfield-1099-2025-forwarded.pdf"], "S4")
    write_json(os.path.join(mdir, "events.json"), events)

    # ---------------- Files ----------------
    files, fassets, fbytes = [], [], {}

    def folder(fid, name, parent, at):
        files.append({"id": fid, "account_id": FILES_ACCOUNT, "created_at": at, "updated_at": at, "history": [{"at": at, "action": "seeded"}],
                      "name": name, "parent_id": parent, "kind": "folder", "trashed": False, "versions": []})

    def file(fid, docname, parent, at, source):
        data = read_doc(docname)
        fname = docname.split("-", 1)[1]
        aid = f"asset-{fid}-v1"
        fassets.append(asset("files", FILES_ACCOUNT, "file", fid, aid, fname, data, "tax-packet-files"))
        fbytes[fname] = data
        files.append({"id": fid, "account_id": FILES_ACCOUNT, "created_at": at, "updated_at": at, "history": [{"at": at, "action": "seeded"}],
                      "name": fname, "parent_id": parent, "kind": "file", "trashed": False,
                      "versions": [{"number": 1, "asset_id": aid, "at": at, "source": source}]})

    folder("folder-taxes", "Taxes", None, "2025-02-20T09:00:00-08:00")
    folder("folder-2024", "2024 reference", "folder-taxes", "2025-02-20T09:00:00-08:00")
    folder("folder-2025", "2025 packet", "folder-taxes", "2026-01-20T11:00:00-08:00")
    file("file-nf-2024", "D11-northfield-1099-2024.pdf", "folder-2024", "2025-02-20T09:05:00-08:00", "Northfield Brokerage, issued 2025-02-14")
    file("file-organizer-2024", "D12-tax-organizer-2024.pdf", "folder-2024", "2025-03-03T12:00:00-08:00", "Morgan Lee Tax Advisory, sent 2025-03-03")
    fdir = os.path.join(WS, "files")
    write_json(os.path.join(fdir, "seed.json"), {"account_id": FILES_ACCOUNT, "owner_person_id": "person-rowan", "files": files})
    write_json(os.path.join(fdir, "dataset.json"), dataset("tax-packet-files", "Rowan's tax workspace before S1 for Task #102.", len(files), len(fassets)))
    write_json(os.path.join(fdir, "catalog.json"), {"schema_version": "pale.asset-catalog.v1", "catalog_id": "tax-packet-files-assets", "app_id": "files", "dataset_ref": "dataset.json", "assets": fassets, "extensions": []})
    write_json(os.path.join(fdir, "binding.json"), {"people": [{"person_id": "person-rowan", "name": "Rowan"}], "accounts": [{"app_id": "files", "account_id": FILES_ACCOUNT, "owner_person_id": "person-rowan"}], "objects": {}})
    os.makedirs(os.path.join(fdir, "assets"), exist_ok=True)
    for fname, data in fbytes.items():
        with open(os.path.join(fdir, "assets", fname), "wb") as fh:
            fh.write(data)
    print(f"mail: {len(msgs)} messages, {len(assets_)} attachments, {len(events)} scheduled deliveries; files: {len(files)} records, {len(fassets)} files")


if __name__ == "__main__":
    sys.exit(build())
