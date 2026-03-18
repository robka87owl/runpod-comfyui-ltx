#!/bin/bash
# Downloads alle LTX Video 2.3 22B Distilled Modelle von HuggingFace.
# Überspringt Dateien die bereits vorhanden sind (z.B. via Network Volume).
# Gesamtgröße: ~20-25 GB – Network Volume dringend empfohlen!

set -e

MODEL_DIR="${MODEL_DIR:-/workspace/ComfyUI/models}"
HF_BASE="https://huggingface.co/Lightricks/LTX-Video/resolve/main"

# Verzeichnisse anlegen
mkdir -p \
    "$MODEL_DIR/unet" \
    "$MODEL_DIR/text_encoders" \
    "$MODEL_DIR/checkpoints" \
    "$MODEL_DIR/vae" \
    "$MODEL_DIR/latent_upscale_models"

download() {
    local URL="$1"
    local DEST="$2"
    if [ -f "$DEST" ]; then
        echo "[skip] $(basename $DEST) bereits vorhanden."
    else
        echo "[download] $(basename $DEST) ..."
        wget -q --show-progress -O "$DEST" "$URL"
        echo "[ok] $(basename $DEST)"
    fi
}

# 1. Diffusion Model (Transformer only, FP8)
download \
    "$HF_BASE/ltx-2.3-22b-distilled_transformer_only_fp8_input_scaled.safetensors" \
    "$MODEL_DIR/unet/ltx-2.3-22b-distilled_transformer_only_fp8_input_scaled.safetensors"

# 2. Text Encoder – Gemma 3 12B GGUF
download \
    "$HF_BASE/gemma-3-12b-it-IQ4_XS.gguf" \
    "$MODEL_DIR/text_encoders/gemma-3-12b-it-IQ4_XS.gguf"

# 3. Dual CLIP / Embeddings Connector
download \
    "$HF_BASE/LTX-2.3-22b-distilled_embeddings_connectors.safetensors" \
    "$MODEL_DIR/text_encoders/LTX-2.3-22b-distilled_embeddings_connectors.safetensors"

# 4. Audio VAE
download \
    "$HF_BASE/LTX2.3-22b-distilled_audio_vae.safetensors" \
    "$MODEL_DIR/checkpoints/LTX2.3-22b-distilled_audio_vae.safetensors"

# 5. Video VAE
download \
    "$HF_BASE/LTX-2.3-22b-distilled_video_vae.safetensors" \
    "$MODEL_DIR/vae/LTX-2.3-22b-distilled_video_vae.safetensors"

# 6. Spatial Upscaler
download \
    "$HF_BASE/LTX-2.3-spatial-upscaler-x2-1.0.safetensors" \
    "$MODEL_DIR/latent_upscale_models/LTX-2.3-spatial-upscaler-x2-1.0.safetensors"

echo ""
echo "✅ Alle Modelle bereit in $MODEL_DIR"
