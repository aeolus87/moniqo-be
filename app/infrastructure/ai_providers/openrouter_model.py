"""
OpenRouter LLM Integration

Multi-model proxy for accessing various LLMs through OpenRouter.

Author: Moniqo Team
Last Updated: 2025-01-17
"""

import aiohttp
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


class OpenRouterModel(BaseLLM):
    """
    OpenRouter LLM Integration
    
    Multi-model proxy accessing various LLMs.
    
    Features:
    - Access to multiple model providers (OpenAI, Anthropic, Mistral, etc.)
    - Unified API interface
    - Cost tracking
    - Fallback support
    
    Usage:
        model = OpenRouterModel(
            model_name="anthropic/claude-3-sonnet",
            api_key="your_openrouter_key"
        )
        
        response = await model.generate_response(
            prompt="Analyze BTC market",
            temperature=0.7
        )
    """
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    # Pricing per 1M tokens (varies by model)
    PRICING = {
        "mistralai/mistral-7b-instruct:free": {
            "input": Decimal("0.00"),
            "output": Decimal("0.00")
        },
        "google/gemma-7b-it:free": {
            "input": Decimal("0.00"),
            "output": Decimal("0.00")
        },
        "meta-llama/llama-3.1-8b-instruct:free": {
            "input": Decimal("0.00"),
            "output": Decimal("0.00")
        },
        "anthropic/claude-3-haiku": {
            "input": Decimal("0.25"),
            "output": Decimal("1.25")
        },
        "openai/gpt-4o-mini": {
            "input": Decimal("0.15"),
            "output": Decimal("0.60")
        },
        "meta-llama/llama-3.1-70b-instruct": {
            "input": Decimal("0.52"),
            "output": Decimal("0.75")
        }
    }
    
    # Free models available on OpenRouter
    FREE_MODELS = [
        "mistralai/mistral-7b-instruct:free",
        "google/gemma-7b-it:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "huggingfaceh4/zephyr-7b-beta:free",
        "openchat/openchat-7b:free"
    ]
    
    def __init__(
        self,
        model_name: str = "anthropic/claude-3-haiku",
        api_key: str = "",
        **kwargs
    ):
        """
        Initialize OpenRouter model.
        
        Args:
            model_name: OpenRouter model name (e.g., "anthropic/claude-3-sonnet")
            api_key: OpenRouter API key
            **kwargs: Additional config
        """
        super().__init__(
            provider=ModelProvider.OPENAI,  # OpenRouter uses OpenAI-compatible API
            model_name=model_name,
            api_key=api_key,
            **kwargs
        )
        
        if not api_key:
            raise ModelAuthenticationError("OpenRouter API key is required")
        
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": kwargs.get("app_url", "https://moniqo.ai"),
            "X-Title": kwargs.get("app_name", "Moniqo Trading Platform"),
            "Content-Type": "application/json"
        }
        
        logger.info(f"OpenRouter model initialized: {model_name}")
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text response from OpenRouter"""
        try:
            # Build messages
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Request payload
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                **kwargs
            }
            
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            # Make request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=self.headers,
                    json=payload
                ) as response:
                    if response.status == 401:
                        raise ModelAuthenticationError("OpenRouter authentication failed")
                    
                    if response.status == 429:
                        raise ModelRateLimitError("OpenRouter rate limit exceeded")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise ModelError(f"OpenRouter API error: {error_text}")
                    
                    data = await response.json()
            
            # Extract response
            result_text = data["choices"][0]["message"]["content"]
            
            # Track usage
            if "usage" in data:
                input_tokens = data["usage"].get("prompt_tokens", 0)
                output_tokens = data["usage"].get("completion_tokens", 0)
                self.track_usage(input_tokens, output_tokens)
            
            logger.debug(f"OpenRouter generated response: {len(result_text)} chars")
            
            return result_text
        
        except aiohttp.ClientError as e:
            logger.error(f"OpenRouter connection error: {str(e)}")
            raise ModelConnectionError(f"OpenRouter connection failed: {str(e)}")
        
        except Exception as e:
            if isinstance(e, (ModelAuthenticationError, ModelRateLimitError, ModelError)):
                raise
            logger.error(f"OpenRouter generation failed: {str(e)}")
            raise ModelError(f"OpenRouter generation failed: {str(e)}")
    
    async def generate_structured_output(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured JSON output from OpenRouter"""
        try:
            import json
            
            # Build prompt with JSON instructions
            json_instructions = f"""
Generate a JSON response matching this schema:
{json.dumps(schema, indent=2)}

Return ONLY valid JSON, no other text or markdown.
"""
            
            full_prompt = f"{json_instructions}\n\n{prompt}"
            
            # Generate response
            response_text = await self.generate_response(
                prompt=full_prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                **kwargs
            )
            
            # Clean and parse JSON
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenRouter JSON response: {str(e)}")
            raise ModelError(f"Invalid JSON response from OpenRouter: {str(e)}")
        
        except Exception as e:
            if isinstance(e, ModelError):
                raise
            logger.error(f"OpenRouter structured output failed: {str(e)}")
            raise ModelError(f"OpenRouter structured output failed: {str(e)}")
    
    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """Calculate cost for token usage"""
        # Get pricing for model (default to free if unknown)
        pricing = self.PRICING.get(self.model_name, {"input": Decimal("0"), "output": Decimal("0")})
        
        # Calculate cost per 1M tokens
        input_cost = (Decimal(input_tokens) / Decimal("1000000")) * pricing["input"]
        output_cost = (Decimal(output_tokens) / Decimal("1000000")) * pricing["output"]
        
        return input_cost + output_cost
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to OpenRouter"""
        try:
            import time
            
            start_time = time.time()
            
            response = await self.generate_response(
                prompt="Say 'OK' if you can read this.",
                temperature=0.0,
                max_tokens=10
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                "success": True,
                "provider": "openrouter",
                "model_name": self.model_name,
                "latency_ms": latency_ms,
                "response": response,
                "server_time": datetime.now(timezone.utc),
                "message": "OpenRouter connection successful"
            }
        
        except Exception as e:
            logger.error(f"OpenRouter connection test failed: {str(e)}")
            raise ModelConnectionError(f"OpenRouter connection failed: {str(e)}")
    
    @classmethod
    def get_free_models(cls) -> list:
        """Get list of free models available on OpenRouter"""
        return cls.FREE_MODELS.copy()
