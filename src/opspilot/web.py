"""Web interface for OpsPilot agent."""

import asyncio
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from typing import Optional

from .agent.runtime import AgentRuntime
from .agent.schemas import ReportOutput
from .utils import get_artifacts_dir


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')


class InvestigationManager:
    """Manages investigation state and artifacts."""
    
    def __init__(self):
        self.artifacts_dir = get_artifacts_dir()
        self.artifacts_dir.mkdir(exist_ok=True)
    
    def list_investigations(self) -> list[dict]:
        """List all past investigations."""
        investigations = []
        
        # Find all report files
        for report_file in sorted(self.artifacts_dir.glob("report_*.md"), reverse=True):
            session_id = report_file.stem.replace("report_", "")
            trace_file = self.artifacts_dir / f"trace_{session_id}.jsonl"
            
            # Parse report metadata
            try:
                content = report_file.read_text()
                lines = content.split('\n')
                
                title = lines[0].replace('# ', '') if lines else "Unknown"
                service = ""
                generated = ""
                confidence = ""
                
                for line in lines[1:10]:  # Check first few lines
                    if line.startswith("**Service:**"):
                        service = line.replace("**Service:**", "").strip()
                    elif line.startswith("**Generated:**"):
                        generated = line.replace("**Generated:**", "").strip()
                    elif line.startswith("**Confidence:**"):
                        confidence = line.replace("**Confidence:**", "").strip()
                
                investigations.append({
                    'session_id': session_id,
                    'title': title,
                    'service': service,
                    'generated': generated,
                    'confidence': confidence,
                    'report_path': str(report_file),
                    'trace_path': str(trace_file) if trace_file.exists() else None
                })
            except Exception as e:
                logger.error(f"Error parsing {report_file}: {e}")
                continue
        
        return investigations
    
    def get_investigation(self, session_id: str) -> Optional[dict]:
        """Get details of a specific investigation."""
        report_file = self.artifacts_dir / f"report_{session_id}.md"
        trace_file = self.artifacts_dir / f"trace_{session_id}.jsonl"
        
        if not report_file.exists():
            return None
        
        # Read report content
        report_content = report_file.read_text()
        
        # Read trace if exists
        trace_events = []
        if trace_file.exists():
            try:
                with open(trace_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            trace_events.append(json.loads(line))
            except Exception as e:
                logger.error(f"Error reading trace: {e}")
        
        return {
            'session_id': session_id,
            'report': report_content,
            'trace': trace_events
        }


investigation_manager = InvestigationManager()


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/api/investigations', methods=['GET'])
def list_investigations():
    """API endpoint to list all investigations."""
    investigations = investigation_manager.list_investigations()
    return jsonify(investigations)


@app.route('/api/investigation/<session_id>', methods=['GET'])
def get_investigation(session_id):
    """API endpoint to get a specific investigation."""
    investigation = investigation_manager.get_investigation(session_id)
    if investigation is None:
        return jsonify({'error': 'Investigation not found'}), 404
    return jsonify(investigation)


@app.route('/api/investigate', methods=['POST'])
def investigate():
    """API endpoint to trigger a new investigation."""
    data = request.json
    
    service = data.get('service')
    alert = data.get('alert')
    time_range = data.get('time_range', '30m')
    
    if not service or not alert:
        return jsonify({'error': 'service and alert are required'}), 400
    
    # Get MCP command from environment or use default
    mcp_command = os.environ.get('MCP_COMMAND', 'python -m opspilot_mcp.server --stdio')
    
    # Run investigation asynchronously
    try:
        async def run_investigation():
            """Run the investigation asynchronously."""
            runtime = AgentRuntime(mcp_command)
            return await runtime.run(service=service, alert=alert, time_range=time_range)
        
        # Use asyncio.run() which properly manages the event loop
        report, report_path, trace_path = asyncio.run(run_investigation())
        
        # Extract session_id from file path
        session_id = report_path.stem.replace("report_", "")
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'report_path': str(report_path),
            'trace_path': str(trace_path),
            'root_cause': report.root_cause,
            'confidence': report.confidence
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def run_web(host='0.0.0.0', port=5000, debug=False):
    """Run the web server."""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_web(debug=True)
