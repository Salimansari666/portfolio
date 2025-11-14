import logging
from typing import Optional, Dict, Any
from huggingface_hub import InferenceClient
from datasets import load_dataset, Dataset

logger = logging.getLogger(__name__)


class HuggingService:
    """Service that wraps Hugging Face InferenceClient and datasets loader.

    Methods are synchronous (so they can be called via asyncio.to_thread in FastAPI).
    """

    def __init__(self, hf_token: str):
        if not hf_token:
            raise ValueError("HF_TOKEN is required")
        self.client = InferenceClient(token=hf_token)
        self._datasets: Dict[str, Dataset] = {}
        self.supported = {
            "openai/gsm8k": ["main", "socratic"],
            "mrmrx/CADS-dataset": ["0001_visceral_gc", "0002_visceral_sc", "0003_kits21"],
            "openai/gdpval": [None],
            "kraina/airbnb": ["all", "weekdays", "weekends"],
        }

    def _key(self, name: str, subset: Optional[str]) -> str:
        return f"{name}::{subset or ''}"

    def load_dataset(self, name: str, subset: Optional[str] = None, streaming: bool = False) -> Dict[str, Any]:
        key = self._key(name, subset)
        if key in self._datasets:
            logger.info("Dataset cached: %s", key)
            ds = self._datasets[key]
        else:
            logger.info("Loading dataset %s subset=%s streaming=%s", name, subset, streaming)
            ds = load_dataset(name, subset) if subset else load_dataset(name)
            self._datasets[key] = ds

        # Return lightweight info
        info: Dict[str, Any] = {"key": key, "type": type(ds).__name__}
        try:
            if hasattr(ds, "keys"):
                info["splits"] = list(ds.keys())
                info["size_per_split"] = {k: len(ds[k]) for k in ds.keys()}
            else:
                info["length"] = len(ds)
            info["features"] = getattr(ds, "features", None)
        except Exception:
            logger.exception("Failed to summarize dataset %s", key)
        return info

    def generate_text(self, prompt: str, model: str = "gpt2", max_new_tokens: int = 200, **kwargs) -> str:
        logger.debug("generate_text model=%s tokens=%s", model, max_new_tokens)
        res = self.client.text_generation(model=model, inputs=prompt, parameters={"max_new_tokens": int(max_new_tokens), **kwargs})
        if isinstance(res, list) and res:
            first = res[0]
            if isinstance(first, dict) and "generated_text" in first:
                return first["generated_text"]
            return str(first)
        return str(res)

    def transcribe_audio(self, audio_bytes: bytes, model: str = "openai/whisper-large-v2") -> str:
        logger.debug("transcribe_audio model=%s bytes=%d", model, len(audio_bytes))
        res = self.client.automatic_speech_recognition(model=model, inputs=audio_bytes)
        if isinstance(res, dict) and "text" in res:
            return res["text"]
        return str(res)

    def analyze_image(self, image_bytes: bytes, model: str = "Salesforce/blip-image-captioning-large") -> str:
        logger.debug("analyze_image model=%s bytes=%d", model, len(image_bytes))
        res = self.client.image_to_text(model=model, inputs=image_bytes)
        return str(res)

    def multimodal_vqa(self, image_bytes: bytes, question: str, model: str = "dandelin/vilt-b32-finetuned-vqa") -> str:
        logger.debug("multimodal_vqa model=%s question=%s", model, question)
        res = self.client.visual_question_answering(model=model, image=image_bytes, question=question)
        return str(res)

    def any_to_any(self, *, input_type: str, output_type: str, payload: Any, model: Optional[str] = None) -> Any:
        logger.debug("any_to_any %s->%s model=%s", input_type, output_type, model)
        if input_type == "audio" and output_type == "text":
            return self.transcribe_audio(payload, model=model or "openai/whisper-large-v2")
        if input_type == "image" and output_type == "caption":
            return self.analyze_image(payload, model=model or "Salesforce/blip-image-captioning-large")
        if input_type == "image" and output_type == "vqa":
            question = payload.get("question") if isinstance(payload, dict) else None
            if not question:
                raise ValueError("Missing question for image->vqa")
            image = payload if isinstance(payload, (bytes, bytearray)) else payload.get("image")
            return self.multimodal_vqa(image, question, model=model or "dandelin/vilt-b32-finetuned-vqa")
        if input_type == "text" and output_type == "text":
            return self.generate_text(payload, model=model or "gpt2")
        raise ValueError(f"Unsupported conversion {input_type}->{output_type}")
