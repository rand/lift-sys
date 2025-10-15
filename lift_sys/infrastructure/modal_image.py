"""
Optimized Modal base image for lift-sys inference workloads.

This image includes all dependencies for SGLang-based inference with schema-constrained
generation. Uses NVIDIA CUDA development image to support flashinfer JIT compilation.

Critical Requirements:
- flashinfer requires nvcc (NVIDIA CUDA compiler) for JIT kernel compilation
- Must use nvidia/cuda:devel image, NOT debian_slim or cuda:runtime
- CUDA development tools add ~2GB to image but are essential for flashinfer

Benefits:
- Faster deployments: Dependencies already installed and cached
- Reproducibility: Exact versions locked
- Faster cold starts: No pip install on container startup
- JIT compilation: flashinfer can compile optimized kernels at runtime
- Cost savings: Less time building = less compute time

Usage:
    # Build and cache the image (run once, or when dependencies change)
    modal image build lift_sys/infrastructure/modal_image.py::llm_image

    # Use in your Modal app
    from lift_sys.infrastructure.modal_image import llm_image

    @app.function(image=llm_image)
    def my_function():
        pass

Image Contents:
- NVIDIA CUDA 12.1.0 development environment (includes nvcc)
- Python 3.12
- SGLang 0.5.3.post1 (with all extras: flashinfer, xgrammar, torch)
- Transformers 4.57.0 (required by SGLang 0.5.3.post1)
- FastAPI with standard extras
- HuggingFace Hub utilities
- Optimized environment variables for performance

Model Storage Strategy:
- Models are NOT included in the image (would be 18GB+)
- Models are cached in Modal Volumes for fast loading
- See lift_sys/inference/modal_app.py for volume setup

Build Time: ~8-10 minutes (one-time cost, flashinfer compiles from source)
Image Size: ~6-7 GB (CUDA devel tools + Python packages)
Cold Start with this image: ~10-20 seconds (model loading from volume cache)

Tested Configurations:
- Qwen2.5-Coder-7B-Instruct: Fits on A10G (24GB), works perfectly
- Qwen3-Coder-30B-A3B-Instruct: Requires >40GB VRAM (MoE loads all experts)
"""

import modal

# Pinned dependency versions for reproducibility
# Update these when you want to upgrade dependencies, then rebuild the image
SGLANG_VERSION = "0.5.3.post1"
TRANSFORMERS_VERSION = "4.57.0"  # Required by SGLang 0.5.3.post1
FASTAPI_VERSION = "0.115.12"
HF_HUB_VERSION = "0.20.0"

# Create optimized base image for LLM inference
# CRITICAL: Use NVIDIA CUDA development image for flashinfer JIT compilation
llm_image = (
    # nvidia/cuda:devel includes nvcc compiler required by flashinfer
    # Modal will use GPU-optimized version when gpu= parameter is specified
    modal.Image.from_registry("nvidia/cuda:12.1.0-devel-ubuntu22.04", add_python="3.12")
    # System dependencies for ML workloads
    .apt_install(
        "git",  # Required for transformers cache and git-based model downloads
        "wget",  # Useful for downloading assets
        # Note: build-essential not needed, CUDA devel image already has compilers
    )
    # CUDA toolkit already installed at /usr/local/cuda with nvcc, headers, libraries
    # No need for manual CUDA setup - everything is pre-configured
    .pip_install(
        # Core inference stack - SGLang with all extras
        # [all] includes: flashinfer, xgrammar, torch, and CUDA dependencies
        # flashinfer will compile from source using nvcc during image build
        f"sglang[all]=={SGLANG_VERSION}",
        # Transformers with exact version required by SGLang
        f"transformers=={TRANSFORMERS_VERSION}",
        # Web framework for HTTP endpoints
        f"fastapi[standard]=={FASTAPI_VERSION}",
        # HuggingFace utilities for model downloads and caching
        f"huggingface-hub>={HF_HUB_VERSION}",
    )
    # Set environment defaults for better performance
    .env(
        {
            # CUDA paths (already correct in nvidia/cuda image, but explicit for clarity)
            "CUDA_HOME": "/usr/local/cuda",
            "CUDA_PATH": "/usr/local/cuda",
            "PATH": "/usr/local/cuda/bin:${PATH}",  # Ensure nvcc is in PATH
            "LD_LIBRARY_PATH": "/usr/local/cuda/lib64:/usr/local/cuda/lib",
            # Enable fast model downloads from HuggingFace (uses Rust-based transfer)
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            # Better GPU memory management for PyTorch
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
            # Disable tokenizers parallelism warning (not needed in container)
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
)


def test_image():
    """
    Test function to verify image contents and versions.

    Run with: modal run lift_sys/infrastructure/modal_image.py::test_image
    """
    import sys

    print("=" * 70)
    print("Modal Image Test - Dependency Verification")
    print("=" * 70)

    # Test Python version
    print(f"\nPython version: {sys.version}")

    # Test core dependencies
    try:
        import sglang

        print(f"✅ SGLang version: {sglang.__version__}")
    except ImportError as e:
        print(f"❌ SGLang import failed: {e}")

    try:
        import transformers

        print(f"✅ Transformers version: {transformers.__version__}")
    except ImportError as e:
        print(f"❌ Transformers import failed: {e}")

    try:
        import torch

        print(f"✅ PyTorch version: {torch.__version__}")
        print(f"   CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"   CUDA version: {torch.version.cuda}")
            print(f"   GPU count: {torch.cuda.device_count()}")
    except ImportError as e:
        print(f"❌ PyTorch import failed: {e}")

    try:
        import fastapi

        print(f"✅ FastAPI version: {fastapi.__version__}")
    except ImportError as e:
        print(f"❌ FastAPI import failed: {e}")

    try:
        from huggingface_hub import __version__ as hf_version

        print(f"✅ HuggingFace Hub version: {hf_version}")
    except ImportError as e:
        print(f"❌ HuggingFace Hub import failed: {e}")

    # Test environment variables
    import os

    print("\nEnvironment Variables:")
    print(f"  HF_HUB_ENABLE_HF_TRANSFER: {os.getenv('HF_HUB_ENABLE_HF_TRANSFER')}")
    print(f"  PYTORCH_CUDA_ALLOC_CONF: {os.getenv('PYTORCH_CUDA_ALLOC_CONF')}")
    print(f"  TOKENIZERS_PARALLELISM: {os.getenv('TOKENIZERS_PARALLELISM')}")

    print("\n" + "=" * 70)
    print("Image test complete!")
    print("=" * 70)


# Export for use in other Modal apps
__all__ = ["llm_image", "test_image"]
