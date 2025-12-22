"""Runbook lookup tool implementation."""

from ..storage.data_access import RunbookDataAccess
from ..schemas import RunbookLookupInput, RunbookLookupOutput


def runbook_lookup(service: str, symptom: str, limit: int = 3) -> dict:
    """Lookup runbooks matching a symptom.
    
    Args:
        service: Service name
        symptom: Symptom or issue description to search for
        limit: Maximum number of matches to return
        
    Returns:
        Dict with matches and summary
    """
    # Validate input
    input_data = RunbookLookupInput(
        service=service,
        symptom=symptom,
        limit=limit
    )
    
    # Execute lookup
    accessor = RunbookDataAccess()
    result = accessor.lookup(
        service=input_data.service,
        symptom=input_data.symptom,
        limit=input_data.limit
    )
    
    # Validate output
    output = RunbookLookupOutput(**result)
    return output.model_dump()
