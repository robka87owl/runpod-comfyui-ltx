# 🎬 RunPod ComfyUI – LTX Video 2.3 22B FP8 (Audio-Visual)

[![RunPod](https://api.runpod.io/badge/robka87owl/runpod-comfyui-ltx)](https://www.runpod.io/console/hub/robka87owl/runpod-comfyui-ltx)

Custom ComfyUI Docker image for RunPod, built around the **LTX Video 2.3 22B FP8**
model with native **Audio-Visual inference** – generates synchronised video + audio
from a text prompt in a single pass.

---

## 📦 Repo structure

```
runpod-comfyui-ltx/
│
├── Dockerfile                          # CUDA 12.4 + ComfyUI v0.17.2 + all nodes
├── handler.py                          # RunPod Serverless handler
├── run.sh                              # Container entrypoint (pod & serverless)
├── download_model.sh                   # Downloads all LTX 2.3 22B model files
├── client.py                           # Python API client
├── README.md
├── LICENSE
├── .gitignore
│
├── .github/
│   ├── workflows/
│   │   └── release.yml                 # Auto-versioning & release workflow
│   └── COMMIT_CONVENTION.md
│
├── .runpod/
│   ├── hub.json                        # RunPod Hub configuration
│   └── tests.json                      # Hub test payload
│
├── notebooks/
│   └── download_models.ipynb           # Download models via JupyterLab
│
└── workflows/
    ├── LTXV-2_3-22b_T2V_RA_V1.json    # Original Audio-Visual workflow
    └── ltx_video_t2v.json              # Minimal T2V reference workflow
```

---

## 🧠 Workflow: LTXV-2_3-22b_T2V_RA_V1

Generates **video with synchronised audio** in a single diffusion pass:

| Node | Purpose |
|---|---|
| `LTXVModel` | Loads the 22B FP8 transformer |
| `LTXVAudioVAELoader` | Loads the Audio VAE / vocoder |
| `LTXVConditioning` | Injects frame rate into conditioning |
| `LTXVEmptyLatentAudio` | Creates blank audio latent |
| `EmptyLTXVLatentVideo` | Creates blank video latent (768×512, 105 frames) |
| `LTXVConcatAVLatent` | Merges video + audio latents for joint generation |
| `MultimodalGuider` | Dual-CFG guidance: video CFG=3, audio CFG=7 |
| `LTXVSequenceParallelMultiGPUPatcher` | Multi-GPU / torch.compile wrapper |
| `SamplerCustomAdvanced` | Diffusion sampler (euler, 20 steps) |
| `LTXVSeparateAVLatent` | Splits result back into video/audio |
| `VAEDecode` + `LTXVAudioVAEDecode` | Decodes both modalities |
| `VHS_VideoCombine` | Muxes video + audio → H.264 MP4 @ 25 fps |

**Default output:** 768×512, 105 frames, 25 fps ≈ 4.2 seconds with audio.

---

## 💾 Models

All models are downloaded automatically on first start via `download_model.sh`.
Attach a **Network Volume** at `/workspace/ComfyUI/models` to avoid re-downloading.

| File | Folder | Size |
|---|---|---|
| `ltx-2.3-22b-distilled_transformer_only_fp8_input_scaled.safetensors` | `unet/` | ~10 GB |
| `gemma-3-12b-it-IQ4_XS.gguf` | `text_encoders/` | ~7 GB |
| `LTX-2.3-22b-distilled_embeddings_connectors.safetensors` | `text_encoders/` | ~1 GB |
| `LTX2.3-22b-distilled_audio_vae.safetensors` | `checkpoints/` | ~1 GB |
| `LTX-2.3-22b-distilled_video_vae.safetensors` | `vae/` | ~1 GB |
| `LTX-2.3-spatial-upscaler-x2-1.0.safetensors` | `latent_upscale_models/` | ~0.5 GB |

---

## 🧩 Included custom nodes

| Node pack | Purpose |
|---|---|
| [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager) | Install / manage nodes via UI (legacy UI enabled) |
| [ComfyUI-LTXVideo](https://github.com/Lightricks/ComfyUI-LTXVideo) | All LTXV* nodes incl. Audio-Visual |
| [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) | `VHS_VideoCombine` with audio muxing |
| [ComfyMath](https://github.com/evanspearman/ComfyMath) | `CM_FloatToInt` used in the workflow |

---

## 🚀 Quick start

### 1. Build & push

```bash
docker build -t your-dockerhub/comfyui-ltx:latest .
docker push your-dockerhub/comfyui-ltx:latest
```

### 2a. Pod (interactive – ComfyUI + JupyterLab)

1. **RunPod → Pods → Deploy**
2. Container Image: `your-dockerhub/comfyui-ltx:latest`
3. HTTP Ports: `8188` (ComfyUI), `8888` (JupyterLab)
4. `RUNPOD_SERVERLESS` **not set**

| Service | URL |
|---|---|
| ComfyUI | `https://<pod-id>-8188.proxy.runpod.net` |
| JupyterLab | `https://<pod-id>-8888.proxy.runpod.net` |

### 2b. Serverless endpoint (API)

1. **RunPod → Serverless → New Endpoint**
2. Container Image: `your-dockerhub/comfyui-ltx:latest`
3. Env var: `RUNPOD_SERVERLESS=1`
4. GPU: ≥ 24 GB VRAM (RTX 4090 / A6000 / A100)

```bash
curl -X POST https://api.runpod.io/v2/<ENDPOINT_ID>/run \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"workflow": {...}}}'
```

Or use the included Python client:

```bash
export RUNPOD_API_KEY="rp_xxx"
export RUNPOD_ENDPOINT_ID="your-endpoint-id"
python client.py --prompt "A volcanic eruption at sunset, cinematic"
```

---

## ⚙️ Environment variables

| Variable | Default | Description |
|---|---|---|
| `RUNPOD_SERVERLESS` | *(unset)* | Set to `1` for serverless mode |
| `MODEL_DIR` | `/workspace/ComfyUI/models` | Model storage path |
| `COMFYUI_DIR` | `/workspace/ComfyUI` | ComfyUI installation path |
| `SKIP_MODEL_DOWNLOAD` | `0` | Set to `1` to skip download on startup |

---

## ⚠️ Single-GPU note

`LTXVSequenceParallelMultiGPUPatcher` with `torch_compile: true` adds a one-time
warm-up of ~2–4 minutes on first run. To disable: set `"torch_compile": false`
in node `44` of the workflow.

---

## 📬 Support

For questions: **info@bremer-software.biz**

---

## 📄 License

MIT License

Copyright (c) 2026 Robert Bremer (info@bremer-software.biz)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
