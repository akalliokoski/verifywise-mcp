"""VerifyWise MCP server entry point.

Creates the main ``FastMCP`` instance and registers all domain-specific tools
and resources. Run this module directly to start the server in STDIO mode.
"""

import logging
import sys

from mcp.server.fastmcp import FastMCP

# Configure logging to stderr — CRITICAL for STDIO transport where stdout is
# reserved for JSON-RPC messages. Any log output to stdout would corrupt the
# MCP protocol stream.
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="verifywise-mcp",
    instructions="""
    You are connected to VerifyWise, an open-source AI governance platform.

    Use the available tools to:
    - Manage AI governance projects (Use Cases) and their lifecycle
    - Track, create, and update risks identified in AI deployments
    - Monitor compliance with frameworks: EU AI Act, ISO 42001, ISO 27001, NIST AI RMF
    - Manage vendor risk assessments for third-party AI providers
    - Track AI/ML model inventory across the organisation

    Key concepts:
    - Projects / Use Cases: AI applications being governed
    - Risks: Identified threats to responsible AI deployment
    - Controls: Framework compliance requirements
    - Vendors: Third-party AI service and model providers
    - Models: AI/ML models in the organisation's inventory
    """,
)

# Import and register domain tools
# Each register_* function decorates tools onto the shared `mcp` instance.
from verifywise_mcp.tools.projects import register_tools as _register_projects  # noqa: E402
from verifywise_mcp.tools.risks import register_tools as _register_risks  # noqa: E402

_register_projects(mcp)
_register_risks(mcp)

logger.info("VerifyWise MCP server initialised with %d tools", len(mcp._tool_manager.list_tools()))


def main() -> None:
    """Start the MCP server using the transport specified in settings.

    Reads ``VERIFYWISE_TRANSPORT`` from the environment (defaults to
    ``stdio``). Call this from the CLI entry point or run the module directly.
    """
    import os

    transport = os.getenv("VERIFYWISE_TRANSPORT", "stdio")
    logger.info("Starting VerifyWise MCP server (transport=%s)", transport)
    mcp.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
