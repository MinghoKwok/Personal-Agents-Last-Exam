"""Live review synchronization without fork workflows or stale metadata caches."""
import copy
import unittest
from unittest.mock import Mock, patch

from scripts import sync_proposals as sync
from test_sync_proposals import FakeAPI, ROOT, pr, review


def node(p, rows=None, more=False):
    return {"id": p["node_id"], "number": p["number"], "reviews": {
        "nodes": rows or [], "pageInfo": {"hasNextPage": more}}}


def graphql_review(state="APPROVED", **extra):
    return {"databaseId": 100, "state": state, "submittedAt": "2026-11-24T12:00:00Z",
            "updatedAt": "2026-11-24T12:00:00Z", "author": {"login": "reviewer", "__typename": "User"}, **extra}


class BulkAPI(FakeAPI):
    def __init__(self):
        super().__init__(pr(node_id="PR_42", head={"sha": "head"}, updated_at="2026-11-24T12:00:00Z"),
                         "- **Primary domain:** Travel & commuting\n- **Short task title:** Example")
        self.graphql_rows = []

    def request(self, path, method="GET", data=None):
        self.calls.append((path, method, data))
        assert path == "/graphql" and method == "POST"
        assert data["variables"]["ids"] == ["PR_42"]
        return {"data": {"nodes": [node(self.pr, copy.deepcopy(self.graphql_rows))]}}


class ReviewPollingTests(unittest.TestCase):
    def test_review_changes_invalidate_cache_without_pr_timestamp_or_head_changes(self):
        api = BulkAPI()
        domains = sync.domains_from_readme((ROOT / "README.md").read_text())
        cache = {}
        self.assertEqual(sync.collect(api, domains, "main", cache, now=100)[0]["review"], "Awaiting review")
        for state, expected in [("APPROVED", "Approved (1)"), ("CHANGES_REQUESTED", "Changes requested (1)"),
                                ("DISMISSED", "Awaiting review"), ("COMMENTED", "Commented")]:
            api.graphql_rows = [graphql_review(state)]
            self.assertEqual(sync.collect(api, domains, "main", cache, now=101)[0]["review"], expected)
        api.calls.clear()
        sync.collect(api, domains, "main", cache, now=102)
        self.assertEqual([c[0] for c in api.calls], ["/repos/example/benchmark/pulls", "/graphql"])

    def test_review_edit_changes_fingerprint_even_when_state_is_unchanged(self):
        api = BulkAPI(); api.graphql_rows = [graphql_review()]
        first = sync.open_review_snapshots(api, [api.pr])[42]
        api.graphql_rows[0]["updatedAt"] = "2026-11-24T13:00:00Z"
        second = sync.open_review_snapshots(api, [api.pr])[42]
        self.assertNotEqual(sync.cache_key(api.pr, first), sync.cache_key(api.pr, second))

    def test_open_prs_are_batched_and_closed_reviews_stay_out_of_poll(self):
        pulls = [pr(number=n, node_id=f"PR_{n}") for n in range(101)]
        pulls.append(pr(number=200, node_id="PR_200", state="closed"))
        api = Mock(repository="example/repo")
        by_id = {p["node_id"]: p for p in pulls}
        api.request.side_effect = lambda path, method, data: {"data": {"nodes": [
            node(by_id[i]) for i in data["variables"]["ids"]]}}
        self.assertEqual(len(sync.open_review_snapshots(api, pulls)), 101)
        self.assertEqual(api.request.call_count, 3)
        api.pages.assert_not_called()

    def test_overflow_uses_all_rest_pages_instead_of_truncating_reviews(self):
        p = pr(node_id="PR_42"); api = Mock(repository="example/repo")
        api.request.return_value = {"data": {"nodes": [node(p, more=True)]}}
        api.pages.return_value = [{**review("APPROVED", n), "submitted_at": "2026-11-24T12:00:00Z"}
                                 for n in range(101)] + [{**review("CHANGES_REQUESTED", 102), "submitted_at": "2026-11-24T13:00:00Z"}]
        rows = sync.open_review_snapshots(api, [p])[42]
        self.assertEqual(len(rows), 102)
        self.assertEqual(sync.review_state(rows, p), ("Changes requested (1)", True))

    def test_partial_or_mismatched_graphql_result_never_becomes_empty_review_state(self):
        api = BulkAPI(); cache = {"42": {"key": ["old"], "record": {"review": "Approved (1)"}}}
        domains = sync.domains_from_readme((ROOT / "README.md").read_text())
        for result in [{"data": {"nodes": []}}, {"data": {"nodes": [None]}},
                       {"data": {"nodes": [node(api.pr)]}, "errors": [{"type": "FORBIDDEN"}]},
                       {"data": {"nodes": [node({**api.pr, "node_id": "wrong"})]}}]:
            before = copy.deepcopy(cache)
            with patch.object(api, "request", return_value=result):
                with self.assertRaises(ValueError): sync.collect(api, domains, "main", cache)
            self.assertEqual(cache, before)

    def test_read_only_graphql_retries_server_error_but_not_permissions(self):
        api = BulkAPI()
        result = {"data": {"nodes": [node(api.pr)]}}
        with patch.object(api, "request", side_effect=[sync.APIError(500, "server error"), result]) as call, \
                patch.object(sync.time, "sleep"):
            self.assertEqual(sync.open_review_snapshots(api, [api.pr]), {42: []})
            self.assertEqual(call.call_count, 2)
        with patch.object(api, "request", side_effect=sync.APIError(403, "forbidden")) as call:
            with self.assertRaises(sync.APIError): sync.open_review_snapshots(api, [api.pr])
            self.assertEqual(call.call_count, 1)

    def test_bot_reviews_do_not_approve_or_complete_human_review(self):
        for user in [{"login": "Copilot"}, {"login": "copilot-pull-request-reviewer"},
                     {"login": "chatgpt-codex-connector"}, {"login": "custom-app", "type": "Bot"},
                     {"login": "other[bot]"}]:
            p = pr(requested_reviewers=[user])
            for state in ["APPROVED", "CHANGES_REQUESTED", "COMMENTED"]:
                rows = [{**review(state, 1), "user": user}]
                self.assertEqual(sync.review_state(rows, p), ("Awaiting review", False))
            self.assertEqual(sync.review_state(rows + [review("APPROVED", 2)], p), ("Approved (1)", False))

    def test_deleted_reviewer_and_unsubmitted_reviews_are_not_approvals(self):
        api = BulkAPI(); api.graphql_rows = [graphql_review(author=None), graphql_review("PENDING")]
        rows = sync.open_review_snapshots(api, [api.pr])[42]
        self.assertEqual(sync.review_state(rows, api.pr), ("Awaiting review", False))
        self.assertIsNotNone(sync.cache_key(api.pr, rows))


if __name__ == "__main__":
    unittest.main()
