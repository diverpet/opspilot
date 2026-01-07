#!/usr/bin/env python3
"""Run the OpsPilot web interface."""

import argparse
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from opspilot.web import run_web


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OpsPilot Web Interface - Start the web server"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to bind to (default: 5000)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode"
    )
    
    args = parser.parse_args()
    
    print(f"OpsPilot Web Interface")
    print(f"=" * 50)
    print(f"Starting server on http://{args.host}:{args.port}")
    print(f"Debug mode: {args.debug}")
    print(f"=" * 50)
    print()
    
    # Set default MCP command if not set
    if not os.environ.get('MCP_COMMAND'):
        os.environ['MCP_COMMAND'] = 'python -m opspilot_mcp.server --stdio'
        print("Using default MCP command: python -m opspilot_mcp.server --stdio")
        print()
    
    run_web(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
