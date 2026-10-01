# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment. Every figure is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware and engine it was measured on. This README is **automatically regenerated** from `data/models.json` — see [AGENTS.md](AGENTS.md) and `skills/gather-data.md`.

**Ranked by 7-day X engagement** (likes/comments/views), retained through a 30-day window. Within a rank, models sort by **highest t/s** with the **one engine** that produced it. t/s is always shown **per engine**.

> Last generated: 2026-10-01 20:02 UTC. Source: lightbrd.com mirror (X posts).

---

## ❤️ Most loved open-weight models on X (ranked by 7-day engagement)

| Model | Full name | HF link | Why people love it | CUDA t/s (engine) | Metal t/s (engine) | VRAM |
|---|---|---|---|---|---|---|
| **Ternary Bonsai 27B** | Ternary-Bonsai-2-27B | [link](https://huggingface.co/PrismML/Ternary-Bonsai-2-27B) | Ternary-Bonsai-2-27B — see source posts. | 143 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4060 8GB, ternary 5.9GB)<br>237.4 ([FreeToken](https://github.com/FlashML-org/FreeToken), RTX 3060 12GB + 5GB system, ternary 27B MoE) | — | 12GB |
| **Qwen3.8-27B** | Qwen3.8-27B-Instruct | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | Flagship local model. 384K views on release. 262K ctx (1M via YaRN). | 43.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090 Laptop, Q4_K_M) | 124 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon (M-series), MLX 4-bit)<br>41.5 ([TensorFold](https://github.com/ashhart/TensorFold), MacBook Pro M3 Max 96GB, MLX 4-bit + DFlash2 8-bit drafter) | 16GB |
| **Nemotron 3.5 Lightning 30B-A3B** | NVIDIA-Nemotron-3.5-Lightning-30B-A3B | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16) | NVIDIA's 30B-A3B MoE hitting 188-206 tok/s on Apple Silicon via TensorFold MLX spec-decode. | — | 206 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon (M-series), MLX 4-bit) | 32GB |
| **Qwen3.8-Flash-Next** | Qwen3.8-Flash-Next | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | Large Qwen3.8 MoE at 88-92 tok/s on Apple Silicon via TensorFold MLX speculative decode. | — | 92 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon (M-series), MLX 4-bit) | 48GB |
| **Qwen3.6 35B A3B** | Qwen3.6-35B-A3B | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | Qwen3.6-35B-A3B — see source posts. | 39.3 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4060 8GB, NVFP4 35B-A3B)<br>39.3 ([FreeToken](https://github.com/FlashML-org/FreeToken), RTX 4060 laptop 8GB, NVFP4 MoE on 8GB) | — | 12GB |
| **Bonsai 2 27B** | Ternary-Bonsai-2-27B | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | PrismML 1.75-bit ternary compression of Qwen3.8-27B; ~98.2% capability in 5.9 GB. 11,792 downloads in 5 days. Runs big-VRAM-quality (262K ctx, MTP, vision on 16 GB) on old low-end cards. | 67-71 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5060 Ti 16GB, MTP head)<br>60-91 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4070 12GB, PTQ1_0-mtp-lean (6.3 GB))<br>~50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 12GB, MTP + kernel fix)<br>143 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, ternary) | ~237 ([MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine), Apple Silicon 16GB Mac, mlx.fast 4-bit) | 12GB |
| **Qwen3 8B** | Qwen3-8B | [link](https://huggingface.co/Qwen/Qwen3-8B) | The default 8 GB pick. Fast, Apache 2.0. | 100 ([Ollama](https://github.com/ollama/ollama), RTX 4060, Q4_K_M) | — | 8GB |
| **Qwen3 14B** | Qwen3-14B | [link](https://huggingface.co/Qwen/Qwen3-14B) | 2M HF downloads. The community mid-size favorite. | 65 ([Ollama](https://github.com/ollama/ollama), RTX 3090, Q4_K_M) | — | 9GB |
| **DFlash2 spec decode** | DFlash2 speculative decoding (llama.cpp) | [link](https://huggingface.co/z-lab/dflash) | DFlash2 speculative decoding (llama.cpp) — see source posts. | 381 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3090 24GB, spec decode 27B) | — | 16GB |
| **Gemma 4 12B** | gemma-4-12B-it | [link](https://huggingface.co/google/gemma-4-12B-it) | Best overall personal-agent model. Multimodal + audio, 256K ctx. | 99.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4090 Laptop, Q4) | 49.67 ([llama.cpp](https://github.com/ggml-org/llama.cpp), Apple Silicon, Q4) | 9GB |
| **Qwen 3.6 27B** | Qwen3.6-27B | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | Strongest local coding model (SWE-bench 77.2%). | 37 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3090, Q4_K_M) | — | 18GB |
| **Gemma 4 E2B** | Gemma 4 E2B (edge / Raspberry Pi 5) | [link](https://huggingface.co/google/gemma-4-E2B-it) | Gemma 4 E2B runs fully on a Raspberry Pi 5 CPU via LiteRT-LM at ~99 tok/s prefill and ~9 tok/s decode in only 1432 MB — a real edge/embedded, no-GPU deployment (Google dev blog via Shakthi). | 9 ([LiteRT](https://github.com/google-ai-edge/LiteRT), Raspberry Pi 5 CPU, 1432 MB peak (LiteRT-LM), Intel / LiteRT-LM full; prefill 99 tok/s, decode 9 tok/s) | — | edge |
| **Muse Glimmer 30B** | Muse-Glimmer-30B | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | Meta Superintelligence 30B agentic model, Apache 2.0. Fits 24/32 GB at 4-bit (<20GB weights + KV + vision + spec draft). DFlash drafter gives 3.1x decode on RTX 5090. | 233 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, 4-bit) | 50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), M5 Max (Apple Silicon), 4-bit) | 24GB |
| **DeepSeek-R1 1.5B** | DeepSeek-R1-1.5B (distill) | [link](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B) | A $35 Raspberry Pi 4B (2GB) from 2019 boots Ollama and serves DeepSeek-R1-1.5B offline at ~4 tok/s, no internet and ~5W under load — a pure CPU/embedded inference stack. | 4 ([Ollama](https://github.com/ollama/ollama), Raspberry Pi 4B 2GB LPDDR4, offline (CPU-only), community GGUF) | — | edge |

---

# 🟦 CUDA — NVIDIA GPUs (8–48 GB)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **DFlash2 spec decode** | n/a (draft engine) | MIT | [link](https://huggingface.co/z-lab/dflash) | 16GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 381 (2026-09-10) |
| **Ternary Bonsai 27B** | 27B MoE | Apache 2.0 | [link](https://huggingface.co/PrismML/Ternary-Bonsai-2-27B) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-28); [FreeToken](https://github.com/FlashML-org/FreeToken) 237.4 (2026-09-24) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 233 (2026-08-10) |
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 67-71 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 60-91 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) ~50 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-18) |
| **Qwen3 8B** | 8B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-8B) | 8GB | [Ollama](https://github.com/ollama/ollama) 100 (2026-09-12) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 99.7 (2026-09-19) |
| **Qwen3 14B** | 14B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-14B) | 9GB | [Ollama](https://github.com/ollama/ollama) 65 (2026-09-15) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 43.7 (2026-09-18) |
| **Qwen3.6 35B A3B** | 35B (3B active, MoE) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 39.3 (2026-09-24); [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-10) |
| **Qwen 3.6 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | 18GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 37 (2026-09-10) |

---

# 🟨 CPU — no GPU

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Gemma 4 E2B** | 2B | Apache-2.0 | [link](https://huggingface.co/google/gemma-4-E2B-it) | edge | [LiteRT](https://github.com/google-ai-edge/LiteRT) 9 (2026-09-05) |
| **DeepSeek-R1 1.5B** | 1.5B | MIT | [link](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B) | edge | [Ollama](https://github.com/ollama/ollama) 4 (2026-06-25) |

> CPU inference is **memory-bandwidth bound**. Use Q4 quant + a fast CPU build (AVX-512/AMX).

---

# 🟩 Metal — Apple Silicon (unified memory)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) ~237 (2026-09-26) |
| **Nemotron 3.5 Lightning 30B-A3B** | 30B-A3B | NVIDIA Open Model License | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16) | 32GB | [TensorFold](https://github.com/ashhart/TensorFold) 206 (2026-09-27) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [TensorFold](https://github.com/ashhart/TensorFold) 124 (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 41.5 (2026-09-27) |
| **Qwen3.8-Flash-Next** | 125B-A3B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 48GB | [TensorFold](https://github.com/ashhart/TensorFold) 92 (2026-09-27) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (2026-08-10) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 49.67 (2026-09-19) |

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
