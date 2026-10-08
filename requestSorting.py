"""Sorting helpers for support requests."""

from __future__ import annotations

from typing import Any


def _sortKey(request: dict[str, Any], sort_by: str) -> Any:
    """Return the value used to sort one request."""
    if sort_by == "date":
        return request["created_at"]
    if sort_by == "priority":
        return {"high": 0, "normal": 1, "low": 2}[request["priority"]]
    if sort_by == "status":
        return request["status"]
    raise ValueError("sort_by must be 'date', 'priority', or 'status'")


def sortRequests(
    requests: list[dict[str, Any]],
    sort_by: str = "date",
    algorithm: str = "built-in",
) -> list[dict[str, Any]]:
    """Sort copied requests with the built-in sort or insertion sort.

    Built-in sorting takes O(n log n) comparisons. Insertion sort takes
    O(n**2) comparisons in the worst case and O(n) when the input is sorted.
    """
    sort_by = sort_by.strip().casefold()
    algorithm = algorithm.strip().casefold()
    if sort_by not in {"date", "priority", "status"}:
        raise ValueError("sort_by must be 'date', 'priority', or 'status'")

    if algorithm == "built-in":
        return sorted(requests, key=lambda request: _sortKey(request, sort_by))
    if algorithm != "insertion":
        raise ValueError("algorithm must be 'built-in' or 'insertion'")

    for index in range(1, len(requests)):
        current = requests[index]
        current_key = _sortKey(current, sort_by)
        previous = index - 1
        while previous >= 0 and _sortKey(requests[previous], sort_by) > current_key:
            requests[previous + 1] = requests[previous]
            previous -= 1
        requests[previous + 1] = current
    return requests
