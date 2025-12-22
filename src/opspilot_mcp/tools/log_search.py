"""Log search tool implementation."""

from ..storage.data_access import LogDataAccess
from ..schemas import LogSearchInput, LogSearchOutput


def log_search(service: str, query: str, time_range: str, limit: int = 20) -> dict:
    """Search logs for a service.
    
    Args:
        service: Service name to search logs for
        query: Search query string
        time_range: Time range (e.g., '30m', '1h', '24h')
        limit: Maximum number of hits to return
        
    Returns:
        Dict with hits, summary, and total_matched
    """
    # Validate input
    input_data = LogSearchInput(
        service=service,
        query=query,
        time_range=time_range,
        limit=limit
    )
    
    # Execute search
    accessor = LogDataAccess()
    result = accessor.search(
        service=input_data.service,
        query=input_data.query,
        time_range=input_data.time_range,
        limit=input_data.limit
    )
    
    # Validate output
    output = LogSearchOutput(**result)
    return output.model_dump()
