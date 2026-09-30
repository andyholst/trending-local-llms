# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment. Every figure is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware and engine it was measured on. This README is **automatically regenerated** from `data/models.json` — see [AGENTS.md](AGENTS.md) and `skills/gather-data.md`.

**Ranked by 7-day X engagement** (likes/comments/views), retained through a 30-day window. Within a rank, models sort by **highest t/s** with the **one engine** that produced it. t/s is always shown **per engine**.

> Last generated: 2026-09-30 20:26 UTC. Source: lightbrd.com mirror (X posts).

---

## ❤️ Most loved open-weight models on X (ranked by 7-day engagement)

| Model | Full name | HF link | Why people love it | CUDA t/s (engine) | Metal t/s (engine) | VRAM |
|---|---|---|---|---|---|---|
| **Qwen3.6-35B** | Qwen3.6-35B-A3B | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | UC Berkeley open-sourced FreeToken (2-4x faster local inference than Ollama) serving big MoEs on small GPUs; Qwen3.6-35B at 39.3 t/s on an 8GB GPU. | 39.3 ([FreeToken](https://github.com/FlashML-org/FreeToken), 8GB GPU)<br>39.3 (est) ([FreeToken](https://github.com/FlashML-org/FreeToken), 8GB GPU, MoE expert streaming) | — | 8GB |
| **DeepSeek-V4-Flash** | DeepSeek-V4-Flash 284B | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | FreeToken serves DeepSeek-V4-Flash 284B MoE (picks 6 of 256 experts per layer, ~13B active) at 22 t/s on a 32GB GPU. | 22 ([FreeToken](https://github.com/FlashML-org/FreeToken), 32GB GPU)<br>22 (est) ([FreeToken](https://github.com/FlashML-org/FreeToken), 32GB GPU, MoE expert streaming) | — | 32GB |
| **Qwen3.8-27B** | Qwen3.8-27B-Instruct | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | Flagship local model. 384K views on release. 262K ctx (1M via YaRN). | 44 (spec-decode 3.6x; 12 stock) ([DFlash2](https://github.com/z-lab/dflash), DGX Spark, DFlash2 draft head)<br>35.5-43.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090 Laptop, Q4_K_M) | 120-124 ([TensorFold](https://github.com/ashhart/TensorFold), MacBook Pro M5 Max, 4-bit MLX) | 16GB |
| **Qwen3.8-Flash-Next** | Qwen3.8-Flash-Next (125B MoE) | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | Qwen4-arch open-weight MoE (125B/6B active) benchmarked running locally at sustained 52-60 output t/s on an 8GB+ AMD GPU via the Strata engine; 1250 prompt-token/s. | 52-60 output / 1250 prompt ([Strata](https://github.com/Niko1221/Strata), RX 7900 XTX (AMD, 8GB+)) | — | 8GB+ |
| **WebLLM (Llama-3.1-8B)** | web-llm (MLC-AI) — in-browser | [link](https://huggingface.co/mlc-ai/Llama-3.1-8B-Instruct-q4f16_1-MLC) | WebLLM runs Llama-3.1-8B at 41.1 tok/s inside a browser tab (WebGPU), ~71% of native speed — the GPU in the user's own laptop does the inference, no server. | — | 41.1 ([WebLLM](https://github.com/mlc-ai/web-llm), Apple M3 Max (WebGPU, in-browser), q4) | edge/browser (device GPU) |
| **Qwen2.5-7B-Instruct** | Qwen2.5-7B-Instruct | [link](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | Served a 7B chat model on a free Kaggle T4 via vLLM with a coding agent; ~38 output t/s single-user, ~25 t/s at 4 users, ~215 t/s peak across 16 parallel requests. | ~38 (1 user); ~215 peak (16 parallel) ([vLLM](https://github.com/vllm-project/vllm), Kaggle T4 (16GB) free GPU, 4-bit AWQ) | — | 8GB |
| **GLM-5.2** | GLM-5.2 753B | [link](https://huggingface.co/zai-org/GLM-5.2) | FreeToken runs GLM-5.2 753B MoE at 14.9 t/s on a 96GB GPU — frontier open MoE made runnable on single-GPU hardware. | 14.9 ([FreeToken](https://github.com/FlashML-org/FreeToken), 96GB GPU) | — | 96GB |
| **Gemma 3 4B** | gemma-3-4b-it | [link](https://huggingface.co/google/gemma-3-4b-it) | Vitanom: single Android process around llama.cpp, off-grid local knowledge app. Gemma 3 4B Q4_K_M (~2.5 GB) fits a 6 GB phone, no GPU backend, no INTERNET permission. | a few (est) ([llama.cpp](https://github.com/ggml-org/llama.cpp), Android phone CPU (arm64 KleidiAI), Q4_K_M) | — | phone (2.5GB) |
| **Qwen3-30B-A3B** | Qwen3-30B-A3B-Instruct | [link](https://huggingface.co/Qwen/Qwen3-30B-A3B) | Vitanom loads Qwen3-30B-A3B (11.8 GB) on a 12 GB phone: MoE leaves cold experts on flash, re-reads only active ones per token on CPU — a few tok/s but no server. | a few (est) ([llama.cpp](https://github.com/ggml-org/llama.cpp), 12GB Android phone CPU, MoE streamed from flash, UD-Q2_K_XL) | — | 12GB phone RAM |
| **Bonsai 2 27B** | Ternary-Bonsai-2-27B | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | PrismML 1.75-bit ternary compression of Qwen3.8-27B; ~98.2% capability in 5.9 GB. 11,792 downloads in 5 days. Runs big-VRAM-quality (262K ctx, MTP, vision on 16 GB) on old low-end cards. | 67-71 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5060 Ti 16GB, MTP head)<br>60-91 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4070 12GB, PTQ1_0-mtp-lean (6.3 GB))<br>~50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 12GB, MTP + kernel fix)<br>143 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, ternary) | ~237 decode ([MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine), Apple Silicon 16GB Mac, mlx.fast 4-bit) | 12GB |
| **Qwen3 8B** | Qwen3-8B | [link](https://huggingface.co/Qwen/Qwen3-8B) | The default 8 GB pick. Fast, Apache 2.0. | 100 ([Ollama](https://github.com/ollama/ollama), RTX 4060, Q4_K_M) | — | 8GB |
| **Gemma 4 12B** | gemma-4-12B-it | [link](https://huggingface.co/google/gemma-4-12B-it) | Best overall personal-agent model. Multimodal + audio, 256K ctx. | 99.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4090 Laptop, Q4) | 49.67 ([llama.cpp](https://github.com/ggml-org/llama.cpp), Apple Silicon, Q4) | 9GB |
| **Qwen3 14B** | Qwen3-14B | [link](https://huggingface.co/Qwen/Qwen3-14B) | 2M HF downloads. The community mid-size favorite. | 65 ([Ollama](https://github.com/ollama/ollama), RTX 3090, Q4_K_M) | — | 9GB |
| **Qwen 3.6 27B** | Qwen3.6-27B | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | Strongest local coding model (SWE-bench 77.2%). | 37 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3090, Q4_K_M) | — | 18GB |
| **Muse Glimmer 30B** | Muse-Glimmer-30B | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | Meta Superintelligence 30B agentic model, Apache 2.0. Fits 24/32 GB at 4-bit (<20GB weights + KV + vision + spec draft). DFlash drafter gives 3.1x decode on RTX 5090. | 233 (DFlash spec-decode), 74.9 stock ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, 4-bit) | 50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), M5 Max (Apple Silicon), 4-bit) | 24GB |

---

# 🟦 CUDA — NVIDIA GPUs (8–48 GB)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Qwen3.8-Flash-Next** | 125B (6B active) MoE | Apache-2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 8GB+ | [Strata](https://github.com/Niko1221/Strata) 52-60 output / 1250 prompt (2026-09-29) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 233 (DFlash spec-decode), 74.9 stock (2026-08-10) |
| **Qwen2.5-7B-Instruct** | 7B | Apache-2.0 | [link](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | 8GB | [vLLM](https://github.com/vllm-project/vllm) ~38 (1 user); ~215 peak (16 parallel) (2026-09-28) |
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 67-71 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 60-91 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) ~50 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-18) |
| **Qwen3 8B** | 8B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-8B) | 8GB | [Ollama](https://github.com/ollama/ollama) 100 (2026-09-12) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 99.7 (2026-09-19) |
| **Qwen3 14B** | 14B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-14B) | 9GB | [Ollama](https://github.com/ollama/ollama) 65 (2026-09-15) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [DFlash2](https://github.com/z-lab/dflash) 44 (spec-decode 3.6x; 12 stock) (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 35.5-43.7 (2026-09-18) |
| **Qwen3.6-35B** | 35B (3B active) MoE | Apache-2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 8GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-27); [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (est) (2026-09-27) |
| **Qwen 3.6 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | 18GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 37 (2026-09-10) |
| **DeepSeek-V4-Flash** | 284B (13B active) MoE | MIT | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | 32GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (2026-09-27); [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (est) (2026-09-27) |
| **GLM-5.2** | 753B MoE | MIT | [link](https://huggingface.co/zai-org/GLM-5.2) | 96GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 14.9 (2026-09-27) |

---

# 🟨 CPU — no GPU

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Gemma 3 4B** | 4B | Gemma | [link](https://huggingface.co/google/gemma-3-4b-it) | phone (2.5GB) | [llama.cpp](https://github.com/ggml-org/llama.cpp) a few (est) (2026-09-29) |
| **Qwen3-30B-A3B** | 30B (3B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-30B-A3B) | 12GB phone RAM | [llama.cpp](https://github.com/ggml-org/llama.cpp) a few (est) (2026-09-29) |

> CPU inference is **memory-bandwidth bound**. Use Q4 quant + a fast CPU build (AVX-512/AMX).

---

# 🟩 Metal — Apple Silicon (unified memory)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) ~237 decode (2026-09-26) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [TensorFold](https://github.com/ashhart/TensorFold) 120-124 (2026-09-20) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (2026-08-10) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 49.67 (2026-09-19) |
| **WebLLM (Llama-3.1-8B)** | 8B | Apache 2.0 | [link](https://huggingface.co/mlc-ai/Llama-3.1-8B-Instruct-q4f16_1-MLC) | edge/browser (device GPU) | [WebLLM](https://github.com/mlc-ai/web-llm) 41.1 (2026-09-29) |

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
