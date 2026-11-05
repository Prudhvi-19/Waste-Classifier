"""Compatibility loader for trusted fast.ai v1 exports on current PyTorch."""
from io import BytesIO
from pathlib import Path


def load_predictor(model_path):
    model_path = Path(model_path)
    if not model_path.is_file():
        raise FileNotFoundError(f"Missing fast.ai v1 model: {model_path}")

    import torch
    from app.fastai_compat import import_fastai_vision

    import_fastai_vision()
    from fastai.basic_train import LabelLists, load_callback
    from fastai.vision import open_image

    # Adapted from fastai 1.0.61 basic_train.load_learner. A v1 export contains
    # Python objects, not just weights. Only operator-provided local files may
    # reach this call. Never pass uploads or download untrusted pickle files.
    # Keep this opt-out local; do not weaken torch.load globally.
    state = torch.load(model_path, map_location="cpu", weights_only=False)
    model = state.pop("model")
    source = LabelLists.load_state(model_path.parent, state.pop("data"))
    data = source.databunch(num_workers=0, device=torch.device("cpu"))
    callback_state = state.pop("cb_state")
    learner_class = state.pop("cls")
    learner = learner_class(data, model, **state)
    learner.callback_fns = state["callback_fns"]
    learner.callbacks = [load_callback(cls, values, learner) for cls, values in callback_state.items()]

    def predict(image_bytes):
        return str(learner.predict(open_image(BytesIO(image_bytes)))[0])

    return predict
