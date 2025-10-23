"""
Custom Modal base image with CUDA dependencies pre-installed.

This dramatically reduces build times by pre-installing large CUDA libraries:
- Before: 60s downloading 142 packages every build
- After: 20-30s installing only vLLM and app-specific deps

Usage:
    # Build and publish base image (one-time, ~10 min)
    modal run lift_sys/inference/modal_base_image.py::build_base

    # Deploy app using base image (faster builds)
    modal deploy lift_sys/inference/modal_app.py

The base image is versioned and cached, so rebuilding only happens when:
- CUDA version changes
- PyTorch version changes
- Base dependencies need updates
"""

import modal

# Dependency versions - keep in sync with modal_app.py
VLLM_VERSION = "0.9.2"
TRANSFORMERS_VERSION = "4.53.0"
FASTAPI_VERSION = "0.115.12"
HF_HUB_VERSION = "0.20.0"
TORCH_VERSION = "2.7.0"

# Create app for base image building
app = modal.App("lift-sys-base-image")

# Custom base image with CUDA + PyTorch + heavy dependencies pre-installed
# This is the "expensive" part that we build once and reuse
base_image = (
    modal.Image.from_registry("nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.12")
    .apt_install(
        "git",  # Required for transformers cache
        "wget",  # Useful for downloading assets
    )
    .uv_pip_install(
        # PyTorch ecosystem (largest dependencies)
        f"torch=={TORCH_VERSION}",  # 825 MiB
        "torchaudio==2.7.0",  # 3.3 MiB
        "torchvision==0.22.0",  # 7.1 MiB
        "triton==3.3.0",  # 149.3 MiB
        # NVIDIA CUDA libraries (1.8 GiB total)
        "nvidia-cudnn-cu12==9.5.1.17",  # 544.5 MiB
        "nvidia-cublas-cu12==12.6.4.1",  # 374.9 MiB
        "nvidia-cusparse-cu12==12.5.4.2",  # 206.5 MiB
        "nvidia-nccl-cu12==2.26.2",  # 192.0 MiB
        "nvidia-cufft-cu12==11.3.0.4",  # 190.9 MiB
        "nvidia-cusolver-cu12==11.7.1.2",  # 150.9 MiB
        "nvidia-cusparselt-cu12==0.6.3",  # 149.5 MiB
        "nvidia-curand-cu12==10.3.7.77",  # 53.7 MiB
        "nvidia-cuda-nvrtc-cu12==12.6.77",  # 22.6 MiB
        "nvidia-nvjitlink-cu12==12.6.85",  # 18.8 MiB
        "nvidia-cuda-cupti-cu12==12.6.80",  # 8.5 MiB
        "nvidia-cufile-cu12==1.11.1.6",  # 1.1 MiB
        "nvidia-cudnn-frontend==1.15.0",  # 1.8 MiB
        "nvidia-cuda-runtime-cu12==12.6.77",
        "nvidia-nvtx-cu12==12.6.77",
        "nvidia-ml-py==13.580.82",
        # Scientific computing
        "numpy==2.2.6",  # 15.8 MiB
        "scipy==1.16.2",  # 34.0 MiB
        "sympy==1.14.0",  # 6.0 MiB
        # FastAPI and dependencies
        f"fastapi[standard]=={FASTAPI_VERSION}",  # Web framework
        "uvicorn==0.38.0",
        "uvloop==0.22.1",  # 4.2 MiB
        "httptools==0.7.1",
        "watchfiles==1.1.1",
        "websockets==15.0.1",
        # HuggingFace ecosystem
        f"transformers=={TRANSFORMERS_VERSION}",  # 10.3 MiB
        f"huggingface-hub>={HF_HUB_VERSION}",
        "tokenizers==0.21.4",  # 3.0 MiB
        "safetensors==0.6.2",
        "hf-transfer==0.1.9",  # 3.4 MiB (Rust-based fast downloads)
        "hf-xet==1.1.10",  # 3.0 MiB
        # ML utilities
        "sentencepiece==0.2.1",  # 1.3 MiB
        "tiktoken==0.12.0",  # 1.1 MiB
        # Accelerators
        "xformers==0.0.30",  # 30.1 MiB
        "cupy-cuda12x==13.6.0",  # 107.7 MiB
        # Ray (distributed computing)
        "ray==2.50.1",  # 67.8 MiB
        # Other dependencies
        "opencv-python-headless==4.12.0.88",  # 51.5 MiB
        "pillow==12.0.0",  # 6.7 MiB
        "pydantic==2.12.3",
        "pydantic-core==2.41.4",  # 2.0 MiB
        "aiohttp==3.13.1",  # 1.7 MiB
        "mistral-common==1.8.5",  # 6.2 MiB
        "llvmlite==0.44.0",  # 40.4 MiB
        "numba==0.61.2",  # 3.7 MiB
        "networkx==3.5",  # 1.9 MiB
    )
    .env(
        {
            # CUDA paths
            "CUDA_HOME": "/usr/local/cuda",
            "PATH": "/usr/local/cuda/bin:${PATH}",
            "LD_LIBRARY_PATH": "/usr/local/cuda/lib64:/usr/local/cuda/lib",
            # Performance optimizations
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
)


@app.function(image=base_image, timeout=600)
def build_base():
    """
    Build and cache the base image.

    This is run once to pre-build the heavy dependencies.
    Subsequent app deployments will use this cached base.
    """
    print("✅ Base image built successfully!")
    print(f"   PyTorch: {TORCH_VERSION}")
    print(f"   Transformers: {TRANSFORMERS_VERSION}")
    print(f"   FastAPI: {FASTAPI_VERSION}")
    print("")
    print("📦 Large dependencies pre-installed:")
    print("   - torch (825 MiB)")
    print("   - NVIDIA CUDA libs (1.8 GiB)")
    print("   - Scientific computing (numpy, scipy)")
    print("   - HuggingFace ecosystem")
    print("")
    print("Next: Deploy modal_app.py which extends this base")
    return {"status": "success", "torch_version": TORCH_VERSION}
