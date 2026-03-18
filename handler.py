"""
RunPod Serverless Handler for ComfyUI + LTX Video 2.3 22B FP8
Accepts a ComfyUI workflow (JSON) and returns generated video/audio as base64.
"""

import runpod
import time
import base64
import os
import subprocess
import requests
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_DIR = os.environ.get("COMFYUI_DIR", "/workspace/ComfyUI")
OUTPUT_DIR = Path(COMFYUI_DIR) / "output"


# ── Initialise once at worker start (outside the handler) ─────────────────

def _start_comfyui():
    """Launch ComfyUI as a background process and wait until it is ready."""
    print("[init] Starting ComfyUI in background...")
    subprocess.Popen(
        [
            "python", "main.py",
            "--listen", "0.0.0.0",
            "--port", "8188",
            "--disable-auto-launch",
            "--cuda-malloc",
        ],
        cwd=COMFYUI_DIR,
    )
    _wait_for_comfyui(timeout=120)
    print("[init] ComfyUI is ready.")


def _wait_for_comfyui(timeout: int = 120):
    """Block until the ComfyUI REST API is reachable."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{COMFYUI_URL}/system_stats", timeout=3)
            if r.status_code == 200:
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    raise RuntimeError("ComfyUI did not start within timeout.")


# Download models if not already present, then start ComfyUI.
def _download_models():
    script = "/workspace/download_model.sh"
    if os.path.exists(script):
        print("[init] Running download_model.sh...")
        subprocess.run(["bash", script], check=True)
    else:
        print("[init] download_model.sh not found, skipping.")

_download_models()
_start_comfyui()


# ── Helpers ────────────────────────────────────────────────────────────────

def _queue_prompt(workflow: dict) -> str:
    r = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
    r.raise_for_status()
    return r.json()["prompt_id"]


def _wait_for_completion(prompt_id: str, timeout: int = 600) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
        if r.status_code == 200:
            history = r.json()
            if prompt_id in history:
                return history[prompt_id]["outputs"]
        time.sleep(3)
    raise TimeoutError(f"Prompt {prompt_id} timed out after {timeout}s.")


def _collect_output_files(outputs: dict) -> list:
    results = []
    for node_output in outputs.values():
        for key in ("images", "gifs", "videos", "audio"):
            for item in node_output.get(key, []):
                filename = item.get("filename", "")
                filepath = OUTPUT_DIR / filename
                if filepath.exists():
                    with open(filepath, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("utf-8")
                    ext = filepath.suffix.lower().lstrip(".")
                    if ext in ("mp4", "webm", "gif"):
                        media_type = "video"
                    elif ext in ("wav", "mp3", "flac", "ogg"):
                        media_type = "audio"
                    else:
                        media_type = "image"
                    results.append({
                        "type": media_type,
                        "filename": filename,
                        "mime": f"{media_type}/{ext}",
                        "data": encoded,
                    })
    return results


# ── Handler ────────────────────────────────────────────────────────────────

def handler(job):
    """
    Expected job input:
        { "workflow": { ...ComfyUI API-format JSON... }, "timeout": 300 }
    Returns:
        { "prompt_id": "...", "outputs": [ { "type", "filename", "mime", "data" } ] }
    """
    job_input = job.get("input", {})
    workflow = job_input.get("workflow")
    timeout = int(job_input.get("timeout", 300))

    if not workflow:
        return {"error": "Missing 'workflow' in job input."}

    try:
        runpod.serverless.progress_update(job, "Queuing workflow in ComfyUI...")
        prompt_id = _queue_prompt(workflow)

        runpod.serverless.progress_update(job, f"Running inference (prompt: {prompt_id})...")
        outputs = _wait_for_completion(prompt_id, timeout=timeout)

        runpod.serverless.progress_update(job, "Collecting output files...")
        files = _collect_output_files(outputs)

        if not files:
            return {"error": "No output files found.", "prompt_id": prompt_id}

        return {"prompt_id": prompt_id, "outputs": files}

    except Exception as e:
        return {"error": str(e)}


# ── RunPod entrypoint — must be at module top level, NOT inside __main__ ──
runpod.serverless.start({"handler": handler})
