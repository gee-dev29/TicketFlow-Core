import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from request import SupportRequestSystem


class SupportRequestSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.system = SupportRequestSystem()

    def add_request(
        self,
        request_id: str,
        name: str = "Morgan Lee",
        *,
        urgent: bool = False,
        created_at: str = "2025-03-10T09:00:00+00:00",
    ) -> dict:
        return self.system.addRequest(
            request_id,
            {"name": name, "email": f"{request_id.lower()}@example.com"},
            f"Subject {request_id}",
            f"Description {request_id}",
            urgent=urgent,
            created_at=created_at,
        )

    def test_add_request_normalizes_fields_and_sets_priority(self) -> None:
        request = self.system.addRequest(
            " REQ-1 ",
            {"name": " Morgan Lee ", "email": "morgan@example.com"},
            " Password help ",
            " Reset link does not work ",
            urgent=True,
            created_at="2025-03-10T09:00:00",
        )

        self.assertEqual(request["request_id"], "REQ-1")
        self.assertEqual(request["customer"]["name"], " Morgan Lee ")
        self.assertEqual(request["subject"], "Password help")
        self.assertEqual(request["priority"], "high")
        self.assertEqual(request["status"], "open")
        self.assertEqual(request["created_at"].tzinfo, timezone.utc)
        self.assertEqual(self.system.processing_queue[0], "REQ-1")

    def test_add_request_rejects_duplicate_id_and_empty_fields(self) -> None:
        self.add_request("REQ-1")

        with self.assertRaisesRegex(ValueError, "already exists"):
            self.add_request("REQ-1")
        with self.assertRaisesRegex(ValueError, "subject cannot be empty"):
            self.system.addRequest("REQ-2", {"name": "Morgan"}, " ", "Details")

        self.assertEqual(list(self.system.requests), ["REQ-1"])

    def test_processing_is_fifo_and_skips_non_open_requests(self) -> None:
        self.add_request("REQ-1")
        self.add_request("REQ-2")
        self.system.updateRequest("REQ-1", status="resolved")

        processed = self.system.processNext()

        self.assertEqual(processed["request_id"], "REQ-2")
        self.assertEqual(self.system.searchById("REQ-2")["status"], "in_progress")
        self.assertIsNone(self.system.processNext())

    def test_update_can_be_undone_with_queue_state(self) -> None:
        self.add_request("REQ-1")
        self.add_request("REQ-2")
        self.system.updateRequest("REQ-1", status="resolved")

        restored = self.system.undoLastUpdate()

        self.assertEqual(restored["status"], "open")
        self.assertEqual(list(self.system.processing_queue), ["REQ-1", "REQ-2"])
        self.assertIsNone(self.system.undoLastUpdate())

    def test_search_by_id_and_case_insensitive_customer_name(self) -> None:
        self.add_request("REQ-1", "Morgan Lee")
        self.add_request("REQ-2", "Morgan Lee")
        self.add_request("REQ-3", "Riley Park")

        self.assertEqual(self.system.searchById("REQ-1")["request_id"], "REQ-1")
        self.assertIsNone(self.system.searchById("missing"))
        self.assertEqual(
            [request["request_id"] for request in self.system.searchByCustomerName(" mOrGaN lEe ")],
            ["REQ-1", "REQ-2"],
        )

    def test_both_sorting_algorithms_return_ordered_copies(self) -> None:
        self.add_request("REQ-2", urgent=False, created_at="2025-03-11T09:00:00+00:00")
        self.add_request("REQ-1", urgent=True, created_at="2025-03-10T09:00:00+00:00")
        original_order = list(self.system.requests)

        for algorithm in ("built-in", "insertion"):
            with self.subTest(algorithm=algorithm):
                sorted_requests = self.system.sortRequests("priority", algorithm)
                self.assertEqual(
                    [request["request_id"] for request in sorted_requests],
                    ["REQ-1", "REQ-2"],
                )
                self.assertEqual(list(self.system.requests), original_order)

    def test_sort_rejects_unknown_field_or_algorithm(self) -> None:
        self.add_request("REQ-1")

        with self.assertRaisesRegex(ValueError, "sort_by"):
            self.system.sortRequests("customer")
        with self.assertRaisesRegex(ValueError, "algorithm"):
            self.system.sortRequests("date", "unknown")

    def test_replies_are_validated_and_displayed_in_arrival_order(self) -> None:
        self.add_request("REQ-1")
        self.system.addReply("REQ-1", " We are looking into this. ", " Agent ")
        self.system.addReply("REQ-1", " The issue is resolved. ")

        replies = self.system.searchById("REQ-1")["replies"]
        displayed = self.system.displayReplies("REQ-1")

        self.assertEqual([reply["author"] for reply in replies], ["Agent", "Support"])
        self.assertIn("Agent: We are looking into this.", displayed)
        self.assertLess(displayed.index("looking into this"), displayed.index("issue is resolved"))
        self.assertTrue(all(isinstance(reply["created_at"], datetime) for reply in replies))
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            self.system.addReply("REQ-1", " ")

    def test_sample_data_can_be_added_using_request_api(self) -> None:
        sample_path = Path(__file__).parents[1] / "data" / "sample_requests.json"
        sample_requests = json.loads(sample_path.read_text(encoding="utf-8"))

        for request in sample_requests:
            self.system.addRequest(**request)

        self.assertEqual(len(self.system.requests), 3)
        self.assertEqual(self.system.searchById("REQ-1001")["priority"], "high")
        self.assertEqual(len(self.system.searchByCustomerName("Avery Chen")), 2)


if __name__ == "__main__":
    unittest.main()
