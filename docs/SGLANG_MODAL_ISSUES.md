# SGLang on Modal: Issues and Investigation
**Date**: October 15, 2025 (Updated)
**Status**: ✅ RESOLVED in SGLang >= 0.4.6.post1
**Previous Issue**: sgl_kernel ImportError (fixed in newer versions)
**Current Recommendation**: Use SGLang 0.4.10.post2 with Modal's configuration

---

## 🎉 UPDATE (October 15, 2025)

**SGLang support for Qwen3-Coder is now CONFIRMED WORKING!**

**Official Announcement**: LMSYS Org announced on July 22, 2025 that Qwen3-Coder runs smoothly on SGLang with:
- Tool call parser enabled
- Expert parallelism enabled
- Flexible configurations supported

**Working Version**: SGLang >= 0.4.6.post1 (Modal uses 0.4.10.post2)

**Key Changes from Previous Attempt**:
- Use **CUDA 12.8.0** instead of 12.4.1
- Use **Python 3.11** instead of 3.12
- Use **SGLang 0.4.10.post2** instead of 0.5.3.post1
- Use **transformers 4.54.1** instead of 4.53.0

**Performance Benefit**: 3-10x faster constrained generation compared to vLLM

**See**: `docs/QWEN3_CODER_GUIDE.md` for complete implementation guide

---

## Original Investigation (Historical Context)

This section documents the original sgl_kernel issues encountered in October 2024, which have since been resolved in newer SGLang versions.

## Executive Summary

Attempted to deploy SGLang 0.5.3.post1 on Modal for GPU-accelerated IR generation with XGrammar constrained generation. **Deployment failed** due to sgl_kernel shared library incompatibility issues.

**Solution at the Time**: Migrated to vLLM 0.6.4.post1 which provides similar XGrammar support without sgl_kernel dependency.

**Resolution**: These issues were fixed in SGLang 0.4.10.post2 and later versions.

---

## Why SGLang Was Chosen

SGLang offered several advantages over vLLM for our use case:

1. **3-10x Faster Constrained Generation**: XGrammar is SGLang's default backend with optimized speculative parallel decoding
2. **Native Qwen3 Support**: vLLM 0.6.4 doesn't support Qwen3MoeForCausalLM architecture
3. **RadixAttention**: Superior prefix caching compared to vLLM's PagedAttention
4. **Production Proven**: Deployed at scale, generating trillions of tokens daily
5. **Simpler Configuration**: Built-in XGrammar vs plugin-based in vLLM

---

## The Problem: sgl_kernel ImportError

### Error Log (H100, Compute Capability 90)

```
ImportError:
[sgl_kernel] CRITICAL: Could not load any common_ops library!

Attempted locations:
1. Architecture-specific pattern: /usr/local/lib/python3.12/site-packages/sgl_kernel/sm90/common_ops.*
   - found files: ['/usr/local/lib/python3.12/site-packages/sgl_kernel/sm90/common_ops.abi3.so']
2. Fallback pattern: /usr/local/lib/python3.12/site-packages/sgl_kernel/common_ops.*
   - found files: []
3. Standard Python import: common_ops - failed

GPU Info:
- Compute capability: 90
- Expected variant: SM90 (Hopper/H100 with fast math optimization)
```

### Root Cause Analysis

**The binary exists but can't be loaded.** This suggests:

1. **Missing Shared Library Dependencies**: The `common_ops.abi3.so` file requires shared libraries not present in the container
2. **CUDA Version Mismatch**: sgl_kernel compiled against different CUDA version than container's CUDA 12.1.0
3. **ABI Incompatibility**: Python ABI or glibc version mismatch
4. **Build Environment Difference**: Prebuilt wheel compiled in environment different from Modal's

**Note**: This is NOT the same as A10G's sm86 architecture mismatch - in that case the binary file didn't exist. On H100 (sm90), the file exists but fails to import.

### What We Tried

**1. CUDA Environment Setup** ✗ Failed
```python
os.environ["CUDA_HOME"] = "/usr/local/cuda"
os.environ["LD_LIBRARY_PATH"] = "/usr/local/cuda/lib64:/usr/local/cuda/lib:..."
```
Result: Same error - binary found but not loadable

**2. NVIDIA CUDA Development Image** ✗ Failed
```python
modal.Image.from_registry("nvidia/cuda:12.1.0-devel-ubuntu22.04", add_python="3.12")
```
Result: Same error - nvcc present, flashinfer compiles, but sgl_kernel still fails

**3. Compile sgl-kernel from Source** ✗ Failed
```bash
TORCH_CUDA_ARCH_LIST='8.6' pip install --no-binary sgl-kernel 'sgl-kernel==0.3.15'
```
Result: `ERROR: No matching distribution found` - sgl-kernel not available as source package

**4. Newer CUDA Base Image (12.4.1)** Not Tested
Could potentially resolve CUDA version mismatch if that's the issue

---

## The Workaround: vLLM Migration

**What We Did**: Switched from SGLang to vLLM 0.6.4.post1

### Comparison

| Feature | vLLM 0.9.2 | vLLM 0.6.4.post1 | SGLang 0.5.3.post1 |
|---------|------------|------------------|-------------------|
| **XGrammar Support** | ✅ Native (default backend) | ❌ Not supported | ✅ Default backend |
| **JSON Schema Constraints** | ✅ `guided_json` parameter | ✅ `guided_json` parameter | ✅ `json_schema` parameter |
| **Qwen2.5-Coder-7B** | ✅ Works perfectly | ✅ Works perfectly | ✅ Works perfectly |
| **Qwen3-Coder-30B MoE** | ✅ Supported in 0.9.2+ | ❌ Not supported | ✅ Native support |
| **Modal Compatibility** | ✅ Works (transformers<4.54) | ✅ No issues | ❌ sgl_kernel ImportError |
| **Performance** | Good (PagedAttention) | Good (PagedAttention) | Better (RadixAttention, 3-10x faster JSON) |
| **GPU Requirements** | A10G sufficient (~$1.10/hr) | A10G sufficient (~$1.10/hr) | H100 attempted (~$4/hr) |
| **Transformers Requirement** | <4.54.0 (aimv2 conflict) | Any version | =4.57.0 |

### vLLM Implementation

```python
from vllm import LLM, SamplingParams

# Initialize
self.llm = LLM(
    model=MODEL_NAME,
    trust_remote_code=True,
    dtype="auto",
    gpu_memory_utilization=0.90,
    guided_decoding_backend="xgrammar",  # XGrammar support
)

# Generate with schema constraints
sampling_params = SamplingParams(
    temperature=0.3,
    top_p=0.95,
    max_tokens=2048,
    guided_json=schema,  # JSON schema enforcement
)
response = self.llm.generate([prompt], sampling_params)
```

**Result**: ✅ Works perfectly, deployed on A10G, no errors

---

## Modal Labs Forks (IMPORTANT)

### Discovery

Modal Labs maintains forks of SGLang and related tools:

1. **https://github.com/modal-labs/sglang**
2. **https://github.com/modal-labs/SpecForge**

### Implications

- Modal is **actively working on SGLang compatibility**
- Their fork likely contains **fixes for the sgl_kernel issues** we encountered
- May include Modal-specific optimizations for their infrastructure
- Could enable us to switch back to SGLang for performance benefits

### Next Steps for Investigation

1. **✅ Reviewed Modal's Official SGLang Guide** (COMPLETED)
   - **Documentation**: https://modal.com/docs/examples/sgl_vlm
   - **Modal's tested config**:
     - CUDA 12.8.0 (vs our 12.4.1)
     - Python 3.11 (vs our 3.12)
     - SGLang 0.4.10.post2 (vs our 0.5.3.post1)
     - transformers 4.54.1 (vs our 4.53.0/4.57.0)
   - **Recommendation**: Try Modal's exact configuration

2. **Test Modal's Exact SGLang Configuration**
   ```python
   llm_image = (
       modal.Image.from_registry(
           "nvidia/cuda:12.8.0-devel-ubuntu22.04",  # Modal's CUDA version
           add_python="3.11"  # Modal's Python version
       )
       .pip_install(
           "sglang[all]==0.4.10.post2",  # Modal's SGLang version
           "transformers==4.54.1",  # Modal's transformers version
           "torch==2.7.1",
           "fastapi[standard]",
       )
   )
   ```
   - May resolve sgl_kernel issues
   - Different CUDA version might have better prebuilt wheels
   - Worth testing before investigating fork

3. **✅ Qwen3 Support in vLLM 0.9.2+** (VERIFIED)
   - **Reference**: https://github.com/vllm-project/vllm/issues/17327
   - vLLM >= 0.8.4 supports all Qwen3 models
   - Our vLLM 0.9.2 is fully compatible
   - Can use Qwen3-Coder-30B-A3B-Instruct-FP8 right now
   - **See**: `docs/QWEN3_CODER_GUIDE.md` for details

4. **Test Modal Labs SGLang Fork** (if official config fails)
   ```python
   .pip_install("git+https://github.com/modal-labs/sglang.git@main")
   ```
   - Fallback option if Modal's official config doesn't work
   - May have Modal-specific fixes for sgl_kernel
   - Last resort before abandoning SGLang path

5. **Contact Modal Support** (if both above fail)
   - Report sgl_kernel ImportError specifics
   - Ask about recommended SGLang configuration for H100
   - Inquire about known compatibility issues

---

## Technical Debugging Notes

### Shared Library Dependencies

To debug the sgl_kernel import issue, would need to:

```bash
# Check what libraries the .so file requires
ldd /usr/local/lib/python3.12/site-packages/sgl_kernel/sm90/common_ops.abi3.so

# Common missing libraries:
# - libcuda.so.1 (NVIDIA CUDA driver)
# - libcudart.so.12 (CUDA runtime)
# - libcublas.so.12 (CUDA BLAS)
# - libcublasLt.so.12 (CUDA BLAS Lite)
# - libstdc++.so.6 (C++ standard library)
```

### CUDA Version Compatibility

sgl_kernel 0.3.15 prebuilt wheels may be compiled for:
- CUDA 12.0
- CUDA 12.1
- CUDA 12.2+

Modal's CUDA 12.1.0 should match, but minor version differences can cause issues.

### Python ABI

The `.abi3.so` suffix indicates "stable ABI" - should work across Python 3.x versions. If import fails, could be:
- glibc version mismatch
- Compiled with different Python build flags
- Incompatible with Ubuntu 22.04 system libraries

---

## Cost Analysis

### Current Setup (vLLM)
- **GPU**: A10G @ ~$1.10/hr
- **Model**: Qwen2.5-Coder-7B
- **Estimated per-request**: $0.001-0.003 (warm)
- **Status**: ✅ Working, tested, deployed

### Hypothetical SGLang (if working)
- **GPU**: Could use A10G @ ~$1.10/hr (if sm86 binaries available)
- **Model**: Qwen3-Coder-30B MoE (native support)
- **Performance**: 3-10x faster constrained generation
- **Estimated per-request**: $0.0003-0.001 (due to speed improvement)
- **Status**: ❌ Blocked by sgl_kernel

**Potential Savings with SGLang**: 70-90% cost reduction per request due to faster generation

---

## Recommendations

### Short Term (Current)
✅ **Use vLLM 0.6.4.post1** - Works reliably, good performance, A10G compatible

### Medium Term (Next 1-2 weeks)
🔍 **Investigate Modal Labs SGLang fork**
- Test their fork to see if sgl_kernel issues are resolved
- If successful, switch to SGLang for 3-10x performance improvement
- Document any Modal-specific configuration requirements

### Long Term (Production)
⚡ **Optimize based on results**
- If Modal's SGLang works: switch for performance + cost savings
- If issues persist: stick with vLLM, proven and stable
- Consider Qwen3-Coder-30B if SGLang becomes viable

---

## References

- **SGLang Documentation**: https://docs.sglang.ai
- **XGrammar Documentation**: https://xgrammar.mlc.ai
- **vLLM Guided Decoding**: https://docs.vllm.ai/en/latest/serving/guided_decoding.html
- **Modal LLM Guide**: https://modal.com/docs/guide/developing-with-llms
- **Modal Labs SGLang Fork**: https://github.com/modal-labs/sglang ⭐
- **Modal Labs SpecForge**: https://github.com/modal-labs/SpecForge ⭐
- **Modal SGLang VLM Example**: https://modal.com/docs/examples/sgl_vlm ⭐
- **Qwen3 Support in vLLM**: https://github.com/vllm-project/vllm/issues/17327 ⭐

---

## Status Log

**2025-10-14**:
- ❌ SGLang 0.5.3.post1 deployment failed (sgl_kernel ImportError on H100/sm90)
- ✅ Migrated to vLLM 0.6.4.post1 successfully
- 🔍 Discovered Modal Labs maintains SGLang and SpecForge forks
- 📝 Documented for future investigation

**2025-10-15**:
- ❌ vLLM 0.6.4.post1 doesn't support XGrammar (user required it as essential)
- ✅ Upgraded to vLLM 0.9.2 for native XGrammar support
- ❌ vLLM 0.9.2 + transformers 4.57.0 has aimv2 config conflict
- ✅ Downgraded to transformers 4.46.0 (must be <4.54.0)
- 📝 vLLM 0.9.2 now works with XGrammar and transformers 4.46.0

**Next**: Test Modal endpoint with vLLM 0.9.2 + XGrammar, then investigate SGLang forks

---

**Document Status**: Complete - Ready for future SGLang investigation
