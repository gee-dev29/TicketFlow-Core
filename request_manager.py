"""Support request system with FIFO processing and undo history."""
from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, TextIO

from requestReplies import createReply, displayReplies
from requestSorting import sortRequests


class SupportRequestSystem:
    """Manage customer requests, FIFO processing, and undo history.

    Requests and the processing queue use O(n) bookkeeping space, in addition
    to customer and reply data. Undo history uses space proportional to the
    request snapshots that have been saved.
    """

    def __init__(self) -> None:
        self.requests: dict[str, dict[str, Any]] = {}
        self.request_ids: set[str] = set()
        self.processing_queue: deque[str] = deque()
        self.undo_stack: list[tuple[str, dict[str, Any], list[str]]] = []

    @staticmethod
    def _normaliseDate(value: datetime | str | None) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError as error:
                raise ValueError("created_at must be a valid ISO date/time") from error
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _validatePriority(value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("priority must be 'high', 'normal', or 'low'")
        priority = value.strip().casefold()
        if priority not in {"high", "normal", "low"}:
            raise ValueError("priority must be 'high', 'normal', or 'low'")
        return priority

    @staticmethod
    def _copyCustomer(customer: object) -> dict[str, Any]:
        if (
            not isinstance(customer, Mapping)
            or not isinstance(customer.get("name"), str)
            or not customer["name"].strip()
        ):
            raise ValueError("customer must be a dictionary with a non-empty 'name'")
        return deepcopy(dict(customer))

    @staticmethod
    def _validateUrgent(value: object) -> bool:
        if not isinstance(value, bool):
            raise ValueError("urgent must be a boolean")
        return value

    def _saveUndoState(self, request_id: str) -> None:
        self.undo_stack.append(
            (
                request_id,
                deepcopy(self.requests[request_id]),
                list(self.processing_queue),
            )
        )

    def addRequest(
        self,
        request_id: str,
        customer: Mapping[str, Any],
        subject: str,
        description: str,
        urgent: bool = False,
        created_at: datetime | str | None = None,
    ) -> dict[str, Any]:
        # Add a request and its customer details, rejecting duplicate IDs
        request_id = request_id.strip()
        if not request_id:
            raise ValueError("request_id cannot be empty")
        if request_id in self.request_ids:
            raise ValueError(f"request ID {request_id!r} already exists")
        if not subject.strip():
            raise ValueError("subject cannot be empty")
        if not description.strip():
            raise ValueError("description cannot be empty")

        request = {
            "request_id": request_id,
            "customer": self._copyCustomer(customer),
            "subject": subject.strip(),
            "description": description.strip(),
            "status": "open",
            "priority": "high" if self._validateUrgent(urgent) else "normal",
            "created_at": self._normaliseDate(created_at),
            "replies": [],
        }
        self.requests[request_id] = request
        self.request_ids.add(request_id)
        self.processing_queue.append(request_id)
        return deepcopy(request)

    def updateRequest(self, request_id: str, **changes: Any) -> dict[str, Any]:
        # Update supported request fields and record the previous state
        if request_id not in self.request_ids:
            raise KeyError(f"request ID {request_id!r} was not found")
        if not changes:
            raise ValueError("provide at least one field to update")

        updates = dict(changes)
        if "urgent" in updates:
            urgent = updates.pop("urgent")
            if not isinstance(urgent, bool):
                raise ValueError("urgent must be a boolean")
            if urgent:
                updates["priority"] = "high"
            elif (
                updates.get("priority") == "high"
                or self.requests[request_id]["priority"] == "high"
            ):
                updates["priority"] = "normal"

        allowed_fields = {
            "customer",
            "subject",
            "description",
            "status",
            "priority",
            "created_at",
            "replies",
        }
        invalid_fields = updates.keys() - allowed_fields
        if invalid_fields:
            fields = ", ".join(sorted(invalid_fields))
            raise ValueError(f"unsupported request field(s): {fields}")

        if "status" in updates:
            if not isinstance(updates["status"], str):
                raise ValueError("status must be open, in_progress, resolved, or closed")
            status = updates["status"].strip().casefold()
            if status not in {"open", "in_progress", "resolved", "closed"}:
                raise ValueError("status must be open, in_progress, resolved, or closed")
            updates["status"] = status
        if "priority" in updates:
            updates["priority"] = self._validatePriority(updates["priority"])
        if "customer" in updates:
            updates["customer"] = self._copyCustomer(updates["customer"])
        for field in ("subject", "description"):
            if field in updates:
                if not isinstance(updates[field], str) or not updates[field].strip():
                    raise ValueError(f"{field} cannot be empty")
                updates[field] = updates[field].strip()
        if "created_at" in updates:
            updates["created_at"] = self._normaliseDate(updates["created_at"])
        if "replies" in updates:
            if not isinstance(updates["replies"], list):
                raise ValueError("replies must be a list")
            updates["replies"] = deepcopy(updates["replies"])

        self._saveUndoState(request_id)
        self.requests[request_id].update(updates)
        self._updateQueueForStatus(request_id, updates)
        return deepcopy(self.requests[request_id])

    def _updateQueueForStatus(
        self, request_id: str, updates: dict[str, Any]
    ) -> None:
        """Keep only open requests waiting in the FIFO queue."""
        if "status" not in updates:
            return
        if updates["status"] == "open":
            if request_id not in self.processing_queue:
                self.processing_queue.append(request_id)
        elif request_id in self.processing_queue:
            self.processing_queue.remove(request_id)

    def processNext(self) -> dict[str, Any] | None:
        """Start the oldest open request in the FIFO queue."""
        while self.processing_queue:
            request_id = self.processing_queue[0]
            request = self.requests[request_id]
            if request["status"] != "open":
                self.processing_queue.popleft()
                continue
            self._saveUndoState(request_id)
            self.processing_queue.popleft()
            request["status"] = "in_progress"
            return deepcopy(request)
        return None

    def undoLastUpdate(self) -> dict[str, Any] | None:
        """Restore the request and queue state from the most recent update."""
        if not self.undo_stack:
            return None
        request_id, previous_request, previous_queue = self.undo_stack.pop()
        self.requests[request_id] = previous_request
        self.processing_queue = deque(previous_queue)
        return deepcopy(previous_request)

    def searchById(self, request_id: str) -> dict[str, Any] | None:
        """Look up a request by its unique ID in average O(1) time."""
        request = self.requests.get(request_id)
        return deepcopy(request) if request is not None else None

    def searchByCustomerName(self, name: str) -> list[dict[str, Any]]:
        """Find exact, case-insensitive customer-name matches in O(n) time."""
        target = name.strip().casefold()
        return [
            deepcopy(request)
            for request in self.requests.values()
            if request["customer"]["name"].strip().casefold() == target
        ]

    def sortRequests(
        self, sort_by: str = "date", algorithm: str = "built-in"
    ) -> list[dict[str, Any]]:
        """Return a sorted copy using the selected sorting algorithm."""
        requests = [deepcopy(request) for request in self.requests.values()]
        return sortRequests(requests, sort_by, algorithm)

    def addReply(
        self, request_id: str, text: str, author: str = "Support"
    ) -> dict[str, Any]:
        """Append a reply while preserving its arrival order and undo history."""
        if request_id not in self.request_ids:
            raise KeyError(f"request ID {request_id!r} was not found")
        replies = deepcopy(self.requests[request_id]["replies"])
        replies.append(createReply(text, author))
        return self.updateRequest(request_id, replies=replies)

    def displayReplies(self, request_id: str, output: TextIO | None = None) -> str:
        """Display replies recursively in the order they were received."""
        request = self.searchById(request_id)
        if request is None:
            raise KeyError(f"request ID {request_id!r} was not found")
        return displayReplies(request["replies"], output)
