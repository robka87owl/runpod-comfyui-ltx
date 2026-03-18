FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

SHELL ["/bin/bash", "-c"]

# System dependencies
RUN apt-get update && apt-get install -y \
    git wget curl libgl1 libglib2.0-0 ffmpeg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && \
    cd ComfyUI && pip install -r requirements.txt

# Install ComfyUI-Manager
RUN git clone https://github.com/ltdrdata/ComfyUI-Manager.git \
    ComfyUI/custom_nodes/ComfyUI-Manager && \
    cd ComfyUI/custom_nodes/ComfyUI-Manager && \
    pip install -r requirements.txt

# Install ComfyUI-LTXVideo node support (LTXV nodes + Audio-Visual inference)
RUN git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git \
    ComfyUI/custom_nodes/ComfyUI-LTXVideo && \
    cd ComfyUI/custom_nodes/ComfyUI-LTXVideo && \
    pip install -r requirements.txt

# VideoHelperSuite (VHS_VideoCombine with audio support)
RUN git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git \
    ComfyUI/custom_nodes/ComfyUI-VideoHelperSuite && \
    cd ComfyUI/custom_nodes/ComfyUI-VideoHelperSuite && \
    pip install -r requirements.txt

# ComfyMath (CM_FloatToInt used in the workflow)
RUN git clone https://github.com/evanspearman/ComfyMath.git \
    ComfyUI/custom_nodes/ComfyMath

# Install RunPod SDK & helpers
RUN pip install runpod requests websocket-client Pillow

# Copy handler and startup scripts
COPY handler.py /workspace/handler.py
COPY start.sh /workspace/start.sh
COPY download_model.sh /workspace/download_model.sh

RUN chmod +x /workspace/start.sh /workspace/download_model.sh

# Model will be downloaded at container start (not baked in to keep image lean)
# Set model dir as env var so handler and scripts share it
ENV MODEL_DIR=/workspace/ComfyUI/models
ENV COMFYUI_DIR=/workspace/ComfyUI

CMD ["/workspace/start.sh"]
