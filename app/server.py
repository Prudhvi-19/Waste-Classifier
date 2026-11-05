"""HTTP interface for the legacy fast.ai v1 waste classifier."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_IMAGE_BYTES + 64 * 1024
MAX_IMAGE_PIXELS = 16_000_000
logger = logging.getLogger(__name__)


def validate_image(data):
    with Image.open(BytesIO(data)) as image:
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise ValueError("Image dimensions are too large")
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError("Use a JPEG, PNG, or WebP image")
        image.verify()


def create_app(predictor=None, model_path=None):
    """Allow injected predictors for tests; production loads a trusted local export."""
    @asynccontextmanager
    async def lifespan(app):
        app.state.predictor = predictor
        app.state.predict_lock = asyncio.Lock()
        if predictor is None:
            from app.inference import load_predictor

            location = Path(model_path or os.environ.get("MODEL_PATH", ROOT / "export.pkl"))
            try:
                app.state.predictor = await run_in_threadpool(load_predictor, location)
            except Exception:
                logger.exception("Cannot load classifier; provide a trusted fast.ai v1 export via MODEL_PATH")
        yield

    async def homepage(request):
        return HTMLResponse((ROOT / "view" / "index.html").read_text())

    async def health(request):
        ready = request.app.state.predictor is not None
        return JSONResponse({"status": "ok" if ready else "model_unavailable"}, status_code=200 if ready else 503)

    async def analyze(request):
        if request.app.state.predictor is None:
            return JSONResponse({"error": "Classifier model is unavailable"}, status_code=503)

        # Bound the complete body before multipart parsing, including chunked uploads.
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_REQUEST_BYTES:
                return JSONResponse({"error": "Upload is too large"}, status_code=413)
            body.extend(chunk)

        async def receive():
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        bounded_request = Request(request.scope, receive)
        async with bounded_request.form(max_files=1, max_fields=0, max_part_size=MAX_IMAGE_BYTES) as form:
            upload = form.get("file")
            if not isinstance(upload, UploadFile):
                return JSONResponse({"error": "Provide one image in the file field"}, status_code=400)
            data = await upload.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                return JSONResponse({"error": "Image is too large"}, status_code=413)
            try:
                await run_in_threadpool(validate_image, data)
            except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
                return JSONResponse({"error": "Provide a valid JPEG, PNG, or WebP image within the size limit"}, status_code=400)

        # fast.ai mutates learner state. Serialize calls and keep CPU work off the event loop.
        async with request.app.state.predict_lock:
            prediction = await run_in_threadpool(request.app.state.predictor, data)
        return JSONResponse({"result": str(prediction)})

    return Starlette(
        lifespan=lifespan,
        routes=[
            Route("/", homepage),
            Route("/health", health),
            Route("/analyze", analyze, methods=["POST"]),
            Mount("/static", StaticFiles(directory=ROOT / "static")),
        ],
        middleware=[Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["X-Requested-With", "Content-Type"])],
    )


app = create_app()
