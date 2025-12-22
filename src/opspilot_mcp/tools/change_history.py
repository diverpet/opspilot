"""Change history tool implementation."""

from ..storage.data_access import ChangeDataAccess
from ..schemas import ChangeHistoryInput, ChangeHistoryOutput


def change_history(service: str, time_range: str, limit: int = 10) -> dict:
    """Get change history for a service.
    
    Args:
        service: Service name
        time_range: Time range (e.g., '30m', '1h', '24h')
        limit: Maximum number of changes to return
        
    Returns:
        Dict with changes and summary
    """
    # Validate input
    input_data = ChangeHistoryInput(
        service=service,
        time_range=time_range,
        limit=limit
    )
    
    # Execute query
    accessor = ChangeDataAccess()
    result = accessor.get_history(
        service=input_data.service,
        time_range=input_data.time_range,
        limit=input_data.limit
    )
    
    # Validate output
    output = ChangeHistoryOutput(**result)
    return output.model_dump()
