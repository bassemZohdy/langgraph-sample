# Model Provider Configuration Guide

This LangGraph agent supports multiple AI model providers with automatic failover and priority-based selection.

## Supported Providers

### 1. OpenAI (Default Priority #1)
- **Default Model**: `gpt-5-nano` (OpenAI's latest cheapest model from GPT-5 series)
- **GPT-5 Features**: 272k token context, built-in reasoning, minimal reasoning mode, verbosity control, 94.6% on AIME 2025
- **Environment Variables**:
  ```bash
  OPENAI_API_KEY=sk-your-openai-api-key-here
  OPENAI_MODEL=gpt-5-nano
  OPENAI_BASE_URL=https://api.openai.com/v1
  ```
- **Available Models**: `gpt-5`, `gpt-5-mini`, `gpt-5-nano`

### 2. DeepSeek (Default Priority #2)
- **Default Model**: `deepseek-r1` (DeepSeek's reasoning model)
- **Environment Variables**:
  ```bash
  DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
  DEEPSEEK_MODEL=deepseek-r1
  DEEPSEEK_BASE_URL=https://api.deepseek.com
  ```

### 3. Anthropic Claude (Default Priority #3)
- **Default Model**: `claude-3-haiku-20240307`
- **Environment Variables**:
  ```bash
  ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
  ANTHROPIC_MODEL=claude-3-haiku-20240307
  ANTHROPIC_BASE_URL=https://api.anthropic.com
  ```

### 4. Groq (Default Priority #4)
- **Default Model**: `llama3-8b-8192`
- **Environment Variables**:
  ```bash
  GROQ_API_KEY=gsk_your-groq-api-key-here
  GROQ_MODEL=llama3-8b-8192
  GROQ_BASE_URL=https://api.groq.com/openai/v1
  ```

### 5. Together AI (Default Priority #5)
- **Default Model**: `meta-llama/Llama-2-7b-chat-hf`
- **Environment Variables**:
  ```bash
  TOGETHER_API_KEY=your-together-api-key-here
  TOGETHER_MODEL=meta-llama/Llama-2-7b-chat-hf
  TOGETHER_BASE_URL=https://api.together.xyz/v1
  ```

### 6. Ollama (Default Priority #6)
- **Default Model**: `llama3.2:1b` (Minimal local model)
- **Environment Variables**:
  ```bash
  OLLAMA_BASE_URL=http://ollama:11434
  OLLAMA_MODEL=llama3.2:1b
  ```

## Configuration

### Setting Provider Priority
You can customize which providers are tried first by setting:
```bash
MODEL_PROVIDER_PRIORITY=openai,deepseek,anthropic,groq,together,ollama
```

### Model Parameters
Global settings that apply to all providers:
```bash
MODEL_TEMPERATURE=0.7
MODEL_TOP_P=0.9
MODEL_MAX_TOKENS=500
```

## How It Works

1. **Automatic Detection**: The system scans environment variables to detect available providers
2. **Priority Selection**: Uses the first available provider from the priority list
3. **Failover**: If the primary provider fails, automatically tries the next available provider
4. **Logging**: All provider status and switching is logged for debugging

## Usage Examples

### Development (Local Only)
```bash
# Use only local Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b
MODEL_PROVIDER_PRIORITY=ollama
```

### Production (Cloud First, Local Fallback)
```bash
# Primary: OpenAI, Fallback: Local
OPENAI_API_KEY=sk-your-key
OLLAMA_BASE_URL=http://ollama:11434
MODEL_PROVIDER_PRIORITY=openai,ollama
```

### Multi-Provider Setup
```bash
# Multiple cloud providers for redundancy
OPENAI_API_KEY=sk-your-openai-key
DEEPSEEK_API_KEY=sk-your-deepseek-key
ANTHROPIC_API_KEY=sk-ant-your-claude-key
MODEL_PROVIDER_PRIORITY=openai,deepseek,anthropic
```

## Model Recommendations

### For Cost Efficiency (GPT-5 Series 2025)
- **OpenAI**: `gpt-5-nano` ($0.05/1M input, $0.40/1M output - cheapest GPT-5)
- **OpenAI**: `gpt-5-mini` ($0.25/1M input, $2/1M output - balanced cost/performance)
- **DeepSeek**: `deepseek-r1` (Reasoning specialist)
- **Local**: `llama3.2:1b` (Minimal resource usage)

### For Performance (GPT-5 Series 2025)
- **OpenAI**: `gpt-5` ($1.25/1M input, $10/1M output - flagship model)
- **OpenAI**: `gpt-5-mini` (Good performance at lower cost)
- **Anthropic**: `claude-3-5-sonnet-20241022`
- **Groq**: `llama3-70b-8192`

### For Reasoning Tasks (GPT-5 Series 2025)
- **OpenAI**: `gpt-5` (94.6% on AIME 2025, 74.9% on SWE-bench, built-in reasoning)
- **OpenAI**: `gpt-5-mini` (GPT-5 reasoning at lower cost)
- **DeepSeek**: `deepseek-r1` (Specialized for reasoning)
- **OpenAI**: `o3` (Dedicated reasoning model)
- **Anthropic**: `claude-3-5-sonnet-20241022`

## Getting API Keys

1. **OpenAI**: https://platform.openai.com/api-keys
2. **DeepSeek**: https://platform.deepseek.com/
3. **Anthropic**: https://console.anthropic.com/
4. **Groq**: https://console.groq.com/keys
5. **Together AI**: https://api.together.xyz/settings/api-keys
6. **Ollama**: No API key required (self-hosted)