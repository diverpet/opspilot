"""OpenAI LLM provider."""

import os
import json
import re
from typing import Type, Optional

from pydantic import BaseModel, ValidationError
from openai import AsyncOpenAI

from .base import BaseLLM
from ..agent.prompts import SYSTEM_PROMPT


class OpenAILLM(BaseLLM):
    """OpenAI LLM provider."""
    
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    
    async def raw_call(self, prompt: str, system_prompt: str = "") -> str:
        """Raw LLM call without schema validation."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=2000
        )
        
        return response.choices[0].message.content or ""
    
    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON from text response."""
        # Try to find JSON in code blocks
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        # Try to parse the entire text as JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object in text
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    async def call(
        self,
        step_name: str,
        prompt: str,
        schema: Type[BaseModel],
        max_retries: int = 2
    ) -> tuple[Optional[BaseModel], bool, str]:
        """Call the LLM and parse response with schema validation."""
        last_error = ""
        
        for attempt in range(max_retries + 1):
            try:
                current_prompt = prompt
                if attempt > 0:
                    current_prompt = f"{prompt}\n\nPrevious attempt failed with error: {last_error}\nPlease provide valid JSON matching the schema."
                
                raw_response = await self.raw_call(current_prompt, SYSTEM_PROMPT)
                
                # Extract JSON
                json_data = self._extract_json(raw_response)
                if json_data is None:
                    last_error = "Could not extract valid JSON from response"
                    continue
                
                # Validate with schema
                result = schema.model_validate(json_data)
                return result, True, ""
                
            except ValidationError as e:
                last_error = f"Schema validation failed: {str(e)}"
            except Exception as e:
                last_error = f"LLM call failed: {str(e)}"
        
        return None, False, last_error
