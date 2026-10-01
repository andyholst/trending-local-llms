# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment. Every figure is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware and engine it was measured on. This README is **automatically regenerated** from `data/models.json` — see [AGENTS.md](AGENTS.md) and `skills/gather-data.md`.

**Ranked by 7-day X engagement** (likes/comments/views), retained through a 30-day window. Within a rank, models sort by **highest t/s** with the **one engine** that produced it. t/s is always shown **per engine**.

> Last generated: 2026-10-01 22:41 UTC. Source: lightbrd.com mirror (X posts).

---

## ❤️ Most loved open-weight models on X (ranked by 7-day engagement)

| Model | Full name | HF link | Why people love it | CUDA t/s (engine) | Metal t/s (engine) | VRAM |
|---|---|---|---|---|---|---|
| **Bonsai 2 27B** | Ternary-Bonsai-2-27B | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | PrismML 1.75-bit ternary compression of Qwen3.8-27B; ~98.2% capability in 5.9 GB. 11,792 downloads in 5 days. Runs big-VRAM-quality (262K ctx, MTP, vision on 16 GB) on old low-end cards. | 50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 12GB, Q2_0 ternary PTQ1_0 + MTP)<br>71 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5060 Ti 16GB, MTP head)<br>91 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4070 12GB, PTQ1_0-mtp-lean (6.3 GB))<br>143 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090 32GB, tern 27B MoE) | 237 ([MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine), Apple Silicon 16GB Mac, mlx.fast 4-bit) | 12GB |
| **Qwen3.8-27B** | Qwen3.8-27B-Instruct | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | Flagship local model. 384K views on release. 262K ctx (1M via YaRN). | 381 ([DFlash2](https://github.com/z-lab/dflash), RTX 3090 24GB, DFlash2 context-lookup 15/16 accept + prefix cache)<br>43.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090 Laptop, Q4_K_M)<br>134 ([DFlash2](https://github.com/z-lab/dflash), RTX 3090 24GB, DFlash2 speculative decode) | 124 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon (M3 Ultra 512GB), 4-bit MLX)<br>124 ([TensorFold](https://github.com/ashhart/TensorFold), MacBook Pro M5 Max, 4-bit MLX)<br>70 ([DFlash2](https://github.com/z-lab/dflash), M5 Max MacBook Pro, 4-bit MLX) | 16GB |
| **Nemotron 3.5 Lightning** | NVIDIA-Nemotron-3.5-Lightning-30B-A3B | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4) | 188-206 tok/s on M5 Max via TensorFold speculative decoding. | — | 206 ([TensorFold](https://github.com/ashhart/TensorFold), M5 Max (Apple Silicon), 4-bit MLX) | 24GB |
| **Qwen3 8B** | Qwen3-8B | [link](https://huggingface.co/Qwen/Qwen3-8B) | The default 8 GB pick. Fast, Apache 2.0. | 100 ([Ollama](https://github.com/ollama/ollama), RTX 4060, Q4_K_M) | 42 ([MLX](https://github.com/ml-explore/mlx), M3 (Apple Silicon), MLX) | 8GB |
| **Qwen3.8-Flash-Next** | Qwen3.8-Flash-Next | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 88-92 tok/s on Apple Silicon via TensorFold. | — | 92 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon (M3 Ultra), 4-bit MLX) | 48GB |
| **Muse Glimmer 30B** | Muse-Glimmer-30B | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | Meta Superintelligence 30B agentic model, Apache 2.0. Fits 24/32 GB at 4-bit (<20GB weights + KV + vision + spec draft). DFlash drafter gives 3.1x decode on RTX 5090. | 233 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090 32GB, 4-bit + DFlash drafter) | 50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), M5 Max (Apple Silicon), 4-bit) | 24GB |
| **Qwen3 14B** | Qwen3-14B | [link](https://huggingface.co/Qwen/Qwen3-14B) | 2M HF downloads. The community mid-size favorite. | 65 ([Ollama](https://github.com/ollama/ollama), RTX 3090, Q4_K_M) | — | 9GB |
| **Gemma 4 12B** | gemma-4-12B-it | [link](https://huggingface.co/google/gemma-4-12B-it) | Best overall personal-agent model. Multimodal + audio, 256K ctx. | 99.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4090 Laptop, Q4) | 49.67 ([llama.cpp](https://github.com/ggml-org/llama.cpp), Apple Silicon, Q4) | 9GB |
| **Qwen 3.6 27B** | Qwen3.6-27B | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | Strongest local coding model (SWE-bench 77.2%). | 37 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3090, Q4_K_M) | — | 18GB |
| **Qwen3.6-35B** | Qwen3.6-35B | [link](https://huggingface.co/Qwen/Qwen3.6-35B) | FreeToken runs Qwen3.6-35B on an 8GB GPU at 39.3 t/s. | 39.3 ([FreeToken](https://github.com/FlashML-org/FreeToken), 8GB GPU, MoE on small GPU) | — | 8GB |
| **DeepSeek-V4-Flash** | DeepSeek-V4-Flash | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | ~80GB DeepSeek V4 Flash MoE on a 5090 32GB + 64GB RAM at 22 t/s once warm. | 22 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090 32GB + 64GB RAM, Q2_0 ~80GB MoE offload) | — | 48GB |

---

# 🟦 CUDA — NVIDIA GPUs (8–48 GB)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [DFlash2](https://github.com/z-lab/dflash) 381 (2026-10-01); [llama.cpp](https://github.com/ggml-org/llama.cpp) 43.7 (2026-09-18); [DFlash2](https://github.com/z-lab/dflash) 134 (2026-08-22) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 233 (2026-08-10) |
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 71 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 91 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-26) |
| **Qwen3 8B** | 8B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-8B) | 8GB | [Ollama](https://github.com/ollama/ollama) 100 (2026-09-12) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 99.7 (2026-09-19) |
| **Qwen3 14B** | 14B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-14B) | 9GB | [Ollama](https://github.com/ollama/ollama) 65 (2026-09-15) |
| **Qwen3.6-35B** | 35B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-35B) | 8GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-08-13) |
| **Qwen 3.6 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | 18GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 37 (2026-09-10) |
| **DeepSeek-V4-Flash** | ~300B | DeepSeek License | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | 48GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 22 (2026-08-25) |

---

# 🟨 CPU — no GPU

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
_No models measured on this backend yet._

> CPU inference is **memory-bandwidth bound**. Use Q4 quant + a fast CPU build (AVX-512/AMX).

---

# 🟩 Metal — Apple Silicon (unified memory)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) 237 (2026-09-26) |
| **Nemotron 3.5 Lightning** | 30B-A3B | MIT | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4) | 24GB | [TensorFold](https://github.com/ashhart/TensorFold) 206 (2026-09-30) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [TensorFold](https://github.com/ashhart/TensorFold) 124 (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 124 (2026-09-20); [DFlash2](https://github.com/z-lab/dflash) 70 (2026-08-18) |
| **Qwen3.8-Flash-Next** | 125B-A22B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 48GB | [TensorFold](https://github.com/ashhart/TensorFold) 92 (2026-09-27) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (2026-08-10) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 49.67 (2026-09-19) |
| **Qwen3 8B** | 8B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-8B) | 8GB | [MLX](https://github.com/ml-explore/mlx) 42 (2026-09-29) |

> On Apple Silicon, **MLX** is the fastest engine; **TensorFold** adds speculative decoding (3–6x on memory-bound Macs); **MLX-fast Bonsai 2** (Layr-Labs/mlxfast-bonsai2-27b-engine) pushes Ternary Bonsai 2 27B to ~237 tok/s on a 16 GB Mac.

---

## ⚙️ Inference engine / server guide

| Engine | Backend | Best for |
|---|---|---|
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | CUDA / CPU / Metal | Max control, custom quants |
| [Ollama](https://github.com/ollama/ollama) | CUDA / CPU / Metal | Easiest start |
| [FreeToken](https://github.com/FlashML-org/FreeToken) | CUDA | Big MoE on small GPUs |
| [vLLM](https://github.com/vllm-project/vllm) | CUDA | Production serving, high throughput |
| [SGLang](https://github.com/sgl-project/sglang) | CUDA | High-throughput serving |
| [MLX](https://github.com/ml-explore/mlx) | Metal | Fastest on Apple Silicon |
| [TensorFold](https://github.com/ashhart/TensorFold) | Metal | Speculative decoding on Mac, 3-6x |
| [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) | CUDA | Max NVIDIA perf |
| [LiteRT](https://github.com/google-ai-edge/LiteRT) | CUDA / Metal | Google local runtime |
| [Strata](https://github.com/Niko1221/Strata) | CUDA | Runs big MoE (Qwen3.8-Flash-Next 125B) on 8-48 GB NVIDIA GPUs; experts across GPU/RAM/SSD, speculative decoding ~1.6-1.8x |
| [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) | Metal | Speedup benchmark engine for Ternary Bonsai 2 27B on Apple Silicon; ~237 tok/s decode on 16 GB Mac (mlx.fast, Yukon/Layr-Labs) |
| [DFlash2](https://github.com/z-lab/dflash) | CUDA | Speculative decoding + context-lookup (Inco AI / syv-ai); Qwen3.8-27B ~118-133 tok/s chat, up to ~381 tok/s context-lookup on 24 GB RTX 3090 |
| [WebLLM](https://github.com/mlc-ai/web-llm) | CUDA / Metal | In-browser LLM inference accelerated with WebGPU (MLC-LLM). |

**Quick picks:** Ollama (just works) · llama.cpp (gaming laptop, max speed) · FreeToken (big MoE on small GPU) · MLX + TensorFold + MLX-fast (Mac) · Strata (125B MoE on 12–24 GB) · vLLM + DFlash2 (spec decode) · llama.cpp CPU (tiny/edge).

---

## How to contribute

- Update `data/models.json` (add/refresh a model row with real X-sourced engagement and per-engine t/s), then run `python3 scripts/update_trending.py` to regenerate the README.
- Include: full model name, HF link, license, params, type, VRAM tier, a **measured** t/s + **engine + hardware + quant**, and the source X post.
- Prefer numbers from real X benchmark posts over vendor claims. Data is **community-reported on X** — directional, not lab-grade; mark projections `(est)`.
- All changes go through a **feature branch + PR**; automation never pushes to/merges `master` directly.

## License

Apache License 2.0. See [LICENSE](LICENSE).
