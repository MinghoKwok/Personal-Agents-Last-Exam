"""Recovery regressions for delayed commands and interrupted GitHub calls."""
import copy
from datetime import datetime, timezone
from email.message import Message
from http.client import RemoteDisconnected
from io import BytesIO
import json
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from scripts import proposal_lifecycle as life
from scripts import sync_proposals as sync
from test_proposal_lifecycle import pr, files, initial, approved, submitted, accepted, apply, HEAD, NEXT, BLOB, PATH, RULES


def comment(n, body, actor="Jasonya"):
    return {"id": n, "body": body, "user": {"login": actor},
            "created_at": f"2026-11-20T00:00:{n:02d}Z", "updated_at": f"2026-11-20T00:00:{n:02d}Z"}


class MemoryAPI:
    repository = "example/repo"

    def __init__(self, comments, head=HEAD):
        self.pr = pr(head={"sha": head})
        self.comments = copy.deepcopy(comments)
        self.writes = []
        self.old_blob = BLOB
        self.ancestry = "ahead"
        self.permission = "read"

    def pages(self, path, **kwargs):
        if path.endswith("/pulls"):return [copy.deepcopy(self.pr)]
        if path.endswith("/files"):return files(True)
        if path.endswith("/comments"):return copy.deepcopy(self.comments)
        if path.endswith("/timeline"):return [{"event": "review_requested", "requested_reviewer": {"login": "Jasonya"}}]
        raise AssertionError(path)

    def contents(self, path, ref):
        return {"sha": BLOB if ref == self.pr["head"]["sha"] else self.old_blob, "encoding": "base64", "content": ""}

    def request(self, path, method="GET", data=None):
        if method != "GET": self.writes.append((path, method, data))
        if "/issues/comments/" in path:
            c = next(c for c in self.comments if c["id"] == int(path.rsplit("/", 1)[1]))
            if method == "PATCH":c["body"] = data["body"]
            return copy.deepcopy(c)
        if path.endswith("/pulls/123"):return copy.deepcopy(self.pr)
        if path.endswith("/permission"):return {"permission": self.permission}
        if "/compare/" in path:return {"status": self.ancestry}
        if path.endswith("/comments") and method == "POST":
            c = {"id": 1000 + len(self.comments), "body": data["body"],
                 "user": {"login": "github-actions[bot]"}, "performed_via_github_app": {"id": 15368},
                 "created_at": "2026-11-21T00:00:00Z", "updated_at": "2026-11-21T00:00:00Z"}
            self.comments.append(c);return copy.deepcopy(c)
        if path.endswith("/labels") and method == "POST":
            self.pr["labels"] += [{"name": x} for x in data["labels"]]
        if "/labels/" in path and method == "DELETE":
            self.pr["labels"] = [x for x in self.pr["labels"] if x["name"] != path.rsplit("/", 1)[1]]
        if path.endswith("/status"):return {"statuses": []}
        if "/check-runs?" in path:return {"check_runs": []}
        return {}

    def state(self):
        return life.load_state(self.comments, 123)[0]


class RecoveryTests(unittest.TestCase):
    def runner(self, api):
        return life.Lifecycle(api, RULES, datetime(2026, 11, 21, tzinfo=timezone.utc))

    def test_batch_approval_then_submission_and_duplicate_approval_preserves_validation(self):
        api = MemoryAPI([comment(3, "/approve-plan " + NEXT),
                         comment(1, "/approve-plan " + HEAD),
                         comment(2, "/submit-implementation " + NEXT + " https://example.org/run", "author")], NEXT)
        self.runner(api).reconcile({123})
        state = api.state()
        self.assertEqual(state["processed"], [1, 2, 3])
        self.assertEqual(state["stage"], "validation")
        self.assertEqual(state["approval"]["head_sha"], HEAD)
        self.assertEqual(state["first_approved_at"], "2026-11-20T00:00:01Z")
        self.assertEqual(state["environment_v1_due_at"], "2026-12-04T00:00:01Z")
        self.assertNotIn("acceptance", state)
        self.assertEqual(len([c for c in api.comments if c['body'].startswith(life.MARKER)]), 1)
        self.runner(api).reconcile({123})
        self.assertEqual(api.state(), state)

    def test_old_approve_cannot_override_later_revoke_in_batch(self):
        api = MemoryAPI([comment(2, "/revoke-plan Scope changed"), comment(1, "/approve-plan " + HEAD)])
        self.runner(api).reconcile({123})
        self.assertEqual(api.state()["stage"], "plan-needs-review")
        self.assertNotIn("approval", api.state())

    def test_older_missing_command_cannot_undo_already_processed_revoke(self):
        api = MemoryAPI([comment(1, "/approve-plan " + HEAD), comment(2, "/revoke-plan Changed")])
        state = {**initial(), "processed": [2], "stage": "plan-needs-review", "track": "environment"}
        api.request("/issues/123/comments", "POST", {"body": life.render_state(state, self.runner(api).now)})
        self.runner(api).reconcile({123})
        self.assertNotIn("approval", api.state())

    def test_legacy_rejection_recovery_requires_explicit_flag_and_revalidates(self):
        api = MemoryAPI([comment(1, "/approve-plan " + HEAD),
                         comment(2, "/submit-implementation " + NEXT + " https://example.org/run", "author")], NEXT)
        api.request("/issues/123/comments", "POST", {"body": "<!-- pale-command-result:1 -->\nCommand not applied: Use the full current 40-character PR commit SHA"})
        self.runner(api).reconcile({123})
        self.assertNotIn("approval", api.state())
        self.runner(api).reconcile({123}, recover_rejected=True)
        self.assertEqual(api.state()["stage"], "validation")
        self.assertTrue(any("Recovered after" in c['body'] for c in api.comments))

    def test_changed_proposal_or_unrelated_commit_never_inherits_approval(self):
        for option in ["changed", "unrelated", "no-permission"]:
            api = MemoryAPI([comment(1, "/approve-plan " + HEAD)], NEXT)
            if option == "changed":api.old_blob = "different"
            if option == "unrelated":api.ancestry = "diverged"
            if option == "no-permission":api.permission = "none"
            self.runner(api).reconcile({123})
            self.assertNotIn("approval", api.state(), option)

    def test_duplicate_start_does_not_revoke_final_acceptance(self):
        before = accepted()
        after, _ = apply(before, "start-implementation", "", comment_id=20)
        self.assertEqual(after["acceptance"], before["acceptance"])
        self.assertEqual(after["stage"], "ready-to-merge")

    def test_final_acceptance_still_rejects_old_sha(self):
        with self.assertRaises(ValueError):
            apply(submitted(), "accept-implementation", NEXT + " https://example.org/run", maintainer=True, comment_id=4)

    def test_scope_change_during_processing_stops_authority_write(self):
        api = MemoryAPI([comment(1, "/approve-plan " + HEAD)])
        runner = self.runner(api); context = runner.context(copy.deepcopy(api.pr))
        api.pr["head"]["sha"] = NEXT
        with self.assertRaises(RuntimeError):
            runner.command({"issue": {"number":123}, "comment":api.comments[0]}, context)
        self.assertNotIn("approval", api.state())


class RequestTests(unittest.TestCase):
    def response(self):
        response = Mock(status=200)
        response.read.return_value = b'{"ok":true}'
        response.__enter__ = Mock(return_value=response);response.__exit__ = Mock(return_value=False)
        return response

    def test_read_disconnect_is_retried_but_post_is_not_duplicated(self):
        api = sync.GitHub("example/repo", None)
        with patch.object(sync, "urlopen", side_effect=[RemoteDisconnected(), self.response()]) as call, patch.object(sync.time, "sleep"):
            self.assertEqual(api.request("/x"), {"ok": True});self.assertEqual(call.call_count, 2)
        with patch.object(sync, "urlopen", side_effect=RemoteDisconnected()) as call, patch.object(sync.time, "sleep"):
            with self.assertRaises(sync.APIError):api.request("/x", "POST", {})
            self.assertEqual(call.call_count, 1)

    def test_retry_after_is_respected_and_permission_403_is_not_retried(self):
        api = sync.GitHub("example/repo", None); h = Message();h['retry-after'] = '2'
        limited = HTTPError('https://api.github.com/x', 429, 'Limited', h, BytesIO(b'{}'))
        with patch.object(sync, "urlopen", side_effect=[limited, self.response()]), patch.object(sync.time, "sleep") as sleep:
            self.assertEqual(api.request('/x'), {'ok': True});sleep.assert_called_once_with(2)
        denied = HTTPError('https://api.github.com/x', 403, 'Forbidden', Message(), BytesIO(b'{}'))
        with patch.object(sync, "urlopen", side_effect=denied) as call:
            with self.assertRaises(sync.APIError):api.request('/x')
            self.assertEqual(call.call_count, 1)

    def test_long_quota_reset_fails_explicitly_without_unbounded_sleep(self):
        h = Message();h['x-ratelimit-remaining'] = '0';h['x-ratelimit-reset'] = '1000'
        error = HTTPError('https://api.github.com/x', 403, 'Limited', h, BytesIO(b'{}'))
        with patch.object(sync, 'urlopen', side_effect=error), patch.object(sync.time, 'time', return_value=100), patch.object(sync.time, 'sleep') as sleep:
            with self.assertRaises(sync.RateLimited):sync.GitHub('example/repo', None).request('/x')
            sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
