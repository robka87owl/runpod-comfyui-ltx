FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

ENV PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-c"]

# System dependencies
RUN apt-get update && apt-get install -y \
    git wget curl libgl1 libglib2.0-0 ffmpeg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# ── ComfyUI v0.17.2 ────────────────────────────────────────────────────────
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && \
    cd ComfyUI && git checkout v0.17.2 && \
    pip install -r requirements.txt

# ── Custom Nodes ───────────────────────────────────────────────────────────
RUN git clone https://github.com/ltdrdata/ComfyUI-Manager.git \
    ComfyUI/custom_nodes/ComfyUI-Manager && \
    cd ComfyUI/custom_nodes/ComfyUI-Manager && \
    pip install -r requirements.txt

RUN git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git \
    ComfyUI/custom_nodes/ComfyUI-LTXVideo && \
    cd ComfyUI/custom_nodes/ComfyUI-LTXVideo && \
    pip install -r requirements.txt

RUN git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git \
    ComfyUI/custom_nodes/ComfyUI-VideoHelperSuite && \
    cd ComfyUI/custom_nodes/ComfyUI-VideoHelperSuite && \
    pip install -r requirements.txt

RUN git clone https://github.com/evanspearman/ComfyMath.git \
    ComfyUI/custom_nodes/ComfyMath

# ── Python packages ────────────────────────────────────────────────────────
RUN pip install --no-cache-dir runpod requests websocket-client Pillow jupyterlab

# ── App-Dateien ────────────────────────────────────────────────────────────
COPY handler.py /workspace/handler.py
COPY download_model.sh /workspace/download_model.sh
COPY run.sh /workspace/run.sh
COPY notebooks/ /workspace/notebooks/
RUN chmod +x /workspace/download_model.sh /workspace/run.sh

# ── Umgebung ───────────────────────────────────────────────────────────────
ENV MODEL_DIR=/workspace/ComfyUI/models
ENV COMFYUI_DIR=/workspace/ComfyUI

# ── Ports ──────────────────────────────────────────────────────────────────
# 8188 = ComfyUI Web UI
# 8888 = JupyterLab (via RunPod /start.sh)
# 22   = SSH        (via RunPod /start.sh)
EXPOSE 8188 8888 22
ENV RUNPOD_TCP_PORT_8188=8188

# ── Entrypoint ─────────────────────────────────────────────────────────────
# run.sh startet /start.sh (JupyterLab+SSH) und dann ComfyUI oder handler.py
COPY run.sh /run.sh
CMD ["/run.sh"]
