# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment. Every figure is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware and engine it was measured on. This README is **automatically regenerated** from `data/models.json` — see [AGENTS.md](AGENTS.md) and `skills/gather-data.md`.

**Ranked by 7-day X engagement** (likes/comments/views), retained through a 30-day window. Within a rank, models sort by **highest t/s** with the **one engine** that produced it. t/s is always shown **per engine**.

> Last generated: 2026-09-29 20:10 UTC. Source: lightbrd.com mirror (X posts).

---

## ❤️ Most loved open-weight models on X (ranked by 7-day engagement)

| # | Model | Full name | HF link | Why people love it | CUDA t/s (engine) | Metal t/s (engine) | VRAM | Engines + t/s |
|---|---|---|---|---|---|---|---|---|
| 1 | **Qwen3.8-27B** | Qwen3.8-27B-Instruct | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | Flagship local model. 384K views on release. 262K ctx (1M via YaRN). | 90 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4090, UD-Q4_K_XL)<br>63 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3090, Q4_K_M)<br>200 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, Q4)<br>34.8 / 38.7 ([Ollama](https://github.com/ollama/ollama), M3 Max 96GB, MLX 4-bit)<br>35.5-43.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090 Laptop, Q4_K_M) | 120-124 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon, MLX 4-bit)<br>61.9 code / 30.8 chat (6.1x / 3.0x) ([TensorFold](https://github.com/ashhart/TensorFold), Mac mini M6 32GB, MLX 4-bit + DFlash2 draft)<br>40.0 prose / 41.5 code ([TensorFold](https://github.com/ashhart/TensorFold), M3 Max 96GB, MLX 4-bit + DFlash2 8-bit)<br>120-124 ([TensorFold](https://github.com/ashhart/TensorFold), MacBook Pro M5 Max, 4-bit MLX) | 16GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 90 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 63 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 200 (2026-09-29); [TensorFold](https://github.com/ashhart/TensorFold) 120-124 (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 61.9 code / 30.8 chat (6.1x / 3.0x) (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 40.0 prose / 41.5 code (2026-09-27); [Ollama](https://github.com/ollama/ollama) 34.8 / 38.7 (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 120-124 (2026-09-20); [llama.cpp](https://github.com/ggml-org/llama.cpp) 35.5-43.7 (2026-09-18) |
| 2 | **Qwen3.8-Flash-Next** | Qwen3.8-Flash-Next | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 125B-A6B Flash MoE compressed to run on large-Mac unified memory; 88-92 tok/s on TensorFold MLX 4-bit. | 51.0 ([FreeToken](https://github.com/FlashML-org/FreeToken), RTX 5090 + 128GB RAM, NVFP4)<br>29.5 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX PRO 5000 + 3090 Ti, UD Q4 K XL) | 88-92 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon, MLX 4-bit) | 96GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 51.0 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 29.5 (2026-09-29); [TensorFold](https://github.com/ashhart/TensorFold) 88-92 (2026-09-27) |
| 3 | **Qwen3.6 35B** | Qwen3.6-35B-A3B | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 35B MoE (3B active/token) that FreeToken serves on an 8 GB GPU at 39.3 tok/s by routing experts between GPU cache and system RAM. | 39.3 ([FreeToken](https://github.com/FlashML-org/FreeToken), RTX 8GB GPU, 4-bit)<br>39.3 ([FreeToken](https://github.com/FlashML-org/FreeToken), 8 GB GPU (MoE, ~3B active/token), 4-bit) | — | 8GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-29); [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-27) |
| 4 | **DeepSeek-V4-Flash** | DeepSeek-V4-Flash | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | DeepSeek-V4 Flash (284B/13B active, 1M context) run locally on a 32 GB GPU at 22 tok/s via FreeToken's expert-routing. | 22 ([FreeToken](https://github.com/FlashML-org/FreeToken), RTX 32GB GPU, FP4/FP8)<br>22 ([FreeToken](https://github.com/FlashML-org/FreeToken), 32 GB GPU (MoE, 6 of 256 experts/token), FP8/FP4 mixed) | — | 32GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (2026-09-29); [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (2026-09-27) |
| 5 | **Needle 3** | Needle 3 (foundation tool-calling model for tiny devices) | [link](https://huggingface.co/Cactus-Compute/needle3) | On-device tool-calling/extraction/embedding; runs in ~78MB RAM; llama.cpp CPU i5-13600KF. | ~273-514 (1-4 threads) ([llama.cpp](https://github.com/ggml-org/llama.cpp), Intel i5-13600KF (CPU-only, 8 threads), Q4-style GGUF) | — | <1GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~273-514 (1-4 threads) (2026-09-27) |
| 6 | **Bonsai 2 27B** | Ternary-Bonsai-2-27B | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | PrismML 1.75-bit ternary compression of Qwen3.8-27B; ~98.2% capability in 5.9 GB. 11,792 downloads in 5 days. Runs big-VRAM-quality (262K ctx, MTP, vision on 16 GB) on old low-end cards. | 2 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 2080 8GB, PQ2_0)<br>67-71 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5060 Ti 16GB, MTP head)<br>60-91 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4070 12GB, PTQ1_0-mtp-lean (6.3 GB))<br>~50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 12GB, MTP + kernel fix)<br>143 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, ternary) | ~237 decode ([MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine), Apple Silicon 16GB Mac, mlx.fast 4-bit) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 2 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 67-71 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 60-91 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) ~50 (2026-09-26); [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) ~237 decode (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-18) |
| 7 | **Nemotron 3.5 Lightning 30B** | NVIDIA-Nemotron-3.5-Lightning-30B-A3B | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B) | 30B-A3B Lightning MoE at 188-206 tok/s on TensorFold MLX 4-bit. | — | 188-206 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon, MLX 4-bit) | 16GB | [TensorFold](https://github.com/ashhart/TensorFold) 188-206 (2026-09-27) |
| 8 | **Qwen3 8B** | Qwen3-8B | [link](https://huggingface.co/Qwen/Qwen3-8B) | The default 8 GB pick. Fast, Apache 2.0. | 100 ([Ollama](https://github.com/ollama/ollama), RTX 4060, Q4_K_M) | 42 ([MLX](https://github.com/ml-explore/mlx), M3, MLX) | 8GB | [MLX](https://github.com/ml-explore/mlx) 42 (2026-09-29); [Ollama](https://github.com/ollama/ollama) 100 (2026-09-12) |
| 9 | **Qwen2.5 0.5B** | Qwen2.5-0.5B | [link](https://huggingface.co/Qwen/Qwen2.5-0.5B) | Tiny general-purpose classifier/router; fast on CPU. | ~74-76 ([llama.cpp](https://github.com/ggml-org/llama.cpp), Intel i5-13600KF (CPU-only, 8 threads), Q4-style GGUF) | — | 1GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~74-76 (2026-09-27) |
| 10 | **Ornith 1.5 35B** | Ornith-1.5-35B-A3B | [link](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit) | 35B-A3B MoE hitting 50+ tok/s and ~2K tok/s prompt prefill on an M5 MacBook Pro (MLX 4-bit). | — | 50+ decode / ~2K prefill ([MLX](https://github.com/ml-explore/mlx), MacBook Pro M5 48GB, 4-bit) | 24GB | [MLX](https://github.com/ml-explore/mlx) 50+ decode / ~2K prefill (2026-09-29) |
| 11 | **Llama 3.1 8B** | Llama-3.1-8B-Instruct | [link](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | Runs fully in the browser (WebGPU/WebLLM) at 41.1 tok/s on an M3 Max — no server, no API key, ~71% of native speed. | 41.1 ([WebLLM](https://github.com/mlc-ai/web-llm), M3 Max (in-browser WebGPU, ~71% of native), MLC-compiled) | — | 8GB | [WebLLM](https://github.com/mlc-ai/web-llm) 41.1 (2026-09-29) |
| 12 | **Ling 3.0 Tiny** | Ling-3.0-tiny (7.9B total / 1.3B active MoE) | [link](https://huggingface.co/inclusionAI/Ling-3.0-tiny) | Capable CPU coding/reasoning worker via llama.cpp; 1.3B active params keep it fast on desktop CPU. | ~38-41 ([llama.cpp](https://github.com/ggml-org/llama.cpp), Intel i5-13600KF (CPU-only, 8 threads), Q4-style GGUF) | — | 4GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~38-41 (2026-09-27) |
| 13 | **Qwen3 14B** | Qwen3-14B | [link](https://huggingface.co/Qwen/Qwen3-14B) | 2M HF downloads. The community mid-size favorite. | 65 ([Ollama](https://github.com/ollama/ollama), RTX 3090, Q4_K_M) | — | 9GB | [Ollama](https://github.com/ollama/ollama) 65 (2026-09-15) |
| 14 | **Gemma 4 12B** | gemma-4-12B-it | [link](https://huggingface.co/google/gemma-4-12B-it) | Best overall personal-agent model. Multimodal + audio, 256K ctx. | 99.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4090 Laptop, Q4) | 49.67 ([llama.cpp](https://github.com/ggml-org/llama.cpp), Apple Silicon, Q4) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 99.7 (2026-09-19); [llama.cpp](https://github.com/ggml-org/llama.cpp) 49.67 (2026-09-19) |
| 15 | **Qwen 3.6 27B** | Qwen3.6-27B | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | Strongest local coding model (SWE-bench 77.2%). | 37 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3090, Q4_K_M) | — | 18GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 37 (2026-09-10) |
| 16 | **Muse Glimmer 30B** | Muse-Glimmer-30B | [link](https://huggingface.co/meta/Muse-Glimmer-30B) | Meta Superintelligence 30B agentic model, Apache 2.0. Fits 24/32 GB at 4-bit (<20GB weights + KV + vision + spec draft). DFlash drafter gives 3.1x decode on RTX 5090. | 233 (DFlash spec-decode), 74.9 stock ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, 4-bit) | 50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), M5 Max (Apple Silicon), 4-bit) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 233 (DFlash spec-decode), 74.9 stock (2026-08-10); [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (2026-08-10) |

---

# 🟦 CUDA — NVIDIA GPUs (8–48 GB)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 233 (DFlash spec-decode), 74.9 stock (2026-08-10) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 90 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 63 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 200 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 35.5-43.7 (2026-09-18) |
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 2 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 67-71 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 60-91 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) ~50 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-18) |
| **Qwen3 8B** | 8B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-8B) | 8GB | [Ollama](https://github.com/ollama/ollama) 100 (2026-09-12) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 99.7 (2026-09-19) |
| **Qwen3 14B** | 14B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-14B) | 9GB | [Ollama](https://github.com/ollama/ollama) 65 (2026-09-15) |
| **Qwen3.8-Flash-Next** | 125B-A6B MoE | Apache-2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 96GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 51.0 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 29.5 (2026-09-29) |
| **Qwen3.6 35B** | 35B (3B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 8GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-29); [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-27) |
| **Qwen 3.6 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | 18GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 37 (2026-09-10) |
| **DeepSeek-V4-Flash** | 284B (13B active) | DeepSeek (preview; license unverified) | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | 32GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (2026-09-29); [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (2026-09-27) |

---

# 🟨 CPU — no GPU

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Needle 3** | ~29-121M (8-29MB cact) | Apache 2.0 | [link](https://huggingface.co/Cactus-Compute/needle3) | <1GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~273-514 (1-4 threads) (2026-09-27) |
| **Qwen2.5 0.5B** | 0.5B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen2.5-0.5B) | 1GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~74-76 (2026-09-27) |
| **Ling 3.0 Tiny** | 7.9B (1.3B active) | MIT | [link](https://huggingface.co/inclusionAI/Ling-3.0-tiny) | 4GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~38-41 (2026-09-27) |

> CPU inference is **memory-bandwidth bound**. Use Q4 quant + a fast CPU build (AVX-512/AMX).

---

# 🟩 Metal — Apple Silicon (unified memory)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) ~237 decode (2026-09-26) |
| **Nemotron 3.5 Lightning 30B** | 30B-A3B | NVIDIA Open Model License | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B) | 16GB | [TensorFold](https://github.com/ashhart/TensorFold) 188-206 (2026-09-27) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [TensorFold](https://github.com/ashhart/TensorFold) 120-124 (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 61.9 code / 30.8 chat (6.1x / 3.0x) (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 40.0 prose / 41.5 code (2026-09-27); [Ollama](https://github.com/ollama/ollama) 34.8 / 38.7 (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 120-124 (2026-09-20) |
| **Qwen3.8-Flash-Next** | 125B-A6B MoE | Apache-2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 96GB | [TensorFold](https://github.com/ashhart/TensorFold) 88-92 (2026-09-27) |
| **Ornith 1.5 35B** | 35B-A3B | Apache-2.0 | [link](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit) | 24GB | [MLX](https://github.com/ml-explore/mlx) 50+ decode / ~2K prefill (2026-09-29) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (2026-08-10) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 49.67 (2026-09-19) |
| **Qwen3 8B** | 8B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-8B) | 8GB | [MLX](https://github.com/ml-explore/mlx) 42 (2026-09-29) |
| **Llama 3.1 8B** | 8B | Llama 3.1 (Meta Community License) | [link](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | 8GB | [WebLLM](https://github.com/mlc-ai/web-llm) 41.1 (2026-09-29) |

> On Apple Silicon, **MLX** is the fastest engine; **TensorFold** adds speculative decoding (3–6x on memory-bound Macs); **MLX-fast Bonsai 2** (Layr-Labs/mlxfast-bonsai2-27b-engine) pushes Ternary Bonsai 2 27B to ~237 tok/s on a 16 GB Mac.

---

## ⚙️ Inference engine / server guide

| Engine | Backend | Best for | Repo |
|---|---|---|---|
| **llama.cpp** | CUDA / CPU / Metal | Max control, custom quants | [repo](https://github.com/ggml-org/llama.cpp) |
| **Ollama** | CUDA / CPU / Metal | Easiest start | [repo](https://github.com/ollama/ollama) |
| **FreeToken** | CUDA | Big MoE on small GPUs | [repo](https://github.com/FlashML-org/FreeToken) |
| **vLLM** | CUDA | Production serving, high throughput | [repo](https://github.com/vllm-project/vllm) |
| **SGLang** | CUDA | High-throughput serving | [repo](https://github.com/sgl-project/sglang) |
| **MLX** | Metal | Fastest on Apple Silicon | [repo](https://github.com/ml-explore/mlx) |
| **TensorFold** | Metal | Speculative decoding on Mac, 3-6x | [repo](https://github.com/ashhart/TensorFold) |
| **TensorRT-LLM** | CUDA | Max NVIDIA perf | [repo](https://github.com/NVIDIA/TensorRT-LLM) |
| **LiteRT** | CUDA / Metal | Google local runtime | [repo](https://github.com/google-ai-edge/LiteRT) |
| **Strata** | CUDA | Runs big MoE (Qwen3.8-Flash-Next 125B) on 8-48 GB NVIDIA GPUs; experts across GPU/RAM/SSD, speculative decoding ~1.6-1.8x | [repo](https://github.com/Niko1221/Strata) |
| **MLX-fast (Bonsai 2)** | Metal | Speedup benchmark engine for Ternary Bonsai 2 27B on Apple Silicon; ~237 tok/s decode on 16 GB Mac (mlx.fast, Yukon/Layr-Labs) | [repo](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) |
| **DFlash2** | CUDA | Speculative decoding + context-lookup (Inco AI / syv-ai); Qwen3.8-27B ~118-133 tok/s chat, up to ~381 tok/s context-lookup on 24 GB RTX 3090 | [repo](https://github.com/z-lab/dflash) |
| **WebLLM** | CUDA / Metal | In-browser LLM inference accelerated with WebGPU (MLC-LLM). | [repo](https://github.com/mlc-ai/web-llm) |

**Quick picks:** Ollama (just works) · llama.cpp (gaming laptop, max speed) · FreeToken (big MoE on small GPU) · MLX + TensorFold + MLX-fast (Mac) · Strata (125B MoE on 12–24 GB) · vLLM + DFlash2 (spec decode) · llama.cpp CPU (tiny/edge).

---

## How to contribute

- Update `data/models.json` (add/refresh a model row with real X-sourced engagement and per-engine t/s), then run `python3 scripts/update_trending.py` to regenerate the README.
- Include: full model name, HF link, license, params, type, VRAM tier, a **measured** t/s + **engine + hardware + quant**, and the source X post.
- Prefer numbers from real X benchmark posts over vendor claims. Data is **community-reported on X** — directional, not lab-grade; mark projections `(est)`.
- All changes go through a **feature branch + PR**; automation never pushes to/merges `master` directly.

## License

Apache License 2.0. See [LICENSE](LICENSE).
