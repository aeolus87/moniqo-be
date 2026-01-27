"""
Groq LLM Integration

Complete Groq API integration with cost tracking.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from groq import Groq, AsyncGroq
from typing import Dict, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone

from app.integrations.ai.base import (
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


class GroqModel(BaseLLM):
    """
    Groq LLM Integration
    
    Fast inference LLM client with cost tracking.
    
    Features:
    - Fast inference (LLaMA models)
    - Text generation
    - Structured output (JSON mode)
    - Cost tracking
    - Error handling
    
    Usage:
        model = GroqModel(
            model_name="llama-3.3-70b-versatile",
            api_key="your_groq_key"
        )
        
        response = await model.generate_response(
            prompt="Analyze BTC market",
            temperature=0.7
        )
    """
    
    # Pricing per 1M tokens (as of Nov 2024)
    PRICING = {
        "llama-3.3-70b-versatile": {
            "input": Decimal("0.59"),   # $0.59 per 1M input tokens
            "output": Decimal("0.79")   # $0.79 per 1M output tokens
        },
        "llama-3.1-70b-versatile": {
            "input": Decimal("0.59"),
            "output": Decimal("0.79")
        },
        "llama-3.1-8b-instant": {
            "input": Decimal("0.05"),   # $0.05 per 1M input tokens
            "output": Decimal("0.08")   # $0.08 per 1M output tokens
        },
        "mixtral-8x7b-32768": {
            "input": Decimal("0.24"),
            "output": Decimal("0.24")
        }
    }
    
    def __init__(
        self,
        model_name: str = "llama-3.3-70b-versatile",
        api_key: str = "",
        **kwargs
    ):
        """
        Initialize Groq model.
        
        Args:
            model_name: Groq model name
            api_key: Groq API key
            **kwargs: Additional config
        """
        # Filter out 'proxies' from kwargs as it's not supported by newer httpx versions
        # and causes issues with Groq library initialization
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'proxies'}
        
        super().__init__(
            provider=ModelProvider.GROQ,
            model_name=model_name,
            api_key=api_key,
            **filtered_kwargs
        )
        
        if not api_key:
            raise ModelAuthenticationError("Groq API key is required")
        
        # Initialize Groq client
        # Note: Only pass api_key explicitly to avoid passing unsupported parameters
        # The Groq library 0.9.0 has a bug where it tries to pass 'proxies' to httpx,
        # which newer httpx versions don't support. Updating to groq>=0.27.0 fixes this.
        try:
            self.client = AsyncGroq(api_key=api_key)
        except TypeError as e:
            # Catch TypeError specifically for unsupported parameters
            error_msg = str(e)
            if 'proxies' in error_msg or 'unexpected keyword' in error_msg:
                logger.error(
                    f"Groq client initialization failed due to unsupported parameter. "
                    f"This is likely due to using groq==0.9.0 with newer httpx. "
                    f"Please update: pip install 'groq>=0.27.0'. Error: {error_msg}"
                )
                raise ModelConnectionError(
                    f"Failed to initialize Groq: Unsupported parameter detected. "
                    f"Please update the Groq library: pip install 'groq>=0.27.0'. "
                    f"Original error: {error_msg}"
                )
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {str(e)}")
            raise ModelConnectionError(f"Failed to initialize Groq: {str(e)}")
        
        logger.info(f"Groq model initialized: {model_name}")
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text response from Groq"""
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
            
            # Generation parameters
            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                **kwargs
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            # Generate response
            response = await self.client.chat.completions.create(**params)
            
            # Extract response text
            result_text = response.choices[0].message.content
            
            # Track usage
            if hasattr(response, 'usage'):
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                self.track_usage(input_tokens, output_tokens)
            else:
                # Estimate if not provided
                input_tokens = len(prompt.split()) * 1.3
                output_tokens = len(result_text.split()) * 1.3
                self.track_usage(int(input_tokens), int(output_tokens))
            
            logger.debug(f"Groq generated response: {len(result_text)} chars")
            
            return result_text
        
        except Exception as e:
            error_msg = str(e)
            
            if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                raise ModelAuthenticationError(f"Groq authentication failed: {error_msg}")
            
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                raise ModelRateLimitError(f"Groq rate limit exceeded: {error_msg}")
            
            if "token" in error_msg.lower() and "limit" in error_msg.lower():
                raise ModelTokenLimitError(f"Groq token limit exceeded: {error_msg}")
            
            logger.error(f"Groq generation failed: {error_msg}")
            raise ModelError(f"Groq generation failed: {error_msg}")
    
    async def generate_structured_output(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured JSON output from Groq"""
        try:
            import json
            
            # Build prompt with JSON schema instructions
            json_instructions = f"""
Generate a JSON response matching this schema:
{json.dumps(schema, indent=2)}

Return ONLY valid JSON, no other text.
"""
            
            # Build messages
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": f"{json_instructions}\n\n{prompt}"
            })
            
            # Use JSON mode
            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
                **kwargs
            }
            
            # Generate response
            response = await self.client.chat.completions.create(**params)
            
            # Parse JSON response
            result_text = response.choices[0].message.content
            
            # Extract JSON (may have markdown code blocks)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            # Track usage
            if hasattr(response, 'usage'):
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                self.track_usage(input_tokens, output_tokens)
            
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Groq JSON response: {str(e)}")
            raise ModelError(f"Invalid JSON response from Groq: {str(e)}")
        
        except Exception as e:
            logger.error(f"Groq structured output failed: {str(e)}")
            raise ModelError(f"Groq structured output failed: {str(e)}")
    
    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """Calculate cost for token usage"""
        # Get pricing for model
        pricing = self.PRICING.get(self.model_name, self.PRICING["llama-3.3-70b-versatile"])
        
        # Calculate cost
        input_cost = (Decimal(input_tokens) / Decimal("1000000")) * pricing["input"]
        output_cost = (Decimal(output_tokens) / Decimal("1000000")) * pricing["output"]
        
        total_cost = input_cost + output_cost
        
        return total_cost
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Groq"""
        try:
            import time
            
            start_time = time.time()
            
            # Simple test prompt
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": "Say 'OK' if you can read this."}
                ],
                temperature=0.0,
                max_tokens=10
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            result_text = response.choices[0].message.content
            
            return {
                "success": True,
                "provider": self.provider.value,
                "model_name": self.model_name,
                "latency_ms": latency_ms,
                "response": result_text,
                "server_time": datetime.now(timezone.utc),
                "message": "Groq connection successful"
            }
        
        except Exception as e:
            logger.error(f"Groq connection test failed: {str(e)}")
            raise ModelConnectionError(f"Groq connection failed: {str(e)}")


