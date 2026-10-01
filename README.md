# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment. Every figure is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware and engine it was measured on. This README is **automatically regenerated** from `data/models.json` — see [AGENTS.md](AGENTS.md) and `skills/gather-data.md`.

**Ranked by 7-day X engagement** (likes/comments/views), retained through a 30-day window. Within a rank, models sort by **highest t/s** with the **one engine** that produced it. t/s is always shown **per engine**.

> Last generated: 2026-10-01 14:46 UTC. Source: lightbrd.com mirror (X posts).

---

## ❤️ Most loved open-weight models on X (ranked by 7-day engagement)

| Model | Full name | HF link | Why people love it | CUDA t/s (engine) | Metal t/s (engine) | VRAM |
|---|---|---|---|---|---|---|
| **Bonsai 2 27B** | Ternary-Bonsai-2-27B | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | PrismML 1.75-bit ternary compression of Qwen3.8-27B; ~98.2% capability in 5.9 GB. 11,792 downloads in 5 days. Runs big-VRAM-quality (262K ctx, MTP, vision on 16 GB) on old low-end cards. | 50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 12GB, Bonsai 2 PTQ1_0 + MTP head + gaming-GPU kernel fix)<br>71 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5060 Ti 16GB, MTP head)<br>143 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, ternary PTQ1_0, ~5.9 GB)<br>91 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4070 12GB, PTQ1_0-mtp-lean (6.3 GB)) | 237 ([MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine), Apple Silicon 16GB Mac, mlx.fast 4-bit) | 12GB |
| **Qwen3.8-27B** | Qwen3.8-27B-Instruct | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | Flagship local model. 384K views on release. 262K ctx (1M via YaRN). | 381 ([vLLM](https://github.com/vllm-project/vllm), single RTX 3090 24GB (~250W), DFlash2 spec-decode + context lookup, 16-token verify blocks, quantized KV/heads/activations)<br>43.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090 Laptop, Q4_K_M)<br>118 ([llama.cpp](https://github.com/ggml-org/llama.cpp), single RTX 3090 24GB, 4-bit, DFlash2 draft, 131K ctx decode)<br>219.8 ([SGLang](https://github.com/sgl-project/sglang), 2x RTX 3090 24GB, AutoRound INT4, FP8 KV cache, dual-superfast config, 262K ctx, code decode) | 189 ([TensorFold](https://github.com/ashhart/TensorFold), MacBook Pro M5 Max, MLX 4-bit, DFlash2 spec-decode)<br>124 ([TensorFold](https://github.com/ashhart/TensorFold), MacBook Pro M5 Max, 4-bit MLX) | 16GB |
| **Nemotron 3.5 Lightning** | NVIDIA Nemotron 3.5 Lightning 30B-A3B | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16) | NVIDIA Nemotron 3.5 Lightning 30B-A3B — see source posts. | — | 206 ([TensorFold](https://github.com/ashhart/TensorFold), MacBook Pro M5 Max, MLX 4-bit) | 128GB |
| **Ornith 1.5** | Ornith 1.5 (9B) | [link](https://huggingface.co/ornith-ai/Ornith-1.5-9B-GGUF) | Ornith 1.5 (9B) — see source posts. | — | 50 ([MLX](https://github.com/ml-explore/mlx), MacBook Pro M5 48GB, MLX 4-bit) | 48GB |
| **RavenX-Conjecture-Qwen3-8B-MLX** | RavenX-Conjecture-Qwen3-8B-MLX | [link](https://huggingface.co/deadbydawn101/RavenX-Conjecture-Qwen3-8B-MLX) | RavenX-Conjecture-Qwen3-8B-MLX — see source posts. | — | 42 ([MLX](https://github.com/ml-explore/mlx), Apple M3) | 8GB |
| **Qwen3.6-35B-A3B** | Qwen3.6-35B-A3B (MoE) | [link](https://huggingface.co/https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | UC Berkeley FreeToken serves a 35B MoE on an 8GB GPU (2-4x faster than Ollama) by splitting expert misses between GPU and CPU. | 39.3 ([FreeToken](https://github.com/FlashML-org/FreeToken), 8GB GPU (MoE experts split GPU/RAM), MoE expert offload, GPU+CPU bandwidth-split) | — | 8 GB |
| **DeepSeek-V4-Flash** | DeepSeek-V4-Flash 284B (MoE) | [link](https://huggingface.co/https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | 284B MoE served on a 32GB consumer GPU via FreeToken's GPU+CPU bandwidth-split inference. | 22 ([FreeToken](https://github.com/FlashML-org/FreeToken), 32GB GPU (MoE experts split GPU/RAM), MoE 6-of-256 experts/layer active, hybrid offload) | — | 32 GB |
| **GLM-5.2** | GLM-5.2 753B (MoE) | [link](https://huggingface.co/https://huggingface.co/zai-org/GLM-5.2) | 753B frontier MoE run locally on a 96GB GPU with FreeToken's bandwidth-aware expert offload. | 14.9 ([FreeToken](https://github.com/FlashML-org/FreeToken), 96GB GPU (MoE experts split GPU/RAM), MoE expert offload, hybrid GPU+CPU execution) | — | 96 GB |
| **Vitanom (llama.cpp CPU)** | Vitanom — offline Android llama.cpp CPU knowledge app | [link](https://huggingface.co/google/gemma-3-4b-it) | In-window (Sep 29) CPU-only edge deployment: llama.cpp on Android, no GPU backend, KleidiAI CPU path, mmap from flash. Runs Gemma 3 4B and Qwen3-30B-A3B offline. Post reports only qualitative speed ('a few tokens per second'); no clean numeric t/s figure was provided, so no t/s is fabricated. | 0 ([llama.cpp](https://github.com/ggml-org/llama.cpp), Android ARM64 CPU (no GPU, KleidiAI, mmap-from-flash), Gemma 3 4B Q4_K_M / Qwen3-30B-A3B UD-Q2_K_XL) | — | 2.5GB RAM (Gemma 3 4B Q4_K_M) / 11.8GB (Qwen3-30B-A3B) |
| **Muse Glimmer 30B** | Muse-Glimmer-30B | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | Meta Superintelligence 30B agentic model, Apache 2.0. Fits 24/32 GB at 4-bit (<20GB weights + KV + vision + spec draft). DFlash drafter gives 3.1x decode on RTX 5090. | 233 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, 4-bit + DFlash spec-decode drafter (3.1x over 74.9 baseline)) | 50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), M5 Max (Apple Silicon), 4-bit) | 24GB |
| **Qwen3 8B** | Qwen3-8B | [link](https://huggingface.co/Qwen/Qwen3-8B) | The default 8 GB pick. Fast, Apache 2.0. | 100 ([Ollama](https://github.com/ollama/ollama), RTX 4060, Q4_K_M) | — | 8GB |
| **Qwen3 14B** | Qwen3-14B | [link](https://huggingface.co/Qwen/Qwen3-14B) | 2M HF downloads. The community mid-size favorite. | 65 ([Ollama](https://github.com/ollama/ollama), RTX 3090, Q4_K_M) | — | 9GB |
| **Gemma 4 12B** | gemma-4-12B-it | [link](https://huggingface.co/google/gemma-4-12B-it) | Best overall personal-agent model. Multimodal + audio, 256K ctx. | 99.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4090 Laptop, Q4) | 49.67 ([llama.cpp](https://github.com/ggml-org/llama.cpp), Apple Silicon, Q4) | 9GB |
| **Qwen3.8-Flash-Next** | Qwen3.8-Flash-Next 125B (MoE) | [link](https://huggingface.co/https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 125B MoE run across dual DGX Sparks with MTP sustained ~45 tok/s for long autonomous agent/coding sessions; also runs EXL3 2.50bpw on a single 3090. | 45 ([vLLM](https://github.com/vllm-project/vllm), 2x NVIDIA DGX Spark, tensor-parallel over one cable, official FP8, MTP, 256K context) | — | 128 GB |
| **Qwen 3.6 27B** | Qwen3.6-27B | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | Strongest local coding model (SWE-bench 77.2%). | 37 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3090, Q4_K_M) | — | 18GB |

---

# 🟦 CUDA — NVIDIA GPUs (8–48 GB)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [vLLM](https://github.com/vllm-project/vllm) 381 (2026-09-19); [llama.cpp](https://github.com/ggml-org/llama.cpp) 43.7 (2026-09-18); [llama.cpp](https://github.com/ggml-org/llama.cpp) 118 (2026-09-13); [SGLang](https://github.com/sgl-project/sglang) 219.8 (2026-09-12) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 233 (2026-08-10) |
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 71 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 91 (2026-09-26) |
| **Qwen3 8B** | 8B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-8B) | 8GB | [Ollama](https://github.com/ollama/ollama) 100 (2026-09-12) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 99.7 (2026-09-19) |
| **Qwen3 14B** | 14B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-14B) | 9GB | [Ollama](https://github.com/ollama/ollama) 65 (2026-09-15) |
| **Qwen3.8-Flash-Next** | 125B | Apache 2.0 | [link](https://huggingface.co/https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 128 GB | [vLLM](https://github.com/vllm-project/vllm) 45 (2026-09-17) |
| **Qwen3.6-35B-A3B** | 35B (3B active) | Apache 2.0 | [link](https://huggingface.co/https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 8 GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-27) |
| **Qwen 3.6 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | 18GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 37 (2026-09-10) |
| **DeepSeek-V4-Flash** | 284B (13B active) | DeepSeek license | [link](https://huggingface.co/https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | 32 GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (2026-09-27) |
| **GLM-5.2** | 753B | Z.ai license | [link](https://huggingface.co/https://huggingface.co/zai-org/GLM-5.2) | 96 GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 14.9 (2026-09-27) |

---

# 🟨 CPU — no GPU

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Vitanom (llama.cpp CPU)** | 4B/30B-A3B | Open source (llama.cpp runtime) | [link](https://huggingface.co/google/gemma-3-4b-it) | 2.5GB RAM (Gemma 3 4B Q4_K_M) / 11.8GB (Qwen3-30B-A3B) | [llama.cpp](https://github.com/ggml-org/llama.cpp) 0 (2026-09-29) |

> CPU inference is **memory-bandwidth bound**. Use Q4 quant + a fast CPU build (AVX-512/AMX).

---

# 🟩 Metal — Apple Silicon (unified memory)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) 237 (2026-09-26) |
| **Nemotron 3.5 Lightning** | 30B-A3B | NVIDIA Open Model License | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16) | 128GB | [TensorFold](https://github.com/ashhart/TensorFold) 206 (2026-09-30) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [TensorFold](https://github.com/ashhart/TensorFold) 189 (2026-09-30); [TensorFold](https://github.com/ashhart/TensorFold) 124 (2026-09-20) |
| **Ornith 1.5** | 9B | Apache 2.0 | [link](https://huggingface.co/ornith-ai/Ornith-1.5-9B-GGUF) | 48GB | [MLX](https://github.com/ml-explore/mlx) 50 (2026-09-29) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (2026-08-10) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 49.67 (2026-09-19) |
| **RavenX-Conjecture-Qwen3-8B-MLX** | 8B | Apache 2.0 | [link](https://huggingface.co/deadbydawn101/RavenX-Conjecture-Qwen3-8B-MLX) | 8GB | [MLX](https://github.com/ml-explore/mlx) 42 (2026-09-29) |

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
