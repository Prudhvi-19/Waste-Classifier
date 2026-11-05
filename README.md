# Waste Classifier

A Starlette image-upload application serving a **fast.ai v1** classifier. The
`POST /analyze` API returns `{"result": "O"}` or `{"result": "R"}`, using the
class labels saved in the model.

## Runtime and model

The tested target is **Python 3.11 on Linux x86_64, CPU only**. The dependency
lock includes patched web libraries and current CPU PyTorch wheels while keeping
fast.ai 1.0.61 and NumPy 1.26.4 for the legacy model format. fast.ai v2 exports
are not interchangeable with v1 exports.

The original Google Drive model link returned **404** during the November 4,
2026 maintenance check, including through the connected Drive account. The
trained model is not in this repository. Its accuracy and compatibility with
this runtime remain unverified; the tests exercise generated v1 exports,
including a ResNet-18 model.

Provide a **trusted, operator-controlled** `export.pkl` using `MODEL_PATH`, or
place it at `app/export.pkl` for local runs. A v1 export is executable Python
pickle data. Never use a file from an untrusted source or an HTTP upload as a
model. The application no longer downloads or executes model files during a
Docker build or module import.

Without a usable model, the page and static files remain available;
`GET /health` and `POST /analyze` return HTTP 503. A missing model is never
replaced with a dummy classifier in production.

## Run with Docker

```sh
docker build --platform linux/amd64 -t waste-classifier .
docker run --rm -p 5000:5000 \
  --mount type=bind,source="$(pwd)/export.pkl",target=/models/export.pkl,readonly \
  -e MODEL_PATH=/models/export.pkl \
  waste-classifier
```

The model file must be readable by container UID 10001. `PORT` defaults to 5000;
the container respects the platform-provided `PORT` value. The container runs
as a non-root user. It does not include model files from the build context.

For a Render deployment, use this Dockerfile and provision a trusted model on a
persistent disk, then set `MODEL_PATH`. Use `/health` as the readiness check.
No current Render service or deployment configuration has been verified.

## Run locally and validate

On the supported Linux/Python target:

```sh
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements.txt
MODEL_PATH=/absolute/path/export.pkl uvicorn app.server:app --port 5000 --limit-concurrency 16
```

```sh
python -m pip install -r requirements-dev.txt
python -m pip check
python -m pytest -q
pip-audit --disable-pip --no-deps -r requirements.txt
node --check app/static/client.js
```

Uploads are limited to one JPEG, PNG, or WebP image, 8 MiB and 16 million pixels.
Inference runs on a worker thread and is serialized because the v1 learner
mutates prediction state. The JSON success response and browser upload flow are
preserved; invalid uploads and unavailable models show an error.

## Dependency maintenance

Edit `requirements.in`, then regenerate the complete hash-locked runtime:

```sh
uv pip compile requirements.in --python-version 3.11 --torch-backend cpu \
  --generate-hashes --emit-index-url --index-strategy unsafe-best-match \
  -o requirements.txt
```

All installed versions and hashes must be reviewed after regeneration; the two
indexes are PyPI and the official PyTorch CPU index. Run the full validation
commands before accepting updates. The CI workflow also builds and smoke-tests
the container. See [the security maintenance record](docs/security-maintenance.md)
for advisory coverage and remaining limitations.
