"""Main entry point for OpsPilot agent."""

import argparse
import asyncio
import sys


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OpsPilot - Production Incident Troubleshooting Agent"
    )
    parser.add_argument(
        "--service",
        required=True,
        help="Service name to investigate"
    )
    parser.add_argument(
        "--alert",
        required=True,
        help="Alert text describing the incident"
    )
    parser.add_argument(
        "--time-range",
        default="30m",
        help="Time range for investigation (e.g., '30m', '1h', '24h')"
    )
    parser.add_argument(
        "--mcp-stdio",
        required=True,
        help="Command to start MCP server (e.g., 'python -m opspilot_mcp.server --stdio')"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for artifacts (default: ./artifacts)"
    )
    
    args = parser.parse_args()
    
    # Import here to avoid circular imports
    from .agent.runtime import AgentRuntime
    from pathlib import Path
    
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    print(f"OpsPilot - Production Incident Troubleshooting Agent")
    print(f"=" * 50)
    print(f"Service: {args.service}")
    print(f"Alert: {args.alert}")
    print(f"Time Range: {args.time_range}")
    print(f"MCP Command: {args.mcp_stdio}")
    print(f"=" * 50)
    print()
    
    try:
        runtime = AgentRuntime(args.mcp_stdio, output_dir)
        report, report_path, trace_path = await runtime.run(
            service=args.service,
            alert=args.alert,
            time_range=args.time_range
        )
        
        print(f"\n{'=' * 50}")
        print("Investigation Complete!")
        print(f"{'=' * 50}")
        print(f"\nRoot Cause: {report.root_cause}")
        print(f"Confidence: {report.confidence:.0%}")
        print(f"\nImmediate Actions:")
        for action in report.immediate_actions:
            print(f"  - {action}")
        print(f"\nArtifacts:")
        print(f"  Report: {report_path}")
        print(f"  Trace:  {trace_path}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
