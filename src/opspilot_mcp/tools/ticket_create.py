"""Ticket creation tool implementation."""

from typing import List

from ..storage.data_access import TicketDataAccess
from ..schemas import TicketCreateInput, TicketCreateOutput


def ticket_create(service: str, summary: str, evidence: str, steps: List[str]) -> dict:
    """Create a new incident ticket.
    
    Args:
        service: Service name
        summary: Ticket summary/title
        evidence: Evidence collected during investigation
        steps: Recommended action steps
        
    Returns:
        Dict with ticket_path, id, and created_at
    """
    # Validate input
    input_data = TicketCreateInput(
        service=service,
        summary=summary,
        evidence=evidence,
        steps=steps
    )
    
    # Execute creation
    accessor = TicketDataAccess()
    result = accessor.create(
        service=input_data.service,
        summary=input_data.summary,
        evidence=input_data.evidence,
        steps=input_data.steps
    )
    
    # Validate output
    output = TicketCreateOutput(**result)
    return output.model_dump()
