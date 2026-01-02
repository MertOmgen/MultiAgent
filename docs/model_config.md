# Model Configuration

## Supported Providers

This multi-agent system supports three LLM providers:

1. **OpenAI** - Cloud-based GPT models (requires API key)
2. **z.ai** - Cloud-based AI models via z.ai API (requires API key)
3. **Ollama** - Local models running on your machine (free, requires local setup)

## Agent-Specific Models

### Ollama (Local)

Each agent uses a specialized Ollama model optimized for its role:

| Agent        | Model                 | Purpose                         | Temperature         |
| ------------ | --------------------- | ------------------------------- | ------------------- |
| **Designer** | `llama3.1:8b`         | Architecture & design decisions | 0.7 (creative)      |
| **Backend**  | `qwen2.5-coder:7b`    | .NET/C# code generation         | 0.5 (balanced)      |
| **Frontend** | `qwen2.5-coder:7b`    | Vue 3 code generation           | 0.5 (balanced)      |
| **QA**       | `deepseek-coder:6.7b` | Testing & validation            | 0.3 (deterministic) |

### OpenAI & z.ai (Cloud)

Both OpenAI and z.ai use the same OpenAI-compatible API format. You can configure different models for each agent:

| Agent        | Default Model | Purpose                         | Temperature         |
| ------------ | ------------- | ------------------------------- | ------------------- |
| **Designer** | `gpt-4.1`     | Architecture & design decisions | 0.7 (creative)      |
| **Backend**  | `gpt-4.1`     | .NET/C# code generation         | 0.5 (balanced)      |
| **Frontend** | `gpt-4.1`     | Vue 3 code generation           | 0.5 (balanced)      |
| **QA**       | `gpt-4.1`     | Testing & validation            | 0.3 (deterministic) |

## Setup Instructions

### Option 1: Using z.ai (Recommended for Cloud)

z.ai provides cloud-based AI models with an OpenAI-compatible API.

1. **Get your z.ai API key**

   - Visit https://z.ai to sign up
   - Generate an API key from your dashboard

2. **Configure .env file**

   ```env
   LLM_PROVIDER=zai
   ZAI_API_KEY=your-zai-api-key-here
   # OpenAI-SDK compatible base URL (general):
   ZAI_BASE_URL=https://api.z.ai/api/paas/v4/
   # OR use the Coding endpoint for GLM Coding Plan:
   # ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4/
   # OR omit ZAI_BASE_URL and set: ZAI_ENDPOINT=coding

   ZAI_MODEL_DESIGNER=glm-4.7
   ZAI_MODEL_BACKEND=glm-4.7
   ZAI_MODEL_FRONTEND=glm-4.7
   ZAI_MODEL_QA=glm-4.7
   ```

3. **Start using the system**
   - No additional installation required
   - Models are served from z.ai's cloud infrastructure

### Option 2: Using OpenAI

1. **Get your OpenAI API key**

   - Visit https://platform.openai.com/api-keys
   - Create a new API key

2. **Configure .env file**

   ```env
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your-openai-api-key-here
   OPENAI_BASE_URL=https://api.openai.com/v1
   OPENAI_MODEL_DESIGNER=gpt-4.1
   OPENAI_MODEL_BACKEND=gpt-4.1
   OPENAI_MODEL_FRONTEND=gpt-4.1
   OPENAI_MODEL_QA=gpt-4.1
   ```

3. **Start using the system**
   - No additional installation required
   - Models are served from OpenAI's cloud infrastructure

### Option 3: Using Ollama (Local)

#### 1. Install Ollama

Download and install from: https://ollama.com/

### 2. Start Ollama Service

```bash
ollama serve
```

### 3. Pull Required Models

**Option A: Automated Setup (Recommended)**

```bash
python setup_models.py
```

**Option B: Manual Setup**

```bash
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:7b
ollama pull deepseek-coder:6.7b
```

#### 4. Configure .env file

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_DESIGNER=llama3.1:8b
OLLAMA_MODEL_BACKEND=qwen2.5-coder:7b
OLLAMA_MODEL_FRONTEND=qwen2.5-coder:7b
OLLAMA_MODEL_QA=deepseek-coder:6.7b
```

#### 5. Verify Installation

```bash
ollama list
```

You should see all three models listed.

## Environment Configuration

Copy `.env.example` to `.env` and adjust if needed:

```bash
cp .env.example .env
```

### Provider Selection

Choose your provider by setting `LLM_PROVIDER` in `.env`:

```env
# Options: openai, zai, ollama
LLM_PROVIDER=zai
```

### Configuration Examples

**For z.ai:**

```env
ZAI_API_KEY=your-zai-api-key-here
ZAI_BASE_URL=https://api.z.ai/api/paas/v4/
ZAI_MODEL_DESIGNER=glm-4.7
ZAI_MODEL_BACKEND=glm-4.7
ZAI_MODEL_FRONTEND=glm-4.7
ZAI_MODEL_QA=glm-4.7
```

**For OpenAI:**

```env
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL_DESIGNER=gpt-4.1
OPENAI_MODEL_BACKEND=gpt-4.1
OPENAI_MODEL_FRONTEND=gpt-4.1
OPENAI_MODEL_QA=gpt-4.1
```

**For Ollama (default):**

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_DESIGNER=llama3.1:8b
OLLAMA_MODEL_BACKEND=qwen2.5-coder:7b
OLLAMA_MODEL_FRONTEND=qwen2.5-coder:7b
OLLAMA_MODEL_QA=deepseek-coder:6.7b
```

## Model Selection Rationale

### Ollama Models

- **llama3.1:8b** (Designer): Excellent for reasoning, planning, and architectural decisions
- **qwen2.5-coder:7b** (Backend/Frontend): Specialized in code generation with strong multi-language support
- **deepseek-coder:6.7b** (QA): Strong at code analysis, bug detection, and test case generation

### Cloud Models (OpenAI & z.ai)

- **gpt-4.1**: Advanced reasoning and code generation capabilities
- You can customize to use other available models like `gpt-4`, `gpt-3.5-turbo`, etc.
- Check your provider's documentation for available models

## Customization

### Using Different Models

To use different models, edit the `.env` file:

**For z.ai:**

```env
ZAI_MODEL_DESIGNER=your-model-name
ZAI_MODEL_BACKEND=your-model-name
ZAI_MODEL_FRONTEND=your-model-name
ZAI_MODEL_QA=your-model-name
```

**For OpenAI:**

```env
OPENAI_MODEL_DESIGNER=your-model-name
OPENAI_MODEL_BACKEND=your-model-name
OPENAI_MODEL_FRONTEND=your-model-name
OPENAI_MODEL_QA=your-model-name
```

**For Ollama:**

```env
OLLAMA_MODEL_DESIGNER=your-model:tag
OLLAMA_MODEL_BACKEND=your-model:tag
OLLAMA_MODEL_FRONTEND=your-model:tag
OLLAMA_MODEL_QA=your-model:tag
```

### Mixing Providers

Currently, the system uses a single provider for all agents. To mix providers (e.g., z.ai for designer, Ollama for backend), you would need to modify [`app/config/llm_config.py`](app/config/llm_config.py) to support per-agent provider selection.

## Troubleshooting

### z.ai Issues

**Invalid API key:**

- Verify your z.ai API key is correct
- Check that the key has sufficient permissions
- Ensure the key hasn't expired

**Connection errors:**

- Verify `ZAI_BASE_URL` is correct
- Check your internet connection
- Ensure z.ai services are operational

### OpenAI Issues

**Invalid API key:**

- Verify your OpenAI API key is correct
- Check that the key has sufficient permissions
- Ensure you have credits in your OpenAI account

**Rate limiting:**

- OpenAI has rate limits on API calls
- Consider upgrading your plan if you hit limits frequently

### Ollama Issues

**Ollama not found:**

- Ensure Ollama is installed and in your PATH
- Try `ollama --version` to verify

**Model pull fails:**

- Check internet connection
- Verify disk space (models are 4-8GB each)
- Try pulling one model at a time manually

**Connection refused:**

- Ensure `ollama serve` is running
- Check `OLLAMA_BASE_URL` in `.env` matches your Ollama server

### General Issues

**Provider not recognized:**

- Ensure `LLM_PROVIDER` is set to `openai`, `zai`, or `ollama` (case-insensitive)
- Check for typos in your `.env` file

**Model not found:**

- Verify the model name is correct for your provider
- Check that the model is available in your provider's catalog
- For Ollama, ensure you've pulled the model locally
