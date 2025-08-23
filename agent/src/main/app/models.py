"""
Multi-model support for LangGraph agent.
Supports multiple AI providers based on environment variables and API tokens.
"""

import os
import logging
import requests
from typing import Dict, Any, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Supported model providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    TOGETHER = "together"
    DEEPSEEK = "deepseek"


class ModelManager:
    """Manages multiple AI model providers and routing based on API tokens."""
    
    def __init__(self):
        """Initialize the model manager with available providers."""
        self.providers = {}
        self._setup_providers()
    
    def _setup_providers(self):
        """Setup available providers based on environment variables."""
        # Check for Ollama (local deployment)
        ollama_url = os.getenv("OLLAMA_BASE_URL")
        if ollama_url:
            self.providers[ModelProvider.OLLAMA] = {
                "enabled": True,
                "base_url": ollama_url,
                "model": os.getenv("OLLAMA_MODEL", "llama3.2:1b"),
                "api_key": None  # Ollama doesn't require API key
            }
            logger.info(f"✅ Ollama provider enabled: {ollama_url}")
        
        # Check for OpenAI (GPT-5 Series - 2025)
        # Default: gpt-5-nano ($0.05/1M input, $0.40/1M output)
        # Available: gpt-5, gpt-5-mini, gpt-5-nano
        # Features: 272k context, built-in reasoning, 94.6% AIME score
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.providers[ModelProvider.OPENAI] = {
                "enabled": True,
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model": os.getenv("OPENAI_MODEL", "gpt-5-nano"),
                "api_key": openai_key
            }
            logger.info("✅ OpenAI provider enabled")
        
        # Check for Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.providers[ModelProvider.ANTHROPIC] = {
                "enabled": True,
                "base_url": os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
                "model": os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
                "api_key": anthropic_key
            }
            logger.info("✅ Anthropic provider enabled")
        
        # Check for Groq
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            self.providers[ModelProvider.GROQ] = {
                "enabled": True,
                "base_url": os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
                "model": os.getenv("GROQ_MODEL", "llama3-8b-8192"),
                "api_key": groq_key
            }
            logger.info("✅ Groq provider enabled")
        
        # Check for Together AI
        together_key = os.getenv("TOGETHER_API_KEY")
        if together_key:
            self.providers[ModelProvider.TOGETHER] = {
                "enabled": True,
                "base_url": os.getenv("TOGETHER_BASE_URL", "https://api.together.xyz/v1"),
                "model": os.getenv("TOGETHER_MODEL", "meta-llama/Llama-2-7b-chat-hf"),
                "api_key": together_key
            }
            logger.info("✅ Together AI provider enabled")
        
        # Check for DeepSeek
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_key:
            self.providers[ModelProvider.DEEPSEEK] = {
                "enabled": True,
                "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                "model": os.getenv("DEEPSEEK_MODEL", "deepseek-r1"),
                "api_key": deepseek_key
            }
            logger.info("✅ DeepSeek provider enabled")
        
        if not self.providers:
            logger.warning("⚠️ No model providers configured! Check your environment variables.")
        else:
            logger.info(f"🔧 Model manager initialized with {len(self.providers)} providers")
    
    def get_primary_provider(self) -> Optional[ModelProvider]:
        """Get the primary provider based on the configured priority."""
        # Priority order based on environment variable or default order
        priority_env = os.getenv("MODEL_PROVIDER_PRIORITY", "").lower()
        
        if priority_env:
            # Use specified priority
            priority_list = [p.strip() for p in priority_env.split(",")]
            for provider_name in priority_list:
                for provider in ModelProvider:
                    if provider.value == provider_name and provider in self.providers:
                        return provider
        
        # Default priority order
        default_priority = [
            ModelProvider.OPENAI,
            ModelProvider.DEEPSEEK,
            ModelProvider.ANTHROPIC,
            ModelProvider.GROQ,
            ModelProvider.TOGETHER,
            ModelProvider.OLLAMA
        ]
        
        for provider in default_priority:
            if provider in self.providers:
                return provider
        
        return None
    
    def call_model(self, prompt: str, thread_id: str, provider: Optional[ModelProvider] = None) -> str:
        """
        Call the specified model provider or the primary provider.
        
        Args:
            prompt: The input prompt
            thread_id: Thread identifier for logging
            provider: Specific provider to use (if None, uses primary)
            
        Returns:
            Model response text
        """
        if provider is None:
            provider = self.get_primary_provider()
        
        if provider is None:
            return "No model providers are configured. Please check your environment variables."
        
        if provider not in self.providers:
            return f"Model provider '{provider.value}' is not available."
        
        config = self.providers[provider]
        
        try:
            if provider == ModelProvider.OLLAMA:
                return self._call_ollama(prompt, thread_id, config)
            elif provider in [ModelProvider.OPENAI, ModelProvider.GROQ, ModelProvider.TOGETHER, ModelProvider.DEEPSEEK]:
                return self._call_openai_compatible(prompt, thread_id, config, provider)
            elif provider == ModelProvider.ANTHROPIC:
                return self._call_anthropic(prompt, thread_id, config)
            else:
                return f"Provider '{provider.value}' is not implemented yet."
        
        except Exception as e:
            logger.error(f"❌ Error calling {provider.value} for thread {thread_id}: {str(e)}")
            
            # Try fallback provider if primary fails
            if provider != self.get_primary_provider():
                logger.info(f"🔄 Trying fallback provider...")
                return self.call_model(prompt, thread_id, None)
            
            return f"I'm experiencing technical difficulties. Please try again later. (Error: {str(e)[:100]})"
    
    def _call_ollama(self, prompt: str, thread_id: str, config: Dict[str, Any]) -> str:
        """Call Ollama API."""
        payload = {
            "model": config["model"],
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": float(os.getenv("MODEL_TEMPERATURE", "0.7")),
                "top_p": float(os.getenv("MODEL_TOP_P", "0.9")),
                "max_tokens": int(os.getenv("MODEL_MAX_TOKENS", "500"))
            }
        }
        
        timeout = (
            float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "10")),
            float(os.getenv("OLLAMA_REQUEST_TIMEOUT", "180"))
        )
        
        response = requests.post(
            f"{config['base_url']}/api/generate",
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("response", "I couldn't generate a proper response.").strip()
    
    def _call_openai_compatible(self, prompt: str, thread_id: str, config: Dict[str, Any], provider: ModelProvider) -> str:
        """Call OpenAI-compatible APIs (OpenAI, Groq, Together)."""
        
        # Add system message for natural responses
        system_message = {
            "role": "system", 
            "content": "You are a helpful assistant. Respond naturally and conversationally. Do not start responses with 'Assistant:', 'AI:', or similar prefixes. Jump straight into your helpful response."
        }
        
        user_message = {"role": "user", "content": prompt}
        
        payload = {
            "model": config["model"],
            "messages": [system_message, user_message]
        }
        
        # Handle GPT-5 specific parameters and restrictions
        if provider == ModelProvider.OPENAI and config["model"].startswith("gpt-5"):
            # GPT-5 uses max_completion_tokens instead of max_tokens
            payload["max_completion_tokens"] = int(os.getenv("MODEL_MAX_TOKENS", "500"))
            
            # GPT-5 temperature: Based on error, only default (1) is supported
            # Let's not set temperature to use the default
            
            # GPT-5 specific parameters from official docs
            reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT", "medium")
            if reasoning_effort in ["minimal", "low", "medium", "high"]:
                payload["reasoning_effort"] = reasoning_effort
                
            # GPT-5 verbosity parameter (from official docs)
            verbosity = os.getenv("OPENAI_VERBOSITY", "medium")
            if verbosity in ["low", "medium", "high"]:
                payload["verbosity"] = verbosity
                
            # GPT-5 does NOT support top_p parameter (confirmed by error message)
        else:
            # For all other models (GPT-4, GPT-3.5, etc.), use standard parameters
            payload["temperature"] = float(os.getenv("MODEL_TEMPERATURE", "0.7"))
            payload["top_p"] = float(os.getenv("MODEL_TOP_P", "0.9"))
            payload["max_tokens"] = int(os.getenv("MODEL_MAX_TOKENS", "500"))
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}"
        }
        
        timeout = (
            float(os.getenv("API_CONNECT_TIMEOUT", "10")),
            float(os.getenv("API_REQUEST_TIMEOUT", "60"))
        )
        
        response = requests.post(
            f"{config['base_url']}/chat/completions",
            json=payload,
            headers=headers,
            timeout=timeout
        )
        
        if response.status_code != 200:
            error_detail = ""
            try:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                error_detail = f" - {error_message}"
                
                # Handle specific GPT-5 parameter errors and provide suggestions
                if "Unsupported parameter" in error_message:
                    logger.warning(f"🔧 GPT-5 parameter issue detected. Consider updating model configuration.")
                elif "Unsupported value" in error_message and "temperature" in error_message:
                    logger.warning(f"🔧 GPT-5 temperature restriction: Use default temperature (1.0).")
                    
            except:
                error_detail = f" - Raw response: {response.text[:200]}"
            
            logger.error(f"❌ {provider.value.upper()} API error {response.status_code}: {error_detail}")
            logger.error(f"📝 Request payload: {payload}")
            
        response.raise_for_status()
        
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"].strip()
        
        return "I couldn't generate a proper response."
    
    def _call_anthropic(self, prompt: str, thread_id: str, config: Dict[str, Any]) -> str:
        """Call Anthropic Claude API."""
        
        # Anthropic uses system parameter instead of system message
        system_prompt = "You are a helpful assistant. Respond naturally and conversationally. Do not start responses with 'Assistant:', 'AI:', or similar prefixes. Jump straight into your helpful response."
        
        payload = {
            "model": config["model"],
            "max_tokens": int(os.getenv("MODEL_MAX_TOKENS", "500")),
            "temperature": float(os.getenv("MODEL_TEMPERATURE", "0.7")),
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": config["api_key"],
            "anthropic-version": "2023-06-01"
        }
        
        timeout = (
            float(os.getenv("API_CONNECT_TIMEOUT", "10")),
            float(os.getenv("API_REQUEST_TIMEOUT", "60"))
        )
        
        response = requests.post(
            f"{config['base_url']}/v1/messages",
            json=payload,
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()
        
        result = response.json()
        if "content" in result and len(result["content"]) > 0:
            return result["content"][0]["text"].strip()
        
        return "I couldn't generate a proper response."
    
    def get_available_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get information about available providers."""
        return {
            provider.value: {
                "model": config["model"],
                "base_url": config["base_url"],
                "has_api_key": config["api_key"] is not None
            }
            for provider, config in self.providers.items()
        }


# Global model manager instance
model_manager = ModelManager()