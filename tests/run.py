"""Test runner for OpsPilot agent."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

import yaml


def load_test_cases(cases_file: Path) -> List[Dict[str, Any]]:
    """Load test cases from YAML file."""
    with open(cases_file) as f:
        data = yaml.safe_load(f)
    return data.get("cases", [])


async def run_single_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single test case."""
    from opspilot.agent.runtime import AgentRuntime
    
    print(f"\n{'=' * 60}")
    print(f"Running: {case['name']}")
    print(f"Description: {case['description']}")
    print(f"{'=' * 60}")
    
    # Get the project root
    project_root = Path(__file__).parent.parent
    artifacts_dir = project_root / "artifacts" / case["name"]
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # Create runtime
    mcp_command = f"{sys.executable} -m opspilot_mcp.server --stdio"
    runtime = AgentRuntime(mcp_command, artifacts_dir)
    
    try:
        report, report_path, trace_path = await runtime.run(
            service=case["service"],
            alert=case["alert"],
            time_range=case["time_range"]
        )
        
        # Validate results
        validations = validate_results(case, report, trace_path)
        
        result = {
            "name": case["name"],
            "success": all(v["passed"] for v in validations),
            "report_path": str(report_path),
            "trace_path": str(trace_path),
            "validations": validations
        }
        
        print(f"\nResult: {'PASSED' if result['success'] else 'FAILED'}")
        for v in validations:
            status = "✓" if v["passed"] else "✗"
            print(f"  {status} {v['check']}: {v['message']}")
        
        return result
        
    except Exception as e:
        print(f"\nError running case: {e}")
        return {
            "name": case["name"],
            "success": False,
            "error": str(e),
            "validations": []
        }


def validate_results(
    case: Dict[str, Any],
    report: Any,
    trace_path: Path
) -> List[Dict[str, Any]]:
    """Validate test results against expected values."""
    validations = []
    expected = case.get("expected", {})
    
    # Check that report has evidence chain (not empty conclusions)
    evidence_count = len(report.evidence_chain) if hasattr(report, 'evidence_chain') else 0
    validations.append({
        "check": "Evidence chain exists",
        "passed": evidence_count > 0,
        "message": f"Found {evidence_count} evidence items"
    })
    
    # Check that required tools were called
    expected_tools = expected.get("tools_called", [])
    tools_used = report.tools_used if hasattr(report, 'tools_used') else []
    for tool in expected_tools:
        validations.append({
            "check": f"Tool '{tool}' was called",
            "passed": tool in tools_used,
            "message": f"Tools used: {tools_used}"
        })
    
    # Check that trace contains MCP tool calls
    mcp_calls = count_mcp_calls(trace_path)
    validations.append({
        "check": "Trace contains MCP tool calls",
        "passed": mcp_calls >= 2,
        "message": f"Found {mcp_calls} MCP tool calls in trace"
    })
    
    # Check for expected keywords in report
    report_text = str(report.root_cause) + str(report.alert_summary)
    keywords = expected.get("keywords_in_report", [])
    for keyword in keywords:
        found = keyword.lower() in report_text.lower()
        validations.append({
            "check": f"Report contains keyword '{keyword}'",
            "passed": found,
            "message": "Found" if found else "Not found"
        })
    
    return validations


def count_mcp_calls(trace_path: Path) -> int:
    """Count MCP tool calls in trace file."""
    if not trace_path.exists():
        return 0
    
    count = 0
    with open(trace_path) as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                if event.get("event_type") == "mcp_tool":
                    count += 1
            except json.JSONDecodeError:
                pass
    return count


async def run_all_cases():
    """Run all test cases."""
    # Find cases file
    project_root = Path(__file__).parent.parent
    cases_file = Path(__file__).parent / "cases.yaml"
    
    if not cases_file.exists():
        print(f"Error: Cases file not found at {cases_file}")
        sys.exit(1)
    
    # Load cases
    cases = load_test_cases(cases_file)
    print(f"Loaded {len(cases)} test cases")
    
    # Run each case
    results = []
    for case in cases:
        result = await run_single_case(case)
        results.append(result)
    
    # Print summary
    print(f"\n{'=' * 60}")
    print("TEST SUMMARY")
    print(f"{'=' * 60}")
    
    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed
    
    for r in results:
        status = "PASSED" if r["success"] else "FAILED"
        print(f"  [{status}] {r['name']}")
        if r.get("report_path"):
            print(f"    Report: {r['report_path']}")
            print(f"    Trace:  {r['trace_path']}")
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    # Add src to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))
    
    asyncio.run(run_all_cases())
