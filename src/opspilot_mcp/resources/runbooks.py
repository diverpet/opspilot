"""Runbooks resource implementation."""

from typing import Optional, Dict, Any

from ..storage.data_access import RunbookDataAccess
from ..schemas import RunbookIndex, RunbookContent


def get_runbook_index() -> dict:
    """Get the index of all runbooks.
    
    Returns:
        Dict with runbooks list and total count
    """
    accessor = RunbookDataAccess()
    result = accessor.get_index()
    output = RunbookIndex(**result)
    return output.model_dump()


def get_runbook_content(name: str) -> Optional[dict]:
    """Get the content of a specific runbook.
    
    Args:
        name: Runbook name (without .md extension)
        
    Returns:
        Dict with name, title, content, and path; or None if not found
    """
    accessor = RunbookDataAccess()
    result = accessor.get_content(name)
    if result is None:
        return None
    output = RunbookContent(**result)
    return output.model_dump()
