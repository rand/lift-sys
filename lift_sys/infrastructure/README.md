# Infrastructure Module

Infrastructure utilities for lift-sys deployment, orchestration, and optimization.

## Contents

### `modal_image.py` - Pre-Built Base Image

Optimized Modal container image with pre-installed dependencies for LLM inference.

**What it includes:**
- Python 3.12
- SGLang 0.5.3.post1 (with XGrammar, flashinfer, torch)
- Transformers 4.51.2 (Qwen3 MoE support)
- FastAPI 0.115.12
- HuggingFace Hub utilities
- Performance-optimized environment variables

**Why use it:**
- **Faster deployments**: Dependencies cached in Modal registry
- **Faster cold starts**: No pip install on container startup
- **Reproducible builds**: Exact versions locked
- **Cost savings**: Less build time = less GPU compute time

## Quick Start

### 1. Build the Base Image (One-Time)

```bash
# Build and cache dependencies (takes 3-5 minutes)
modal image build lift_sys/infrastructure/modal_image.py::llm_image
```

This command:
- Builds the Docker image with all dependencies
- Caches it in Modal's container registry
- Makes it available for all your Modal apps

### 2. Verify the Image

```bash
# Test that all dependencies are installed correctly
modal run lift_sys/infrastructure/modal_image.py::test_image
```

Expected output:
```
✅ SGLang version: 0.5.3.post1
✅ Transformers version: 4.51.2
✅ PyTorch version: 2.x.x
   CUDA available: True
✅ FastAPI version: 0.115.12
✅ HuggingFace Hub version: 0.20.0
```

### 3. Use in Your Modal App

```python
# In your modal_app.py
from lift_sys.infrastructure.modal_image import llm_image

@app.function(image=llm_image)
def my_function():
    # Your code here
    # Dependencies are pre-installed!
    pass
```

## Maintenance

### When to Rebuild

Rebuild the base image when:
- **Dependency versions change** (e.g., upgrading SGLang)
- **New dependencies added** (e.g., adding a new library)
- **Security updates** (monthly maintenance)

### How to Rebuild

1. Edit version pins in `modal_image.py`:
   ```python
   SGLANG_VERSION = "0.5.4"  # Update version
   ```

2. Rebuild and re-cache:
   ```bash
   modal image build lift_sys/infrastructure/modal_image.py::llm_image
   ```

3. Redeploy apps using the image:
   ```bash
   modal deploy lift_sys/inference/modal_app.py
   ```

## Architecture

### Image Building Strategy

**Current (Option 1): Dependencies in image, models in volume**
```
┌─────────────────────────────────────┐
│  Modal Base Image (~4-5 GB)         │
│  - Python 3.12                      │
│  - SGLang + dependencies            │
│  - Cached in Modal registry         │
└─────────────────────────────────────┘
              ↓
        Fast to deploy
              ↓
┌─────────────────────────────────────┐
│  Modal Volume (~18 GB)              │
│  - Qwen3 GGUF model                 │
│  - Loaded on container startup      │
│  - Cached across restarts           │
└─────────────────────────────────────┘
```

**Cold Start Time:** ~30-60 seconds (model loading from volume)
**Deployment Time:** ~10-20 seconds (image already cached)
**Image Size:** ~4-5 GB
**Total Storage:** ~23 GB (image + volume)

### Alternative (Option 2): Everything in image

Not implemented, but possible:
- Bundle model in image (~23 GB total)
- Fastest cold starts (<10 seconds)
- Slower image builds
- Less flexible (need full rebuild to change model)

## Performance Comparison

| Metric | Inline Image | Pre-Built Image | Pre-Built + Model |
|--------|--------------|-----------------|-------------------|
| **First Deploy** | 5-8 min | 2-3 min | 1 min |
| **Code Redeploy** | 5-8 min | 10-20 sec | 10-20 sec |
| **Cold Start** | 2-3 min | 30-60 sec | 10-20 sec |
| **Image Size** | ~4 GB | ~4-5 GB | ~23 GB |
| **Flexibility** | High | High | Low |
| **Maintenance** | Easy | Easy | Hard |

**Current Implementation:** Pre-Built Image (Option 1)

## Troubleshooting

### Import Error: `No module named 'lift_sys.infrastructure.modal_image'`

**Cause:** Image not built or not in Modal's registry

**Solution:**
```bash
modal image build lift_sys/infrastructure/modal_image.py::llm_image
```

### Image build fails with dependency conflicts

**Cause:** Version incompatibility

**Solution:**
1. Check `modal_image.py` for version pins
2. Update to compatible versions
3. Rebuild image

### Want to force rebuild

```bash
# Clear Modal's cache and rebuild
modal image build --force lift_sys/infrastructure/modal_image.py::llm_image
```

## Related Files

- `modal_image.py` - Base image definition
- `../inference/modal_app.py` - Uses the base image for inference
- `iac.py` - Infrastructure automation (scaling, deployment)
- `../../docs/MODAL_REFERENCE.md` - Complete Modal guide

## References

- Modal Image Documentation: https://modal.com/docs/guide/custom-container
- Modal Image Caching: https://modal.com/docs/guide/custom-container#caching
- SGLang Documentation: https://sgl-project.github.io/
- lift-sys Modal Guide: `../../docs/MODAL_REFERENCE.md`
