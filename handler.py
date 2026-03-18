"""
RunPod Handler for ComfyUI + LTX Video 2.3 22B FP8

Two modes, selected automatically:
  Pod mode     (RUNPOD_SERVERLESS unset): ComfyUI starts in the foreground.
               Access via browser: https://<pod-id>-8188.proxy.runpod.net
               ComfyUI Manager is available in the menu.

  Serverless   (RUNPOD_SERVERLESS=1): ComfyUI starts in the background.
               Send workflow JSON via RunPod API, get Base64 video/audio back.
"""

import runpod
import time
import base64
import os
import subprocess
import requests
import sys
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_DIR = os.environ.get("COMFYUI_DIR", "/workspace/ComfyUI")
OUTPUT_DIR  = Path(COMFYUI_DIR) / "output"
SERVERLESS  = os.environ.get("RUNPOD_SERVERLESS", "").strip() == "1"


# ── Init helpers ───────────────────────────────────────────────────────────

def _download_models():
    script = "/workspace/download_model.sh"
    if os.path.exists(script):
        print("[init] Running download_model.sh...")
        subprocess.run(["bash", script], check=True)
    else:
        print("[init] download_model.sh not found, skipping.")


def _wait_for_comfyui(timeout: int = 120):
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


def _start_comfyui():
    cmd = [
        "python", "main.py",
        "--listen", "0.0.0.0",
        "--port", "8188",
        "--cuda-malloc",
    ]

    if SERVERLESS:
        # Background process – handler takes over after startup
        print("[init] Serverless mode: starting ComfyUI in background...")
        subprocess.Popen(cmd, cwd=COMFYUI_DIR)
        _wait_for_comfyui(timeout=120)
        print("[init] ComfyUI ready.")
    else:
        # Pod / interactive mode – block forever so the pod stays alive
        # Access via: https://<pod-id>-8188.proxy.runpod.net
        print("[pod] Pod mode: starting ComfyUI in foreground on port 8188...")
        print("[pod] Open: https://<your-pod-id>-8188.proxy.runpod.net")
        proc = subprocess.run(cmd, cwd=COMFYUI_DIR)
        sys.exit(proc.returncode)


# ── Run init at module load ────────────────────────────────────────────────

_download_models()
_start_comfyui()   # exits here in pod mode, continues in serverless mode


# ── Helpers (serverless only) ──────────────────────────────────────────────

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
    Input:  { "workflow": { ...ComfyUI API JSON... }, "timeout": 300 }
    Output: { "prompt_id": "...", "outputs": [ { type, filename, mime, data } ] }
    """
    job_input = job.get("input", {})
    workflow  = job_input.get("workflow")
    timeout   = int(job_input.get("timeout", 300))

    if not workflow:
        return {"error": "Missing 'workflow' in job input."}

    try:
        runpod.serverless.progress_update(job, "Queuing workflow...")
        prompt_id = _queue_prompt(workflow)

        runpod.serverless.progress_update(job, f"Running inference ({prompt_id})...")
        outputs = _wait_for_completion(prompt_id, timeout=timeout)

        runpod.serverless.progress_update(job, "Collecting output files...")
        files = _collect_output_files(outputs)

        if not files:
            return {"error": "No output files found.", "prompt_id": prompt_id}

        return {"prompt_id": prompt_id, "outputs": files}

    except Exception as e:
        return {"error": str(e)}


# ── RunPod entrypoint — top level, NOT inside __main__ ────────────────────
runpod.serverless.start({"handler": handler})
