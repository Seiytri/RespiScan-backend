"""
Inference service layer.

All calls to the DenseNet + Grad-CAM model must go through this module.
The hosting location (same server, separate microservice, GPU worker) is
intentionally not decided — this abstraction lets us swap it later without
touching any callers.

Treat inference as asynchronous by default — never assume it returns
within a single request/response cycle.
"""

import requests
from urllib.parse import urljoin
from django.conf import settings


def run_inference(image: bytes) -> dict:
    """
    Run pneumonia detection inference on a chest X-ray image.

    This is the single entry point for all inference calls. The actual
    hosting backend (local model, remote GPU service, etc.) will be
    wired in later — callers must not depend on where inference runs.

    Args:
        image: Raw image bytes of the chest X-ray.

    Returns:
        A dict containing at minimum:
        - "prediction": str — e.g. "bacterial_pneumonia", "normal"
        - "confidence": float — model confidence score (0.0–1.0)
        - "gradcam_image": bytes | None — Grad-CAM heatmap overlay, if available
    """
    url = urljoin(settings.INFERENCE_API_URL, "/gradcam")
    
    # Send as multipart/form-data with key 'file'
    files = {"file": ("scan.png", image, "image/png")}
    
    # Add ngrok skip header in case the free tier warning page intercepts the request
    headers = {"ngrok-skip-browser-warning": "true"}
    
    response = requests.post(url, files=files, headers=headers)
    response.raise_for_status()
    
    # The /gradcam endpoint returns the raw PNG image in the body
    # and the metadata in custom headers.
    prediction = response.headers.get("X-Prediction", "Unknown")
    confidence_str = response.headers.get("X-Confidence", "0.0")
    
    try:
        confidence = float(confidence_str)
    except ValueError:
        confidence = 0.0

    return {
        "prediction": prediction,
        "confidence": confidence,
        "gradcam_image": response.content
    }
