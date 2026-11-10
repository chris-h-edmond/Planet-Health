"""Load both trained models and run image-level predictions.

This module deliberately has no HTTP framework dependency. A future backend
endpoint can pass its uploaded image to predict_image and return the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import torch
from PIL import Image, ImageOps
from torch import nn
from torchvision import models, transforms


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GROWTH_CHECKPOINT = PROJECT_ROOT / "artifacts" / "growth" / "growth_model.pth"
DEFAULT_STRESS_CHECKPOINT = PROJECT_ROOT / "artifacts" / "stress" / "stress_model.pth"
DEFAULT_IMAGE_SIZE = 224
DEFAULT_MEAN = (0.485, 0.456, 0.406)
DEFAULT_STD = (0.229, 0.224, 0.225)
STRESS_CLASSES = ("Healthy", "Stressed")


@dataclass
class PlantModels:
    """Loaded models and shared preprocessing ready for repeated predictions."""

    growth_model: nn.Module
    stress_model: nn.Module
    preprocess: transforms.Compose
    device: torch.device


def _build_resnet18(output_count: int) -> nn.Module:
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, output_count)
    return model


def _load_checkpoint(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Model checkpoint not found: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Model checkpoint is empty: {path}")
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict) or "model_state_dict" not in checkpoint:
        raise ValueError(f"Not a supported trained checkpoint: {path}")
    return checkpoint


def _make_preprocess(image_size: int, mean, std) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((int(image_size), int(image_size))),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ]
    )


def load_growth_model(
    model_path: str | Path = DEFAULT_GROWTH_CHECKPOINT,
    device: str | torch.device | None = None,
):
    """Load growth checkpoint; return (model, transform, device)."""
    device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    checkpoint = _load_checkpoint(model_path)
    if checkpoint.get("architecture") != "resnet18_regression":
        raise ValueError("Unsupported growth checkpoint architecture")
    if checkpoint.get("targets") != ["leaf_count", "Age"]:
        raise ValueError("Growth checkpoint target order is missing or unsupported")
    model = _build_resnet18(2)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device).eval()
    preprocess = _make_preprocess(
        checkpoint.get("image_size", DEFAULT_IMAGE_SIZE),
        checkpoint.get("mean", DEFAULT_MEAN),
        checkpoint.get("std", DEFAULT_STD),
    )
    return model, preprocess, device


def load_stress_model(
    model_path: str | Path = DEFAULT_STRESS_CHECKPOINT,
    device: str | torch.device | None = None,
):
    """Load stress checkpoint; return (model, transform, device)."""
    device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    checkpoint = _load_checkpoint(model_path)
    if checkpoint.get("architecture") != "resnet18":
        raise ValueError("Unsupported stress checkpoint architecture")
    classes = checkpoint.get("classes")
    if classes != list(STRESS_CLASSES):
        raise ValueError(f"Unexpected stress class order in checkpoint: {classes}")
    model = _build_resnet18(2)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device).eval()
    preprocess = _make_preprocess(
        checkpoint.get("image_size", DEFAULT_IMAGE_SIZE),
        checkpoint.get("mean", DEFAULT_MEAN),
        checkpoint.get("std", DEFAULT_STD),
    )
    return model, preprocess, device


def load_models(
    growth_checkpoint: str | Path = DEFAULT_GROWTH_CHECKPOINT,
    stress_checkpoint: str | Path = DEFAULT_STRESS_CHECKPOINT,
    device: str | torch.device | None = None,
) -> PlantModels:
    """Load both checkpoints once for serving multiple images."""
    device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    growth_model, growth_preprocess, _ = load_growth_model(growth_checkpoint, device)
    stress_model, stress_preprocess, _ = load_stress_model(stress_checkpoint, device)
    # The checkpoints currently store the same size and ImageNet normalization.
    growth_signature = (
        growth_preprocess.transforms[0].size,
        tuple(growth_preprocess.transforms[2].mean),
        tuple(growth_preprocess.transforms[2].std),
    )
    stress_signature = (
        stress_preprocess.transforms[0].size,
        tuple(stress_preprocess.transforms[2].mean),
        tuple(stress_preprocess.transforms[2].std),
    )
    if growth_signature != stress_signature:
        raise ValueError("Growth and stress checkpoints require different preprocessing")
    return PlantModels(
        growth_model=growth_model,
        stress_model=stress_model,
        preprocess=growth_preprocess,
        device=device,
    )


def _to_rgb_image(image: Image.Image | str | Path | bytes | bytearray | BinaryIO) -> Image.Image:
    """Decode a path, uploaded byte stream, or PIL image and normalize to RGB."""
    if isinstance(image, Image.Image):
        return ImageOps.exif_transpose(image).convert("RGB")
    if isinstance(image, (bytes, bytearray)):
        with Image.open(BytesIO(image)) as opened:
            return ImageOps.exif_transpose(opened).convert("RGB")
    if hasattr(image, "read"):
        with Image.open(image) as opened:
            return ImageOps.exif_transpose(opened).convert("RGB")
    with Image.open(image) as opened:
        return ImageOps.exif_transpose(opened).convert("RGB")


def _make_input_tensor(image, preprocess, device) -> torch.Tensor:
    rgb_image = _to_rgb_image(image)
    return preprocess(rgb_image).unsqueeze(0).to(device)


def predict_growth(
    image: Image.Image | str | Path | bytes | bytearray | BinaryIO,
    model: nn.Module,
    preprocess,
    device: str | torch.device,
) -> dict[str, float | int]:
    """Return predicted leaf count and plant age in days for one image."""
    tensor = _make_input_tensor(image, preprocess, device)
    with torch.inference_mode():
        values = model(tensor)[0].detach().cpu().tolist()
    leaf_count = max(0.0, float(values[0]))
    age_days = max(0.0, float(values[1]))
    return {
        "leaf_count": leaf_count,
        "leaf_count_rounded": int(round(leaf_count)),
        "age_days": age_days,
    }


def predict_stress(
    image: Image.Image | str | Path | bytes | bytearray | BinaryIO,
    model: nn.Module,
    preprocess,
    device: str | torch.device,
) -> dict[str, str | float | dict[str, float]]:
    """Return the binary class and probabilities; score is not stress severity."""
    tensor = _make_input_tensor(image, preprocess, device)
    with torch.inference_mode():
        probabilities = torch.softmax(model(tensor)[0], dim=0).detach().cpu().tolist()
    healthy_probability = float(probabilities[0])
    stressed_probability = float(probabilities[1])
    return {
        "label": "Stressed" if stressed_probability >= healthy_probability else "Healthy",
        "stress_score": stressed_probability,
        "probabilities": {
            "healthy": healthy_probability,
            "stressed": stressed_probability,
        },
    }


def predict_image(
    image: Image.Image | str | Path | bytes | bytearray | BinaryIO,
    models_bundle: PlantModels,
) -> dict:
    """Run both models on one image and return a JSON-serializable result."""
    # Decode and preprocess only once; the trained models use identical inputs.
    tensor = _make_input_tensor(image, models_bundle.preprocess, models_bundle.device)
    with torch.inference_mode():
        growth_values = models_bundle.growth_model(tensor)[0].detach().cpu().tolist()
        stress_probabilities = torch.softmax(
            models_bundle.stress_model(tensor)[0], dim=0
        ).detach().cpu().tolist()

    leaf_count = max(0.0, float(growth_values[0]))
    age_days = max(0.0, float(growth_values[1]))
    healthy_probability = float(stress_probabilities[0])
    stressed_probability = float(stress_probabilities[1])
    return {
        "stress": {
            "label": "Stressed" if stressed_probability >= healthy_probability else "Healthy",
            "stress_score": stressed_probability,
            "score_scale": "0-1",
            "probabilities": {
                "healthy": healthy_probability,
                "stressed": stressed_probability,
            },
        },
        "growth": {
            "leaf_count": leaf_count,
            "leaf_count_rounded": int(round(leaf_count)),
            "age_days": age_days,
        },
    }


# Keep the earlier growth-only loader name available for existing callers.
load_model = load_growth_model
