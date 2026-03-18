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

# Install ComfyUI-LTXVideo (LTXV nodes + Audio-Visual inference)
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

# Copy only what actually exists in the repo
COPY handler.py /workspace/handler.py
COPY download_model.sh /workspace/download_model.sh
RUN chmod +x /workspace/download_model.sh

# Set model dir as env var so handler and download script share it
ENV MODEL_DIR=/workspace/ComfyUI/models
ENV COMFYUI_DIR=/workspace/ComfyUI

# Expose ComfyUI web UI – RunPod shows this automatically in the Connect tab
EXPOSE 8188

# handler.py starts ComfyUI internally before runpod.serverless.start()
CMD ["python", "/workspace/handler.py"]
