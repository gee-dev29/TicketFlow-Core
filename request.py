"""Public entry point for the customer support request system.

Run ``python request.py`` to start the interactive menu. Import
``SupportRequestSystem`` from this module to use the request manager directly.
"""

from requestCli import runCli
from request_manager import SupportRequestSystem

__all__ = ["SupportRequestSystem", "runCli"]


if __name__ == "__main__":
    runCli()
