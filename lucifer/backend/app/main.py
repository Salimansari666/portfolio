import asyncio
import logging
import os
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

from .services import HuggingService
from .models import ChatRequest

logger = logging.getLogger("backend.app")

# Load environment and tokens
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
API_KEY = os.getenv("API_KEY")

# Construct service if possible
service = HuggingService(HF_TOKEN) if HF_TOKEN else None

app = FastAPI(title="HuggingFace Multimodal Assistant Backend")

# Thread pool for blocking tasks
IO_POOL = ThreadPoolExecutor(max_workers=4)


async def run_blocking(fn, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(IO_POOL, lambda: fn(*args, **kwargs))


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    # Allow health check without key
    if request.url.path == "/health":
        return await call_next(request)

    if not API_KEY:
        # No API key configured; allow but log
        logger.warning("API_KEY not configured; endpoints are unprotected")
        return await call_next(request)

    provided = request.headers.get("x-api-key") or request.headers.get("X-API-KEY")
    if provided != API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized - invalid API key"})
    return await call_next(request)


@app.post("/dataset")
async def load_any_dataset(name: str = Form(...), subset: Optional[str] = Form(None), streaming: Optional[bool] = Form(False)):
    if service is None:
        raise HTTPException(status_code=500, detail="HF_TOKEN not configured on server")
    try:
        info = await run_blocking(service.load_dataset, name, subset, streaming)
        return {"status": "success", "dataset": info}
    except Exception as e:
        logger.exception("Dataset load failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat_endpoint(body: ChatRequest):
    if service is None:
        raise HTTPException(status_code=500, detail="HF_TOKEN not configured on server")
    try:
        model = body.model or "gpt2"
        text = await run_blocking(service.generate_text, body.prompt, model, body.max_new_tokens)
        return {"status": "success", "model": model, "output": text}
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice")
async def voice_to_text(file: UploadFile = File(...)):
    if service is None:
        raise HTTPException(status_code=500, detail="HF_TOKEN not configured on server")
    try:
        audio = await file.read()
        text = await run_blocking(service.transcribe_audio, audio)
        return {"status": "success", "text": text}
    except Exception as e:
        logger.exception("Voice error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/image")
async def image_to_text(file: UploadFile = File(...), model: Optional[str] = Form(None)):
    if service is None:
        raise HTTPException(status_code=500, detail="HF_TOKEN not configured on server")
    try:
        content = await file.read()
        model_name = model or "Salesforce/blip-image-captioning-large"
        caption = await run_blocking(service.analyze_image, content, model_name)
        return {"status": "success", "model": model_name, "caption": caption}
    except Exception as e:
        logger.exception("Image error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vqa")
async def vqa_endpoint(file: UploadFile = File(...), question: str = Form(...), model: Optional[str] = Form(None)):
    if service is None:
        raise HTTPException(status_code=500, detail="HF_TOKEN not configured on server")
    try:
        image_bytes = await file.read()
        model_name = model or "dandelin/vilt-b32-finetuned-vqa"
        ans = await run_blocking(service.multimodal_vqa, image_bytes, question, model_name)
        return {"status": "success", "model": model_name, "answer": ans}
    except Exception as e:
        logger.exception("VQA error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/any-to-any")
async def any_to_any_endpoint(input_type: str = Form(...), output_type: str = Form(...), model: Optional[str] = Form(None), file: UploadFile = File(None), text: Optional[str] = Form(None), question: Optional[str] = Form(None)):
    if service is None:
        raise HTTPException(status_code=500, detail="HF_TOKEN not configured on server")
    try:
        payload = None
        if file:
            payload = await file.read()
            if input_type == "image" and output_type == "vqa":
                payload = {"image": payload, "question": question}
        elif text is not None:
            payload = text
        else:
            raise HTTPException(status_code=400, detail="No valid payload provided")

        result = await run_blocking(service.any_to_any, input_type=input_type, output_type=output_type, payload=payload, model=model)
        return {"status": "success", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("any-to-any error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup():
    logger.info("Starting backend app. Supported dataset templates: %s", service.supported if service else {})


@app.get("/ready")
async def ready():
    """Readiness probe: returns 200 when the service has been constructed
    and can accept lightweight requests. This does not perform heavy model calls.
    """
    ok = service is not None
    if not ok:
        raise HTTPException(status_code=503, detail="service not ready: HF_TOKEN missing")
    return {"status": "ready"}
import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from concurrent.futures import ThreadPoolExecutor
import os

from .services import HuggingService
from .models import ChatRequest, DatasetRequest, VQARequest, AnyToAnyRequest

logger = logging.getLogger("backend.app")

# Read HF token from env
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    logger.error("HF_TOKEN not set. Please set HF_TOKEN in environment or .env file.")
    # do not raise here to allow import in tests, but endpoints will fail clearly

# Create service (will raise inside if token missing at call time)
service = HuggingService(HF_TOKEN) if HF_TOKEN else None

app = FastAPI(title="HuggingFace Multimodal Assistant Backend")

# Thread pool for dataset and blocking IO
IO_POOL = ThreadPoolExecutor(max_workers=4)


async def run_blocking(fn, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(IO_POOL, lambda: fn(*args, **kwargs))


@app.post("/dataset")
async def load_any_dataset(name: str = Form(...), subset: Optional[str] = Form(None), streaming: Optional[bool] = Form(False)):
    if service is None:
        raise HTTPException(status_code=500, detail="HF_TOKEN not configured on server")
    try:
        info = await run_blocking(service.load_dataset, name, subset, streaming)
        return {"status": "success", "dataset": info}
    except Exception as e:
        logger.exception("Dataset load failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat_endpoint(body: ChatRequest):
    if service is None:
        raise HTTPException(status_code=500, detail="HF_TOKEN not configured on server")
    try:
        model = body.model or "gpt2"
        text = await run_blocking(service.generate_text, body.prompt, model, body.max_new_tokens)
        return {"status": "success", "model": model, "output": text}
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice")
async def voice_to_text(file: UploadFile = File(...)):
    if service is None:
        raise HTTPException(status_code=500, detail="HF_TOKEN not configured on server")
    try:
        audio = await file.read()
        text = await run_blocking(service.transcribe_audio, audio)
        return {"status": "success", "text": text}
    except Exception as e:
        logger.exception("Voice error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/image")
async def image_to_text(file: UploadFile = File(...), model: Optional[str] = Form(None)):
    if service is None:
        raise HTTPException(status_code=500, detail="HF_TOKEN not configured on server")
    try:
        content = await file.read()
        model_name = model or "Salesforce/blip-image-captioning-large"
        caption = await run_blocking(service.analyze_image, content, model_name)
        return {"status": "success", "model": model_name, "caption": caption}
    except Exception as e:
        logger.exception("Image error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vqa")
async def vqa_endpoint(file: UploadFile = File(...), question: str = Form(...), model: Optional[str] = Form(None)):
    if service is None:
        raise HTTPException(status_code=500, detail="HF_TOKEN not configured on server")
    try:
        image_bytes = await file.read()
        model_name = model or "dandelin/vilt-b32-finetuned-vqa"
        ans = await run_blocking(service.multimodal_vqa, image_bytes, question, model_name)
        return {"status": "success", "model": model_name, "answer": ans}
    except Exception as e:
        logger.exception("VQA error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/any-to-any")
async def any_to_any_endpoint(input_type: str = Form(...), output_type: str = Form(...), model: Optional[str] = Form(None), file: UploadFile = File(None), text: Optional[str] = Form(None), question: Optional[str] = Form(None)):
    if service is None:
        raise HTTPException(status_code=500, detail="HF_TOKEN not configured on server")
    try:
        payload = None
        if file:
            payload = await file.read()
            if input_type == "image" and output_type == "vqa":
                payload = {"image": payload, "question": question}
        elif text is not None:
            payload = text
        else:
            raise HTTPException(status_code=400, detail="No valid payload provided")

        result = await run_blocking(service.any_to_any, input_type=input_type, output_type=output_type, payload=payload, model=model)
        return {"status": "success", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("any-to-any error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup():
    logger.info("Starting backend app. Supported dataset templates: %s", service.supported if service else {})
