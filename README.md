# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment. Every figure is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware and engine it was measured on. This README is **automatically regenerated** from `data/models.json` — see [AGENTS.md](AGENTS.md) and `skills/gather-data.md`.

**Ranked by 7-day X engagement** (likes/comments/views), retained through a 30-day window. Within a rank, models sort by **highest t/s** with the **one engine** that produced it. t/s is always shown **per engine**.

> Last generated: 2026-09-30 01:21 UTC. Source: lightbrd.com mirror (X posts).

---

## ❤️ Most loved open-weight models on X (ranked by 7-day engagement)

| Model | Full name | HF link | Why people love it | CUDA t/s (engine) | Metal t/s (engine) | VRAM |
|---|---|---|---|---|---|---|
| **Qwen3.8-27B** | Qwen3.8-27B-Instruct | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | Flagship local model. 384K views on release. 262K ctx (1M via YaRN). | 35.5-43.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090 Laptop, Q4_K_M) | 120-124 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon, MLX 4-bit)<br>61.9 code / 30.8 chat (6.1x / 3.0x spec-decode) ([TensorFold](https://github.com/ashhart/TensorFold), Mac mini M6 32GB, MLX 4-bit + DFlash2 draft)<br>40.0 prose / 41.5 code ([TensorFold](https://github.com/ashhart/TensorFold), M3 Max 96GB, mlx-community 4-bit + z-lab DFlash2 8-bit)<br>46.8 prose / 56.1 code ([MLX](https://github.com/ml-explore/mlx), M4 Max, MTP head split (mlx-community)) | 16GB |
| **Bonsai 2 27B** | Ternary-Bonsai-2-27B | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | PrismML 1.75-bit ternary compression of Qwen3.8-27B; ~98.2% capability in 5.9 GB. 11,792 downloads in 5 days. Runs big-VRAM-quality (262K ctx, MTP, vision on 16 GB) on old low-end cards. | ~50 fresh, ~22 avg (MTP + kernel fix) ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 12GB, ternary 5.95GB)<br>67-71 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5060 Ti 16GB, MTP head)<br>143 ([llama.cpp](https://github.com/ggml-org/llama.cpp), GeForce RTX 5090, ternary 5.9GB)<br>60-91 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4070 12GB, PTQ1_0-mtp-lean (6.3 GB))<br>~50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 12GB, MTP + kernel fix) | ~237 decode ([MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine), Apple Silicon 16GB Mac, mlx.fast 4-bit) | 12GB |
| **Qwen3.8-Flash-Next** | Qwen3.8-Flash-Next (125B MoE) | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | Alibaba open-weight Qwen4-arch preview MoE (125B total, 6B active, +51B n-gram). Runs on 8GB+ GPUs via Strata engine; 52-60 tok/s output on RX 7900 XTX. | 52-60 output / 1250 prompt ([Strata](https://github.com/Niko1221/Strata), RX 7900 XTX 24GB, MoE offload) | 88-92 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon, MLX 4-bit) | 48GB |
| **Nemotron Lightning** | Nemotron Lightning | [link](https://huggingface.co/nvidia/Nemotron-Lightning) | TensorFold MLX 4-bit hits 188-206 tok/s on Apple Silicon. | — | 188-206 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon, MLX 4-bit) | 16GB |
| **Ornith 1.5** | Ornith 1.5 | [link](https://huggingface.co/aosama/ornith-1.5-mlx) | 50+ TPS and ~2K t/s prompt processing on MacBook Pro M5 48GB (Astronomical CLI). | — | 50+ (2K t/s prefill) ([MLX](https://github.com/ml-explore/mlx), MacBook Pro M5 48GB, MLX 4-bit) | 48GB |
| **RavenX-Conjecture-Qwen3-8B-MLX** | RavenX-Conjecture-Qwen3-8B-MLX | [link](https://huggingface.co/RavenX/RavenX-Conjecture-Qwen3-8B-MLX) | 42 tok/s on M3, coherent on multi-step tool calls; fast local routing model. | — | 42 ([MLX](https://github.com/ml-explore/mlx), M3, MLX) | 8GB |
| **Llama 3.1 8B** | Llama-3.1-8B | [link](https://huggingface.co/meta-llama/Llama-3.1-8B) | Llama-3.1-8B runs at 41.1 tok/s in-browser via WebLLM on an M3 Max (~71% of native speed). | — | 41.1 ([WebLLM](https://github.com/mlc-ai/web-llm), M3 Max (Apple Silicon), WebGPU) | 8GB |
| **Qwen3.6 35B** | Qwen3.6-35B-A3B | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | UC Berkeley FreeToken runs Qwen3.6-35B MoE on an 8GB GPU at 39.3 tok/s (2-4x faster than Ollama). | 39.3 ([FreeToken](https://github.com/FlashML-org/FreeToken), 8GB GPU, MoE offload)<br>39.3 (paper, W2 coding-agent decode) ([FreeToken](https://github.com/FlashML-org/FreeToken), RTX 4060 Laptop 8GB, NVFP4) | — | 8GB |
| **Qwen2.5 7B** | Qwen2.5-7B-Instruct | [link](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | Served a 7B LLM on a free Kaggle T4 GPU with vLLM; ~38 tok/s single user, ~215 tok/s peak across 16 parallel requests. | ~38 ([vLLM](https://github.com/vllm-project/vllm), Kaggle T4 16GB, 4-bit AWQ) | — | 8GB |
| **DeepSeek-V4-Flash** | DeepSeek-V4-Flash (284B MoE) | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | DeepSeek-V4-Flash 284B MoE (13B active) runs on a 32GB GPU at 22 tok/s via FreeToken. | 22 ([FreeToken](https://github.com/FlashML-org/FreeToken), 32GB GPU, FP4/FP8 mixed)<br>22 (single GPU, 6-of-256 experts/layer) ([FreeToken](https://github.com/FlashML-org/FreeToken), RTX 5090 32GB, FP4+FP8 mixed) | — | 32GB |
| **Gemma 3 4B** | Gemma 3 4B Instruct | [link](https://huggingface.co/google/gemma-3-4b-it) | Default offline model in Vitanom, a llama.cpp-based Android app that runs fully offline (no INTERNET permission, mmap weights from flash). | a few tokens/s (est) ([llama.cpp](https://github.com/ggml-org/llama.cpp), Android phone CPU (arm64, KleidiAI), 6GB RAM, Q4_K_M) | — | 6GB |
| **Qwen3-30B-A3B** | Qwen3-30B-A3B Instruct | [link](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct) | MoE model (128 experts/layer, 8 active) that streams cold experts from flash on a phone CPU in the Vitanom offline app. | a few tokens/s (est) ([llama.cpp](https://github.com/ggml-org/llama.cpp), Android phone CPU (arm64, KleidiAI), 12GB RAM, UD-Q2_K_XL) | — | 12GB |
| **Qwen3 8B** | Qwen3-8B | [link](https://huggingface.co/Qwen/Qwen3-8B) | The default 8 GB pick. Fast, Apache 2.0. | 100 ([Ollama](https://github.com/ollama/ollama), RTX 4060, Q4_K_M) | — | 8GB |
| **Gemma 4 12B** | gemma-4-12B-it | [link](https://huggingface.co/google/gemma-4-12B-it) | Best overall personal-agent model. Multimodal + audio, 256K ctx. | 99.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4090 Laptop, Q4) | 49.67 ([llama.cpp](https://github.com/ggml-org/llama.cpp), Apple Silicon, Q4) | 9GB |
| **Gemma 4 E2B** | Gemma 4 E2B | [link](https://huggingface.co/google/gemma-4-e2b) | Google's on-device Gemma for tight RAM and speech; runs on a Pi 5 via LiteRT with ~9 tok/s decode. | 99 prefill / 9 decode ([LiteRT](https://github.com/google-ai-edge/LiteRT), Raspberry Pi 5 CPU (1432 MB peak), int8 (est)) | — | 4GB |
| **Qwen3 14B** | Qwen3-14B | [link](https://huggingface.co/Qwen/Qwen3-14B) | 2M HF downloads. The community mid-size favorite. | 65 ([Ollama](https://github.com/ollama/ollama), RTX 3090, Q4_K_M) | — | 9GB |
| **Qwen 3.6 27B** | Qwen3.6-27B | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | Strongest local coding model (SWE-bench 77.2%). | 37 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3090, Q4_K_M) | — | 18GB |
| **Muse Glimmer 30B** | Muse-Glimmer-30B | [link](https://huggingface.co/meta/Muse-Glimmer-30B) | Meta Superintelligence 30B agentic model, Apache 2.0. Fits 24/32 GB at 4-bit (<20GB weights + KV + vision + spec draft). DFlash drafter gives 3.1x decode on RTX 5090. | 233 (DFlash spec-decode), 74.9 stock ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, 4-bit) | 50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), M5 Max (Apple Silicon), 4-bit) | 24GB |

---

# 🟦 CUDA — NVIDIA GPUs (8–48 GB)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Qwen3.8-Flash-Next** | 125B (6B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 48GB | [Strata](https://github.com/Niko1221/Strata) 52-60 output / 1250 prompt (2026-09-29) |
| **DeepSeek-V4-Flash** | 284B (13B active) | DeepSeek | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | 32GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (2026-09-27); [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (single GPU, 6-of-256 experts/layer) (2026-09-27) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 233 (DFlash spec-decode), 74.9 stock (2026-08-10) |
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~50 fresh, ~22 avg (MTP + kernel fix) (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 67-71 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 60-91 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) ~50 (2026-09-26) |
| **Qwen3 8B** | 8B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-8B) | 8GB | [Ollama](https://github.com/ollama/ollama) 100 (2026-09-12) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 99.7 (2026-09-19) |
| **Qwen3 14B** | 14B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-14B) | 9GB | [Ollama](https://github.com/ollama/ollama) 65 (2026-09-15) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 35.5-43.7 (2026-09-18) |
| **Qwen3.6 35B** | 35B (3B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 8GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-27); [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (paper, W2 coding-agent decode) (2026-09-27) |
| **Qwen2.5 7B** | 7B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | 8GB | [vLLM](https://github.com/vllm-project/vllm) ~38 (2026-09-28) |
| **Qwen 3.6 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | 18GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 37 (2026-09-10) |

---

# 🟨 CPU — no GPU

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Gemma 4 E2B** | 2B | Gemma Terms of Use | [link](https://huggingface.co/google/gemma-4-e2b) | 4GB | [LiteRT](https://github.com/google-ai-edge/LiteRT) 99 prefill / 9 decode (2026-09-05) |
| **Gemma 3 4B** | 4B | Gemma Terms of Use | [link](https://huggingface.co/google/gemma-3-4b-it) | 6GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) a few tokens/s (est) (2026-09-29) |
| **Qwen3-30B-A3B** | 30B (3B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) a few tokens/s (est) (2026-09-29) |

> CPU inference is **memory-bandwidth bound**. Use Q4 quant + a fast CPU build (AVX-512/AMX).

---

# 🟩 Metal — Apple Silicon (unified memory)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) ~237 decode (2026-09-26) |
| **Nemotron Lightning** | unknown | NVIDIA Open Model License | [link](https://huggingface.co/nvidia/Nemotron-Lightning) | 16GB | [TensorFold](https://github.com/ashhart/TensorFold) 188-206 (2026-09-27) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [TensorFold](https://github.com/ashhart/TensorFold) 120-124 (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 61.9 code / 30.8 chat (6.1x / 3.0x spec-decode) (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 40.0 prose / 41.5 code (2026-09-27); [MLX](https://github.com/ml-explore/mlx) 46.8 prose / 56.1 code (2026-09-26) |
| **Qwen3.8-Flash-Next** | 125B (6B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 48GB | [TensorFold](https://github.com/ashhart/TensorFold) 88-92 (2026-09-27) |
| **Ornith 1.5** | unknown | Apache 2.0 | [link](https://huggingface.co/aosama/ornith-1.5-mlx) | 48GB | [MLX](https://github.com/ml-explore/mlx) 50+ (2K t/s prefill) (2026-09-29) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (2026-08-10) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 49.67 (2026-09-19) |
| **RavenX-Conjecture-Qwen3-8B-MLX** | 8B | Apache 2.0 | [link](https://huggingface.co/RavenX/RavenX-Conjecture-Qwen3-8B-MLX) | 8GB | [MLX](https://github.com/ml-explore/mlx) 42 (2026-09-29) |
| **Llama 3.1 8B** | 8B | Llama 3.1 Community | [link](https://huggingface.co/meta-llama/Llama-3.1-8B) | 8GB | [WebLLM](https://github.com/mlc-ai/web-llm) 41.1 (2026-09-29) |

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
