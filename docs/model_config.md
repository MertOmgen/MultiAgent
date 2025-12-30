# Model Configuration

## Agent-Specific Models

Each agent uses a specialized Ollama model optimized for its role:

| Agent        | Model                 | Purpose                         | Temperature         |
| ------------ | --------------------- | ------------------------------- | ------------------- |
| **Designer** | `llama3.1:8b`         | Architecture & design decisions | 0.7 (creative)      |
| **Backend**  | `qwen2.5-coder:7b`    | .NET/C# code generation         | 0.5 (balanced)      |
| **Frontend** | `qwen2.5-coder:7b`    | Vue 3 code generation           | 0.5 (balanced)      |
| **QA**       | `deepseek-coder:6.7b` | Testing & validation            | 0.3 (deterministic) |

## Setup Instructions

### 1. Install Ollama

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

### 4. Verify Installation

```bash
ollama list
```

You should see all three models listed.

## Environment Configuration

Copy `.env.example` to `.env` and adjust if needed:

```bash
cp .env.example .env
```

Default configuration:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_DESIGNER=llama3.1:8b
OLLAMA_MODEL_BACKEND=qwen2.5-coder:7b
OLLAMA_MODEL_FRONTEND=qwen2.5-coder:7b
OLLAMA_MODEL_QA=deepseek-coder:6.7b
```

## Model Selection Rationale

- **llama3.1:8b** (Designer): Excellent for reasoning, planning, and architectural decisions
- **qwen2.5-coder:7b** (Backend/Frontend): Specialized in code generation with strong multi-language support
- **deepseek-coder:6.7b** (QA): Strong at code analysis, bug detection, and test case generation

## Customization

To use different models, edit the `.env` file or modify `app/config/llm_config.py`:

```python
AGENT_MODELS = {
    "designer": "your-model:tag",
    "backend": "your-model:tag",
    "frontend": "your-model:tag",
    "qa": "your-model:tag",
}
```

## Troubleshooting

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
