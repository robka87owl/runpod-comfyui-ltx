"""
RunPod Serverless Handler für ComfyUI + LTX Video 2.3 22B FP8

Wichtig: runpod.serverless.start() muss sofort erreichbar sein damit
der RunPod Health-Check nicht in einen Timeout läuft.
ComfyUI startet daher im Hintergrund-Thread – der Handler wartet
erst auf ComfyUI wenn ein Job tatsächlich reinkommt.
"""

import runpod
import time
import base64
import os
import subprocess
import requests
import threading
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_DIR = os.environ.get("COMFYUI_DIR", "/workspace/ComfyUI")
OUTPUT_DIR  = Path(COMFYUI_DIR) / "output"

# Shared event – wird gesetzt sobald ComfyUI bereit ist
_comfyui_ready = threading.Event()


# ── ComfyUI-Start im Hintergrund ───────────────────────────────────────────

def _comfyui_thread():
    """Läuft in einem eigenen Thread – blockiert den Handler nicht."""
    print("[init] ComfyUI wird im Hintergrund gestartet...")
    subprocess.Popen(
        [
            "python", "main.py",
            "--listen", "0.0.0.0",
            "--port", "8188",
            "--cuda-malloc",
            "--enable-manager-legacy-ui",
        ],
        cwd=COMFYUI_DIR,
    )
    # Warten bis ComfyUI API antwortet
    while True:
        try:
            r = requests.get(f"{COMFYUI_URL}/system_stats", timeout=3)
            if r.status_code == 200:
                print("[init] ComfyUI ist bereit.")
                _comfyui_ready.set()
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)


# Sofort im Hintergrund starten – blockiert NICHT
threading.Thread(target=_comfyui_thread, daemon=True).start()


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
    raise TimeoutError(f"Prompt {prompt_id} Timeout nach {timeout}s.")


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
                    media_type = (
                        "video" if ext in ("mp4", "webm", "gif") else
                        "audio" if ext in ("wav", "mp3", "flac", "ogg") else
                        "image"
                    )
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

    # Warten bis ComfyUI bereit – erst hier, nicht beim Start
    runpod.serverless.progress_update(job, "Warte auf ComfyUI...")
    if not _comfyui_ready.wait(timeout=120):
        return {"error": "ComfyUI nicht bereit nach 120s."}

    try:
        runpod.serverless.progress_update(job, "Workflow wird eingereiht...")
        prompt_id = _queue_prompt(workflow)

        runpod.serverless.progress_update(job, f"Inferenz läuft ({prompt_id})...")
        outputs = _wait_for_completion(prompt_id, timeout=timeout)

        runpod.serverless.progress_update(job, "Ausgabedateien werden gesammelt...")
        files = _collect_output_files(outputs)

        if not files:
            return {"error": "Keine Ausgabedateien gefunden.", "prompt_id": prompt_id}

        return {"prompt_id": prompt_id, "outputs": files}

    except Exception as e:
        return {"error": str(e)}


# ── RunPod Entrypoint – sofort erreichbar für Health-Check ────────────────
runpod.serverless.start({"handler": handler})
