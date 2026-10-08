"""Interactive command-line menu for the support request system."""

from request_manager import SupportRequestSystem


def runCli() -> None:
    """Run a small interactive interface for managing requests."""
    system = SupportRequestSystem()
    menu = (
        "\n1 Add request | 2 Process next | 3 Update | 4 Undo | "
        "5 Search | 6 Sort | 7 Add reply | 8 Show replies | 9 List all | 0 Exit"
    )

    while True:
        print(menu)
        choice = input("Choose an action: ").strip()
        try:
            if choice == "0":
                return
            if choice == "1":
                request = system.addRequest(
                    input("Request ID: "),
                    {
                        "name": input("Customer name: ").strip(),
                        "email": input("Customer email: ").strip(),
                    },
                    input("Subject: "),
                    input("Description: "),
                    urgent=input("Urgent? (y/N): ").strip().casefold() == "y",
                )
                print(f"Added {request['request_id']} ({request['priority']} priority).")
            elif choice == "2":
                request = system.processNext()
                print(request if request else "No open requests are waiting.")
            elif choice == "3":
                request_id = input("Request ID: ").strip()
                field = input("Field (status, priority, subject, description): ").strip()
                if field not in {"status", "priority", "subject", "description"}:
                    print("Unsupported field.")
                    continue
                system.updateRequest(request_id, **{field: input(f"New {field}: ")})
                print(f"Updated {request_id}.")
            elif choice == "4":
                request = system.undoLastUpdate()
                print(request if request else "There is no update to undo.")
            elif choice == "5":
                _searchRequests(system)
            elif choice == "6":
                field = input("Sort by (date/priority/status): ")
                algorithm = input("Algorithm (built-in/insertion): ").strip() or "built-in"
                print(system.sortRequests(field, algorithm))
            elif choice == "7":
                request_id = input("Request ID: ").strip()
                text = input("Reply: ")
                author = input("Author (default Support): ").strip() or "Support"
                system.addReply(request_id, text, author)
                print("Reply added.")
            elif choice == "8":
                request_id = input("Request ID: ").strip()
                print(system.displayReplies(request_id) or "No replies yet.")
            elif choice == "9":
                print(list(system.requests.values()))
            else:
                print("Choose a listed action.")
        except (KeyError, ValueError) as error:
            print(f"Error: {error}")


def _searchRequests(system: SupportRequestSystem) -> None:
    """Find a request by ID or customer name and print all matching records."""
    mode = input("Search by (id/name): ").strip().casefold()
    query = input("Search value: ").strip()
    if mode == "id":
        match = system.searchById(query)
        matches = [match] if match is not None else []
    elif mode == "name":
        matches = system.searchByCustomerName(query)
    else:
        matches = []
    print(matches)
