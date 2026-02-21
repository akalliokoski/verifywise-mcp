"""Unit tests for the MCP server entry point."""

import sys


def test_server_mcp_instance_name():
    """The FastMCP instance should be named 'verifywise-mcp'."""
    from verifywise_mcp.server import mcp

    assert mcp.name == "verifywise-mcp"


def test_server_has_instructions():
    """The FastMCP instance should have a non-empty instructions string."""
    from verifywise_mcp.server import mcp

    assert mcp.instructions
    assert len(mcp.instructions) > 20


def test_server_logs_to_stderr_not_stdout(capsys):
    """The server should configure logging to stderr, not stdout."""
    import logging

    from verifywise_mcp.server import mcp  # noqa: F401

    # Emit a test log message and confirm it does not appear on stdout
    logger = logging.getLogger("verifywise_mcp")
    logger.info("test message")

    captured = capsys.readouterr()
    assert "test message" not in captured.out


def test_server_module_has_main_function():
    """server.py should expose a main() function for the entry point."""
    import verifywise_mcp.server as server_module

    assert callable(getattr(server_module, "main", None))
