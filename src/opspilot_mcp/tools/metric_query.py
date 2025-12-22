"""Metric query tool implementation."""

from ..storage.data_access import MetricDataAccess
from ..schemas import MetricQueryInput, MetricQueryOutput


def metric_query(service: str, metric: str, time_range: str) -> dict:
    """Query metrics for a service.
    
    Args:
        service: Service name to query metrics for
        metric: Metric name (e.g., 'latency', 'error_rate', 'cpu')
        time_range: Time range (e.g., '30m', '1h', '24h')
        
    Returns:
        Dict with series, stats, and summary
    """
    # Validate input
    input_data = MetricQueryInput(
        service=service,
        metric=metric,
        time_range=time_range
    )
    
    # Execute query
    accessor = MetricDataAccess()
    result = accessor.query(
        service=input_data.service,
        metric=input_data.metric,
        time_range=input_data.time_range
    )
    
    # Validate output
    output = MetricQueryOutput(**result)
    return output.model_dump()
