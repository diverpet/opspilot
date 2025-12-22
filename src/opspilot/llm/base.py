"""Base LLM interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def call(
        self,
        step_name: str,
        prompt: str,
        schema: Type[BaseModel],
        max_retries: int = 2
    ) -> tuple[Optional[BaseModel], bool, str]:
        """Call the LLM and parse response.
        
        Args:
            step_name: Name of the current step (for tracing)
            prompt: The prompt to send
            schema: Pydantic model to validate response
            max_retries: Maximum retry attempts for schema failures
            
        Returns:
            Tuple of (parsed_result, success, error_message)
        """
        pass
    
    @abstractmethod
    async def raw_call(self, prompt: str, system_prompt: str = "") -> str:
        """Raw LLM call without schema validation.
        
        Args:
            prompt: The prompt to send
            system_prompt: Optional system prompt
            
        Returns:
            Raw text response
        """
        pass
