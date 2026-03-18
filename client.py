"""
RunPod ComfyUI Client – LTX Video 2.3 22B FP8
==============================================
Sendet einen Workflow an den Serverless-Endpoint und speichert das Ergebnis.

Setup:
    pip install requests

Verwendung:
    python client.py                          # Standard-Workflow
    python client.py --prompt "Ein Vulkan"   # Eigener Prompt
    python client.py --sync                   # Synchron (kurze Jobs ≤ 90s)
"""

import argparse
import base64
import json
import os
import time
import requests

# ── Konfiguration ──────────────────────────────────────────────────────────

RUNPOD_API_KEY  = os.environ.get("RUNPOD_API_KEY", "DEIN_API_KEY_HIER")
ENDPOINT_ID     = os.environ.get("RUNPOD_ENDPOINT_ID", "DEINE_ENDPOINT_ID")

BASE_URL        = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"
HEADERS         = {
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
    "Content-Type":  "application/json",
}


# ── Workflow-Vorlage (aus LTXV-2_3-22b_T2V_RA_V1) ─────────────────────────

def build_workflow(prompt: str, negative: str = "blurry, low quality, watermark",
                   width: int = 768, height: int = 512,
                   frames: int = 105, fps: float = 25.0,
                   steps: int = 20, seed: int = 42) -> dict:
    """Gibt einen ComfyUI API-Workflow für LTX Video 22B zurück."""
    return {
        "1":  {"inputs": {"ckpt_name": "ltxv-2.3-22b-fp8.safetensors"},
               "class_type": "LTXVModel"},
        "3":  {"inputs": {"text": prompt, "clip": ["1", 1]},
               "class_type": "CLIPTextEncode"},
        "4":  {"inputs": {"text": negative, "clip": ["1", 1]},
               "class_type": "CLIPTextEncode"},
        "8":  {"inputs": {"sampler_name": "euler"},
               "class_type": "KSamplerSelect"},
        "9":  {"inputs": {"steps": steps, "max_shift": 2.05, "base_shift": 0.95,
                          "stretch": True, "terminal": 0.1, "latent": ["28", 0]},
               "class_type": "LTXVScheduler"},
        "11": {"inputs": {"noise_seed": seed},
               "class_type": "RandomNoise"},
        "12": {"inputs": {"samples": ["29", 0], "vae": ["1", 2]},
               "class_type": "VAEDecode"},
        "13": {"inputs": {"ckpt_name": "ltx-av-step-1751000_vocoder_24K.safetensors"},
               "class_type": "LTXVAudioVAELoader"},
        "14": {"inputs": {"samples": ["29", 1], "audio_vae": ["13", 0]},
               "class_type": "LTXVAudioVAEDecode"},
        "15": {"inputs": {"frame_rate": ["23", 0], "loop_count": 0,
                          "filename_prefix": "output", "format": "video/h264-mp4",
                          "pix_fmt": "yuv420p", "crf": 19, "save_metadata": True,
                          "trim_to_audio": False, "pingpong": False, "save_output": True,
                          "images": ["12", 0], "audio": ["14", 0]},
               "class_type": "VHS_VideoCombine"},
        "17": {"inputs": {"skip_blocks": "29", "model": ["28", 1],
                          "positive": ["22", 0], "negative": ["22", 1],
                          "parameters": ["18", 0]},
               "class_type": "MultimodalGuider"},
        "18": {"inputs": {"modality": "VIDEO", "cfg": 3, "stg": 0,
                          "rescale": 0, "modality_scale": 3, "parameters": ["19", 0]},
               "class_type": "GuiderParameters"},
        "19": {"inputs": {"modality": "AUDIO", "cfg": 7, "stg": 0,
                          "rescale": 0, "modality_scale": 3},
               "class_type": "GuiderParameters"},
        "22": {"inputs": {"frame_rate": ["23", 0],
                          "positive": ["3", 0], "negative": ["4", 0]},
               "class_type": "LTXVConditioning"},
        "23": {"inputs": {"value": fps},
               "class_type": "FloatConstant"},
        "26": {"inputs": {"frames_number": ["27", 0], "frame_rate": ["42", 0], "batch_size": 1},
               "class_type": "LTXVEmptyLatentAudio"},
        "27": {"inputs": {"value": frames},
               "class_type": "INTConstant"},
        "28": {"inputs": {"video_latent": ["43", 0], "audio_latent": ["26", 0], "model": ["44", 0]},
               "class_type": "LTXVConcatAVLatent"},
        "29": {"inputs": {"av_latent": ["41", 0], "model": ["28", 1]},
               "class_type": "LTXVSeparateAVLatent"},
        "41": {"inputs": {"noise": ["11", 0], "guider": ["17", 0], "sampler": ["8", 0],
                          "sigmas": ["9", 0], "latent_image": ["28", 0]},
               "class_type": "SamplerCustomAdvanced"},
        "42": {"inputs": {"a": ["23", 0]},
               "class_type": "CM_FloatToInt"},
        "43": {"inputs": {"width": width, "height": height, "length": ["27", 0], "batch_size": 1},
               "class_type": "EmptyLTXVLatentVideo"},
        "44": {"inputs": {"torch_compile": False, "disable_backup": False, "model": ["1", 0]},
               "class_type": "LTXVSequenceParallelMultiGPUPatcher"},
    }


# ── API-Aufrufe ────────────────────────────────────────────────────────────

def run_async(workflow: dict, timeout_seconds: int = 600) -> str:
    """
    Sendet Job async (/run) und gibt die Job-ID zurück.
    Ergebnis danach mit poll_status() oder wait_for_result() abrufen.
    Ergebnis bleibt 30 Minuten gespeichert.
    """
    payload = {
        "input": {"workflow": workflow},
        "policy": {
            "executionTimeout": timeout_seconds * 1000,  # in Millisekunden
            "ttl": (timeout_seconds + 600) * 1000,       # etwas mehr als executionTimeout
        }
    }
    r = requests.post(f"{BASE_URL}/run", headers=HEADERS, json=payload)
    r.raise_for_status()
    job_id = r.json()["id"]
    print(f"[async] Job gestartet: {job_id}")
    return job_id


def run_sync(workflow: dict) -> dict:
    """
    Sendet Job synchron (/runsync) und wartet direkt auf das Ergebnis.
    Nur für kurze Jobs empfohlen – Ergebnis bleibt nur 1 Minute gespeichert.
    Max Payload: 20 MB.
    """
    payload = {"input": {"workflow": workflow}}
    print("[sync] Warte auf Ergebnis...")
    r = requests.post(f"{BASE_URL}/runsync", headers=HEADERS, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def get_status(job_id: str) -> dict:
    """Gibt den aktuellen Job-Status zurück."""
    r = requests.get(f"{BASE_URL}/status/{job_id}", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def cancel_job(job_id: str):
    """Bricht einen laufenden oder wartenden Job ab."""
    r = requests.post(f"{BASE_URL}/cancel/{job_id}", headers=HEADERS)
    r.raise_for_status()
    print(f"[cancel] Job {job_id} abgebrochen.")


def wait_for_result(job_id: str, poll_interval: int = 5, max_wait: int = 600) -> dict:
    """
    Pollt /status bis der Job fertig ist.
    Status-Übergänge: IN_QUEUE → IN_PROGRESS → COMPLETED / FAILED
    """
    deadline = time.time() + max_wait
    while time.time() < deadline:
        data = get_status(job_id)
        status = data.get("status", "")

        if status == "IN_QUEUE":
            print(f"  [status] In der Warteschlange...")
        elif status == "IN_PROGRESS":
            # Fortschritts-Updates des Handlers anzeigen
            updates = data.get("progressUpdates") or []
            if updates:
                print(f"  [status] {updates[-1]}")
            else:
                print(f"  [status] Läuft...")
        elif status == "COMPLETED":
            print(f"  [status] Fertig!")
            return data
        elif status in ("FAILED", "CANCELLED", "TIMED_OUT"):
            error = data.get("error", "Unbekannter Fehler")
            raise RuntimeError(f"Job {status}: {error}")

        time.sleep(poll_interval)

    raise TimeoutError(f"Job {job_id} nicht fertig nach {max_wait}s.")


# ── Ausgabe speichern ──────────────────────────────────────────────────────

def save_outputs(result: dict, output_dir: str = "."):
    """Dekodiert Base64-Ausgaben und speichert sie als Dateien."""
    outputs = result.get("output", {}).get("outputs", [])
    if not outputs:
        print("[save] Keine Ausgabedateien gefunden.")
        print("[save] Rohes Ergebnis:", json.dumps(result, indent=2)[:500])
        return

    os.makedirs(output_dir, exist_ok=True)
    for i, item in enumerate(outputs):
        ext      = item["mime"].split("/")[-1]
        filename = item.get("filename") or f"output_{i}.{ext}"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(item["data"]))
        print(f"[save] Gespeichert: {filepath}  ({item['type']}, {os.path.getsize(filepath)//1024} KB)")


# ── Hauptprogramm ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="LTX Video 22B – RunPod Client")
    parser.add_argument("--prompt",   default="Eine majestätische Adlerin gleitet über verschneite Berggipfel, kinematisch, 4K")
    parser.add_argument("--negative", default="unscharf, schlechte Qualität, Wasserzeichen, Text")
    parser.add_argument("--width",    type=int,   default=768)
    parser.add_argument("--height",   type=int,   default=512)
    parser.add_argument("--frames",   type=int,   default=105, help="Anzahl Frames (97 = ~4s @ 25fps)")
    parser.add_argument("--fps",      type=float, default=25.0)
    parser.add_argument("--steps",    type=int,   default=20)
    parser.add_argument("--seed",     type=int,   default=42)
    parser.add_argument("--sync",     action="store_true", help="Synchron senden (kurze Jobs)")
    parser.add_argument("--out",      default="output", help="Ausgabeordner")
    args = parser.parse_args()

    print(f"Prompt : {args.prompt}")
    print(f"Größe  : {args.width}×{args.height}, {args.frames} Frames @ {args.fps} fps")

    workflow = build_workflow(
        prompt=args.prompt, negative=args.negative,
        width=args.width, height=args.height,
        frames=args.frames, fps=args.fps,
        steps=args.steps, seed=args.seed,
    )

    if args.sync:
        result = run_sync(workflow)
    else:
        job_id = run_async(workflow)
        result = wait_for_result(job_id)

    save_outputs(result, output_dir=args.out)


if __name__ == "__main__":
    main()
