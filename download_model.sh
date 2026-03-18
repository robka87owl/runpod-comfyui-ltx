#!/bin/bash
# Downloads LTX Video 2.3 22B FP8 model weights + Audio VAE from HuggingFace.
# Skips download if files already exist (e.g. via RunPod network volume).
# Total download size: ~12–13 GB  →  attach a Network Volume to avoid re-downloads.

MODEL_DIR="${MODEL_DIR:-/workspace/ComfyUI/models}"
LTX_DIR="$MODEL_DIR/video_models/ltx_video"
TEXT_ENC_DIR="$MODEL_DIR/text_encoders"
AUDIO_VAE_DIR="$MODEL_DIR/audio_vae"

mkdir -p "$LTX_DIR" "$TEXT_ENC_DIR" "$AUDIO_VAE_DIR"

HF_BASE="https://huggingface.co/Lightricks/LTX-Video/resolve/main"

# ── 1. LTX Video 2.3 22B FP8 (main model) ─────────────────────────────────
LTX_FILE="$LTX_DIR/ltxv-2.3-22b-fp8.safetensors"
LTX_URL="$HF_BASE/ltxv-2.3-22b-distilled-fp8.safetensors"

if [ ! -f "$LTX_FILE" ]; then
    echo "[download] Downloading LTX Video 2.3 22B FP8 (~10–11 GB)..."
    wget -q --show-progress -O "$LTX_FILE" "$LTX_URL"
    echo "[download] Done: $LTX_FILE"
else
    echo "[download] LTX Video 2.3 22B FP8 already present, skipping."
fi

# ── 2. T5 Text Encoder FP8 ────────────────────────────────────────────────
T5_FILE="$TEXT_ENC_DIR/t5xxl_fp8_e4m3fn_scaled.safetensors"
T5_URL="$HF_BASE/t5xxl_fp8_e4m3fn_scaled.safetensors"

if [ ! -f "$T5_FILE" ]; then
    echo "[download] Downloading T5 encoder FP8 (~4.8 GB)..."
    wget -q --show-progress -O "$T5_FILE" "$T5_URL"
    echo "[download] Done: $T5_FILE"
else
    echo "[download] T5 encoder already present, skipping."
fi

# ── 3. Audio VAE (vocoder for Audio-Visual inference) ─────────────────────
# Required by LTXVAudioVAELoader in the LTXV-2_3-22b_T2V_RA_V1 workflow
AUDIO_FILE="$AUDIO_VAE_DIR/ltx-av-step-1751000_vocoder_24K.safetensors"
AUDIO_URL="$HF_BASE/ltx-av-step-1751000_vocoder_24K.safetensors"

if [ ! -f "$AUDIO_FILE" ]; then
    echo "[download] Downloading Audio VAE / vocoder (~1.5 GB)..."
    wget -q --show-progress -O "$AUDIO_FILE" "$AUDIO_URL"
    echo "[download] Done: $AUDIO_FILE"
else
    echo "[download] Audio VAE already present, skipping."
fi

echo "[download] All models ready."

