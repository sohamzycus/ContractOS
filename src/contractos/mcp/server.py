"""ContractOS MCP Server — entry point.

Usage:
    # stdio (default — for Cursor / Claude Desktop)
    python -m contractos.mcp.server

    # Streamable HTTP (for Docker / remote)
    python -m contractos.mcp.server --transport http --port 8743
"""

from __future__ import annotations

import argparse
import logging
import sys

from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("contractos.mcp")


def create_server(
    host: str = "0.0.0.0",
    port: int = 8743,
) -> tuple[FastMCP, "MCPContext"]:  # noqa: F821
    """Create and configure the MCP server with all tools, resources, and prompts."""
    from contractos.mcp.context import MCPContext
    from contractos.mcp.prompts import register_prompts
    from contractos.mcp.resources import register_resources
    from contractos.mcp.tools import register_tools

    mcp = FastMCP(
        name="ContractOS",
        instructions="Contract intelligence — upload, analyse, review, triage, and query legal contracts with full provenance.",
        json_response=True,
        host=host,
        port=port,
    )

    ctx = MCPContext()

    register_tools(mcp, ctx)
    register_resources(mcp, ctx)
    register_prompts(mcp, ctx)

    logger.info(
        "ContractOS MCP server ready — %d tools, %d resources, %d prompts",
        len(mcp._tool_manager._tools) if hasattr(mcp, "_tool_manager") else 13,
        10,
        5,
    )

    return mcp, ctx


def main() -> None:
    """CLI entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="ContractOS MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8743,
        help="Port for HTTP transport (default: 8743)",
    )
    args = parser.parse_args()

    mcp, ctx = create_server(host="0.0.0.0", port=args.port)

    try:
        if args.transport == "http":
            logger.info("Starting ContractOS MCP server on http://0.0.0.0:%d/mcp", args.port)
            mcp.run(transport="streamable-http")
        else:
            logger.info("Starting ContractOS MCP server on stdio")
            mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
