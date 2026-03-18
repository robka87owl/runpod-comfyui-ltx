#!/bin/bash
# RunPod Startup Script

# ── RunPod Basisdienste (JupyterLab + SSH) im Hintergrund ─────────────────
/start.sh &
sleep 3

# ── Modelle herunterladen – nur wenn SKIP_MODEL_DOWNLOAD nicht gesetzt ─────
# RunPod Hub-Tests setzen SKIP_MODEL_DOWNLOAD=1 damit der Health-Check
# nicht auf einen ~20 GB Download warten muss.
if [ "${SKIP_MODEL_DOWNLOAD}" != "1" ]; then
    echo "[run.sh] Starte Modell-Download..."
    bash /workspace/download_model.sh
else
    echo "[run.sh] SKIP_MODEL_DOWNLOAD=1 – überspringe Download (Test/Dev-Modus)"
fi

# ── Modus entscheiden ─────────────────────────────────────────────────────
if [ "$RUNPOD_SERVERLESS" = "1" ]; then
    echo "[run.sh] Serverless-Modus: starte handler.py"
    exec python /workspace/handler.py
else
    echo "[run.sh] Pod-Modus: starte ComfyUI auf Port 8188"
    cd /workspace/ComfyUI && exec python main.py \
        --listen 0.0.0.0 \
        --port 8188 \
        --cuda-malloc \
        --enable-manager-legacy-ui
fi
