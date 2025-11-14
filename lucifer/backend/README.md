# HuggingFace Multimodal Assistant Backend

This folder contains a small, production-ready FastAPI backend that integrates
Hugging Face Inference API and `datasets` into a clean package layout.

Structure
- `app/main.py` - FastAPI app and HTTP routes (uvicorn entrypoint: `app.main:app`)
- `app/services.py` - `HuggingService` class (dataset loader, ASR, text generation, VQA, any-to-any)
- `app/models.py` - Pydantic request/response models
- `.env.example` - example for `HF_TOKEN`

Quick start

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # or .\.venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Create a `.env` in this folder with your HF token (or export `HF_TOKEN`):

```text
HF_TOKEN=your_hf_token_here
```

3. Run the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Notes
- Don't commit your real `HF_TOKEN` to source control.
- For production: add authentication, logging aggregation, persistent dataset cache, rate-limiting, and async worker queues for expensive jobs.
