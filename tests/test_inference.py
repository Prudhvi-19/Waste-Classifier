from io import BytesIO

import torch
import pytest
from PIL import Image
from starlette.testclient import TestClient

from app.inference import load_predictor
from app.server import create_app


@pytest.mark.parametrize("architecture", ["linear", "resnet18"])
def test_real_fastai_export_reload_and_http_prediction(tmp_path, architecture):
    """Real CPU inference, not a mock; this does not validate the missing trained model."""
    from app.fastai_compat import import_fastai_vision

    import_fastai_vision()
    from fastai.vision import CrossEntropyFlat, Flatten, ImageDataBunch, Learner, cnn_learner, models, open_image

    torch.manual_seed(42)
    torch.set_num_threads(1)
    for split in ("train", "valid"):
        for label, color in (("O", "green"), ("R", "blue")):
            directory = tmp_path / split / label
            directory.mkdir(parents=True)
            for index in range(2):
                Image.new("RGB", (32, 32), color).save(directory / f"{index}.png")
    data = ImageDataBunch.from_folder(tmp_path, size=32, bs=2, num_workers=0)
    if architecture == "resnet18":
        learner = cnn_learner(data, models.resnet18, pretrained=False)
    else:
        learner = Learner(data, torch.nn.Sequential(Flatten(), torch.nn.Linear(3 * 32 * 32, 2)), loss_func=CrossEntropyFlat())
    image_bytes = (tmp_path / "valid" / "O" / "0.png").read_bytes()
    expected = str(learner.predict(open_image(BytesIO(image_bytes)))[0])
    assert expected in {"O", "R"}
    model_path = tmp_path / "export.pkl"
    learner.export(model_path)
    original_load = torch.load
    predictor = load_predictor(model_path)
    assert torch.load is original_load  # No process-wide security override.
    assert predictor(image_bytes) == expected
    with TestClient(create_app(model_path=model_path)) as client:
        assert client.get("/health").status_code == 200
        response = client.post("/analyze", files={"file": ("sample.png", image_bytes, "image/png")})
        assert response.status_code == 200
        assert response.json() == {"result": expected}
