"""
Google Gemini LLM Integration

Complete Gemini API integration with cost tracking.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import google.generativeai as genai
from typing import Dict, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone

from app.infrastructure.ai_providers.base import (
    BaseLLM,
    ModelProvider,
    ModelError,
    ModelConnectionError,
    ModelAuthenticationError,
    ModelRateLimitError,
    ModelTokenLimitError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiModel(BaseLLM):
    """
    Google Gemini LLM Integration
    
    Full-featured Gemini API client with cost tracking.
    
    Features:
    - Text generation
    - Structured output (JSON mode)
    - Cost tracking
    - Error handling
    - Connection testing
    
    Usage:
        model = GeminiModel(
            model_name="gemini-1.5-pro",
            api_key="your_gemini_key"
        )
        
        # Generate response
        response = await model.generate_response(
            prompt="Analyze BTC market sentiment",
            temperature=0.7
        )
        
        # Generate structured output
        result = await model.generate_structured_output(
            prompt="Analyze BTC market",
            schema={
                "type": "object",
                "properties": {
                    "sentiment": {"type": "string"},
                    "confidence": {"type": "number"}
                }
            }
        )
    """
    
    # Pricing per 1M tokens (as of Nov 2024)
    PRICING = {
        "gemini-1.5-pro": {
            "input": Decimal("1.25"),   # $1.25 per 1M input tokens
            "output": Decimal("5.00")   # $5.00 per 1M output tokens
        },
        "gemini-1.5-flash": {
            "input": Decimal("0.075"),  # $0.075 per 1M input tokens
            "output": Decimal("0.30")   # $0.30 per 1M output tokens
        },
        "gemini-1.0-pro": {
            "input": Decimal("0.50"),   # $0.50 per 1M input tokens
            "output": Decimal("1.50")   # $1.50 per 1M output tokens
        }
    }
    
    def __init__(
        self,
        model_name: str = "gemini-1.5-pro",
        api_key: str = "",
        **kwargs
    ):
        """
        Initialize Gemini model.
        
        Args:
            model_name: Gemini model name
            api_key: Google API key
            **kwargs: Additional config
        """
        super().__init__(
            provider=ModelProvider.GEMINI,
            model_name=model_name,
            api_key=api_key,
            **kwargs
        )
        
        if not api_key:
            raise ModelAuthenticationError("Gemini API key is required")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Initialize model
        try:
            self.model = genai.GenerativeModel(model_name)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {str(e)}")
            raise ModelConnectionError(f"Failed to initialize Gemini: {str(e)}")
        
        logger.info(f"Gemini model initialized: {model_name}")
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text response from Gemini"""
        try:
            # Build prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Generation config
            generation_config = {
                "temperature": temperature,
                **kwargs
            }
            
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            
            # Generate response
            response = await self.model.generate_content_async(
                full_prompt,
                generation_config=generation_config
            )
            
            # Extract response text
            result_text = response.text if hasattr(response, 'text') else str(response)
            
            # Track usage (Gemini provides token counts)
            if hasattr(response, 'usage_metadata'):
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
                self.track_usage(input_tokens, output_tokens)
            else:
                # Estimate if not provided
                input_tokens = len(full_prompt.split()) * 1.3  # Rough estimate
                output_tokens = len(result_text.split()) * 1.3
                self.track_usage(int(input_tokens), int(output_tokens))
            
            logger.debug(f"Gemini generated response: {len(result_text)} chars")
            
            return result_text
        
        except Exception as e:
            error_msg = str(e)
            
            if "API key" in error_msg or "authentication" in error_msg.lower():
                raise ModelAuthenticationError(f"Gemini authentication failed: {error_msg}")
            
            if "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                raise ModelRateLimitError(f"Gemini rate limit exceeded: {error_msg}")
            
            if "token" in error_msg.lower() and "limit" in error_msg.lower():
                raise ModelTokenLimitError(f"Gemini token limit exceeded: {error_msg}")
            
            logger.error(f"Gemini generation failed: {error_msg}")
            raise ModelError(f"Gemini generation failed: {error_msg}")
    
    async def generate_structured_output(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured JSON output from Gemini"""
        try:
            import json
            
            # Build prompt with JSON schema instructions
            json_instructions = f"""
Generate a JSON response matching this schema:
{json.dumps(schema, indent=2)}

Return ONLY valid JSON, no other text.
"""
            
            full_prompt = f"{system_prompt or ''}\n\n{json_instructions}\n\n{prompt}"
            
            # Use lower temperature for structured output
            generation_config = {
                "temperature": temperature,
                "response_mime_type": "application/json",
                **kwargs
            }
            
            # Generate response
            response = await self.model.generate_content_async(
                full_prompt,
                generation_config=generation_config
            )
            
            # Parse JSON response
            result_text = response.text if hasattr(response, 'text') else str(response)
            
            # Extract JSON (may have markdown code blocks)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            # Track usage
            if hasattr(response, 'usage_metadata'):
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
                self.track_usage(input_tokens, output_tokens)
            
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {str(e)}")
            raise ModelError(f"Invalid JSON response from Gemini: {str(e)}")
        
        except Exception as e:
            logger.error(f"Gemini structured output failed: {str(e)}")
            raise ModelError(f"Gemini structured output failed: {str(e)}")
    
    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """Calculate cost for token usage"""
        # Get pricing for model
        pricing = self.PRICING.get(self.model_name, self.PRICING["gemini-1.5-pro"])
        
        # Calculate cost
        input_cost = (Decimal(input_tokens) / Decimal("1000000")) * pricing["input"]
        output_cost = (Decimal(output_tokens) / Decimal("1000000")) * pricing["output"]
        
        total_cost = input_cost + output_cost
        
        return total_cost
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Gemini"""
        try:
            import time
            
            start_time = time.time()
            
            # Simple test prompt
            response = await self.model.generate_content_async(
                "Say 'OK' if you can read this.",
                generation_config={"temperature": 0.0, "max_output_tokens": 10}
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            result_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                "success": True,
                "provider": self.provider.value,
                "model_name": self.model_name,
                "latency_ms": latency_ms,
                "response": result_text,
                "server_time": datetime.now(timezone.utc),
                "message": "Gemini connection successful"
            }
        
        except Exception as e:
            logger.error(f"Gemini connection test failed: {str(e)}")
            raise ModelConnectionError(f"Gemini connection failed: {str(e)}")


