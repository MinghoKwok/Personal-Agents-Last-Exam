#!/usr/bin/env python3
"""Write the package manifest.json (LifePack 1.0) with SHA-256 for every delivered file."""
import hashlib
import json
import os

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"__pycache__", "node_modules", ".state"}


def files():
    out = {}
    for root, dirs, names in os.walk(PKG):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for n in sorted(names):
            rel = os.path.relpath(os.path.join(root, n), PKG).replace(os.sep, "/")
            if rel == "manifest.json" or n.endswith(".pyc"):
                continue
            with open(os.path.join(root, n), "rb") as fh:
                out[rel] = hashlib.sha256(fh.read()).hexdigest()
    return out


manifest = {
    "format": "lifepack",
    "format_version": "1.0",
    "package_id": "tax-packet",
    "package_version": "0.1.0-dev",
    "tasks": [{
        "id": "tax-packet", "path": "tasks/tax-packet/",
        "proposal_url": "https://github.com/MatrAIx-ai/Personal-Agents-Last-Exam/pull/102",
        "primary_domain": "Money & insurance", "secondary_domains": [],
        "dependencies": ["pale-runtime", "app-mail", "app-files", "app-cpa-portal", "app-issuer-docs"],
    }],
    "dependencies": [
        {"id": "pale-runtime", "kind": "runtime", "version": "1.6.0 (Core API 1.2.0)", "revision": "upstream main 7a05aa9", "source": "runtime/"},
        {"id": "app-mail", "kind": "app", "version": "1.3.0", "source": "examples/apps/mail"},
        {"id": "app-files", "kind": "app", "version": "1.0.0", "source": "apps/files"},
        {"id": "app-cpa-portal", "kind": "app", "version": "0.1.0", "source": "tasks/tax-packet/environment/apps/cpa-portal"},
        {"id": "app-issuer-docs", "kind": "app", "version": "0.1.0", "source": "tasks/tax-packet/environment/apps/issuer-docs"},
        {"id": "harbor", "kind": "framework", "version": "TBD: pinned when the shared LifePack loader is released (#135)", "source": "https://docs.harborframework.com"},
    ],
    "files": files(),
    "artifacts": [],
}
with open(os.path.join(PKG, "manifest.json"), "w") as fh:
    json.dump(manifest, fh, indent=2)
    fh.write("\n")
print(f"manifest.json: {len(manifest['files'])} files")
