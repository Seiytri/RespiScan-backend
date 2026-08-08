"""
Inference service layer.

All calls to the DenseNet + Grad-CAM model must go through this module.
The hosting location (same server, separate microservice, GPU worker) is
intentionally not decided — this abstraction lets us swap it later without
touching any callers.

Treat inference as asynchronous by default — never assume it returns
within a single request/response cycle.
"""


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

    Raises:
        NotImplementedError: Stub — not yet implemented.
    """
    raise NotImplementedError(
        "Inference hosting is not yet decided. "
        "Do not hardcode an inference location — see GEMINI.md."
    )
