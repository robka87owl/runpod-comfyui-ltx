#!/bin/bash
# RunPod Startup Script
# Startet die RunPod-Basisdienste (JupyterLab + SSH) im Hintergrund,
# lädt dann die Modelle und startet ComfyUI.

# ── RunPod Basisdienste starten (JupyterLab auf 8888, SSH auf 22) ──────────
/start.sh &

# Kurz warten bis Basisdienste bereit sind
sleep 3

# ── Modelle herunterladen falls nötig ─────────────────────────────────────
bash /workspace/download_model.sh

# ── Modus entscheiden ─────────────────────────────────────────────────────
if [ "$RUNPOD_SERVERLESS" = "1" ]; then
    echo "[run.sh] Serverless-Modus: starte handler.py"
    exec python /workspace/handler.py
else
    echo "[run.sh] Pod-Modus: starte ComfyUI auf Port 8188"
    echo "[run.sh] ComfyUI:   https://\$RUNPOD_POD_ID-8188.proxy.runpod.net"
    echo "[run.sh] JupyterLab: https://\$RUNPOD_POD_ID-8888.proxy.runpod.net"
    cd /workspace/ComfyUI && exec python main.py \
        --listen 0.0.0.0 \
        --port 8188 \
        --cuda-malloc \
        --enable-manager-legacy-ui
fi
