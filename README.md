# 🎬 RunPod ComfyUI – LTX Video 2.3 22B FP8 (Audio-Visual)

[![RunPod](https://api.runpod.io/badge/robka87owl/runpod-comfyui-ltx)](https://www.runpod.io/console/hub/robka87owl/runpod-comfyui-ltx)

Custom ComfyUI Docker image for RunPod, built around the **LTX Video 2.3 22B FP8**
model with native **Audio-Visual inference** – generates synchronised video + audio
from a text prompt in a single pass.

---

## 📦 Repo structure

```
.
├── Dockerfile                          # CUDA 12.4 + ComfyUI + all required nodes
├── handler.py                          # RunPod Serverless handler
├── start.sh                            # Container entrypoint (pod & serverless)
├── download_model.sh                   # Downloads 22B FP8 + T5 + Audio VAE
└── workflows/
    ├── LTXV-2_3-22b_T2V_RA_V1.json    # ← your original AV workflow
    └── ltx_video_t2v.json              # Minimal T2V reference workflow
```

---

## 🧠 Workflow: LTXV-2_3-22b_T2V_RA_V1

The included workflow generates **video with synchronised audio** using:

| Node | Purpose |
|---|---|
| `LTXVModel` | Loads the 22B FP8 checkpoint |
| `LTXVAudioVAELoader` | Loads the vocoder (`ltx-av-step-1751000_vocoder_24K.safetensors`) |
| `LTXVConditioning` | Injects frame rate into conditioning |
| `LTXVEmptyLatentAudio` | Creates blank audio latent |
| `EmptyLTXVLatentVideo` | Creates blank video latent (768×512, 105 frames) |
| `LTXVConcatAVLatent` | Merges video + audio latents for joint generation |
| `MultimodalGuider` | Dual-CFG guidance: video CFG=3, audio CFG=7 |
| `LTXVSequenceParallelMultiGPUPatcher` | Multi-GPU / torch.compile wrapper |
| `SamplerCustomAdvanced` | Runs the diffusion (euler, 20 steps) |
| `LTXVSeparateAVLatent` | Splits result back into video/audio |
| `VAEDecode` + `LTXVAudioVAEDecode` | Decodes both modalities |
| `VHS_VideoCombine` | Muxes video + audio into H.264 MP4 @ 25 fps |

**Default output:** 768×512, 105 frames, 25 fps ≈ 4.2 seconds of video with audio.

---

## 🚀 Quick start

### 1. Build & push to Docker Hub

```bash
docker build -t your-dockerhub/comfyui-ltx:latest .
docker push your-dockerhub/comfyui-ltx:latest
```

### 2a. Deploy as RunPod **Serverless** endpoint

1. Go to **RunPod → Serverless → New Endpoint**
2. Set **Container Image** to `your-dockerhub/comfyui-ltx:latest`
3. Set env var `RUNPOD_SERVERLESS=1`
4. Choose a GPU with ≥ 24 GB VRAM for the 22B model (e.g. RTX 3090 / 4090 / A100)
5. Deploy → copy your **Endpoint ID**

Call it with your workflow:

```bash
curl -X POST https://api.runpod.io/v2/<ENDPOINT_ID>/run \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "workflow": '"$(cat workflows/LTXV-2_3-22b_T2V_RA_V1.json | python3 -c 'import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get("extra",d)))')"'
    }
  }'
```

### 2b. Deploy as a RunPod **Pod** (interactive)

1. Go to **RunPod → Pods → Deploy**
2. Use the same container image
3. Expose port **8188**
4. Open ComfyUI at `https://<pod-id>-8188.proxy.runpod.net`
5. Load the workflow from `workflows/LTXV-2_3-22b_T2V_RA_V1.json`

---

## ⚙️ Environment variables

| Variable | Default | Description |
|---|---|---|
| `MODEL_DIR` | `/workspace/ComfyUI/models` | Where models are stored |
| `COMFYUI_DIR` | `/workspace/ComfyUI` | ComfyUI installation path |
| `RUNPOD_SERVERLESS` | *(unset)* | Set to `1` for serverless mode |

---

## 💾 Network Volume (strongly recommended)

The models total ~13–14 GB. Attach a **RunPod Network Volume** at
`/workspace/ComfyUI/models` – `download_model.sh` skips files already present,
so cold starts stay fast after the first run.

**Model paths inside the volume:**

```
models/
├── video_models/ltx_video/
│   └── ltxv-2.3-22b-fp8.safetensors          (~10–11 GB)
├── text_encoders/
│   └── t5xxl_fp8_e4m3fn_scaled.safetensors   (~4.8 GB)
└── audio_vae/
    └── ltx-av-step-1751000_vocoder_24K.safetensors (~1.5 GB)
```

---

## 🧩 Included custom nodes

| Node pack | Purpose |
|---|---|
| [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager) | Install / manage nodes via UI |
| [ComfyUI-LTXVideo](https://github.com/Lightricks/ComfyUI-LTXVideo) | All LTXV* nodes incl. Audio-Visual |
| [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) | `VHS_VideoCombine` with audio muxing |
| [ComfyMath](https://github.com/evanspearman/ComfyMath) | `CM_FloatToInt` used in the workflow |

---

## ⚠️ Single-GPU note

The workflow includes `LTXVSequenceParallelMultiGPUPatcher` with `torch_compile: true`.
On a **single GPU**, this node still works but `torch.compile` adds a one-time warm-up
of ~2–4 minutes on first run. To disable it, set `"torch_compile": false` in node `44`
of the workflow.

---

## � Support

For questions, feel free to send an email to info@bremer-software.biz

---

## �📝 License

MIT
