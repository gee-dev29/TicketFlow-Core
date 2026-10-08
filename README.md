# Ticket Flow Core

A standard-library Python command-line program for managing customer support
requests. It supports adding and updating requests, processing open requests in
FIFO order, undoing the last update, searching, sorting, and recording replies.

## Requirements

- Python 3.10 or newer
- No third-party packages

## Set up and run

Clone the repository and change into its directory:

```bash
git clone https://github.com/gee-dev29/TicketFlow-Core.git
cd TicketFlow-Core
```

Start the interactive menu:

```bash
python request.py
```

The menu keeps requests in memory for the duration of the program. Select `0`
to exit. The sample data in [`data/sample_requests.json`](data/sample_requests.json)
is not loaded automatically. To load it into a system instance from Python:

```python
import json
from pathlib import Path

from request import SupportRequestSystem

system = SupportRequestSystem()
sample_path = Path("data/sample_requests.json")
for request in json.loads(sample_path.read_text(encoding="utf-8")):
    system.addRequest(**request)
```

## Tests

Run the automated tests with Python's built-in test runner:

```bash
python -m unittest discover -s tests -v
```

The tests cover request creation and validation, status updates and undo,
FIFO processing, ID and customer-name searches, both sorting algorithms,
reply creation/display, and compatibility of the sample data with the
request-creation API.

## Data structures

| Feature | Data structure | Why it was selected |
| --- | --- | --- |
| Requests keyed by ID | Dictionary (`dict`) | Direct lookup by request ID is average O(1), and insertion order supports listing requests in their original order. |
| Duplicate-ID tracking | Set (`set`) | Average O(1) membership checks prevent adding an ID twice. |
| Requests waiting to be processed | Double-ended queue (`deque`) | Efficient append and removal from the front support FIFO processing. |
| Undo history | Stack (`list`) of request and queue snapshots | Last-in, first-out history makes the most recent update the natural operation to undo. |
| Replies for a request | List (`list`) | Replies remain in the order received and can be traversed in sequence. |
| Sorted search results | List (`list`) | Sorting operates on a copy, so callers can order results without changing the manager's stored order. |

## Searching and sorting

Searching by request ID uses the request dictionary and takes average O(1)
time. Searching by customer name compares normalized names in sequence, so it
takes O(n) time for n requests; it returns exact, case-insensitive matches.

The built-in sorting option uses Python's stable Timsort, with O(n log n)
worst-case time and O(n) auxiliary space. The insertion-sort option is
implemented directly to demonstrate the algorithm: it uses O(n²) worst-case
time, but O(n) time when the input is already sorted, and O(1) auxiliary space.
Both options order a copy when called through `SupportRequestSystem`.

## Limitations and possible improvements

- Requests and undo history are stored only in memory and are lost on exit.
  Persistent JSON or database storage would allow work to continue between runs.
- The command-line interface is intentionally small: it has no authentication,
  input masking, or rich error recovery.
- Name search supports exact matches only. Partial, email, or indexed search
  could improve finding requests as the dataset grows.
- Undo history has no size limit, so long-running sessions may retain many
  snapshots. A configurable history limit or event-based undo could reduce
  memory use.
- Recursive reply display can exceed Python's recursion limit for an unusually
  large reply list; an iterative traversal would remove that limit.

## Commit messages

Use concise, imperative messages that describe the change, for example:

```text
Add support request search and sorting
Document setup and add sample support requests
Test request lifecycle and queue operations
```

The repository currently has an initial commit; these examples are conventions
for future changes, not a claim that additional commits have already been made.
