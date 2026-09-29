# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment. Every figure is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware and engine it was measured on. This README is **automatically regenerated** from `data/models.json` — see [AGENTS.md](AGENTS.md) and `skills/gather-data.md`.

**Ranked by 7-day X engagement** (likes/comments/views), retained through a 30-day window. Within a rank, models sort by **highest t/s** with the **one engine** that produced it. t/s is always shown **per engine**.

> Last generated: 2026-09-29 18:05 UTC. Source: lightbrd.com mirror (X posts).

---

## ❤️ Most loved open-weight models on X (ranked by 7-day engagement)

| # | Model | Full name | HF link | Why people love it | CUDA t/s (engine) | Metal t/s (engine) | VRAM | Engines + t/s |
|---|---|---|---|---|---|---|---|---|
| 1 | **Bonsai 2 27B** | Ternary-Bonsai-2-27B | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | PrismML 1.75-bit ternary compression of Qwen3.8-27B; ~98.2% capability in 5.9 GB. 11,792 downloads in 5 days. Runs big-VRAM-quality (262K ctx, MTP, vision on 16 GB) on old low-end cards. | ~50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 12GB, MTP + kernel fix)<br>67-71 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5060 Ti 16GB, MTP head)<br>143 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, ternary)<br>60-91 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4070 12GB, PTQ1_0-mtp-lean (6.3 GB))<br>~50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 12GB, MTP + kernel fix)<br>143 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, ternary) | ~237 decode ([MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine), Apple Silicon 16GB Mac, mlx.fast 4-bit) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~50 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 67-71 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 60-91 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) ~50 (2026-09-26); [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) ~237 decode (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-18) |
| 2 | **Qwen3.8-27B** | Qwen3.8-27B-Instruct | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | Flagship local model. 384K views on release. 262K ctx (1M via YaRN). | 44 (3.6x spec-decode; ~12 stock) ([DFlash2](https://github.com/z-lab/dflash), DGX Spark (abliterated Leimroth 3 build), DFlash2 draft head)<br>35.5-43.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090 Laptop, Q4_K_M) | 61.9 code / 30.8 chat (6.1x / 3.0x w/ DFlash2 draft) ([TensorFold](https://github.com/ashhart/TensorFold), Mac mini M6, MLX 4-bit + DFlash2 draft)<br>40.0 prose / 41.5 code ([TensorFold](https://github.com/ashhart/TensorFold), MacBook Pro M3 Max 96GB, mlx-community 4-bit + z-lab DFlash2 8-bit drafter)<br>120-124 ([TensorFold](https://github.com/ashhart/TensorFold), MacBook Pro M5 Max, 4-bit MLX) | 16GB | [DFlash2](https://github.com/z-lab/dflash) 44 (3.6x spec-decode; ~12 stock) (2026-09-29); [TensorFold](https://github.com/ashhart/TensorFold) 61.9 code / 30.8 chat (6.1x / 3.0x w/ DFlash2 draft) (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 40.0 prose / 41.5 code (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 120-124 (2026-09-20); [llama.cpp](https://github.com/ggml-org/llama.cpp) 35.5-43.7 (2026-09-18) |
| 3 | **Qwen3.6-35B-A3B** | Qwen3.6-35B-A3B | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | Top MoE model in the General group's highest-engagement post this week (Daily Dose of Data Science roundup of UC Berkeley's open-sourced FreeToken). 39.3 t/s on an 8GB GPU with experts offloaded to system RAM (activates ~3B of its 35B per token). Apache 2.0. | 39.3 ([FreeToken](https://github.com/FlashML-org/FreeToken), 8GB GPU, MoE offload (experts on RAM pass)) | — | 8GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-27) |
| 4 | **DeepSeek-V4-Flash** | DeepSeek-V4-Flash | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | 284B MoE (13B active, 6 experts of 256 per layer) served at 22 t/s on a 32GB GPU via FreeToken's bandwidth-split expert offload. Same UC Berkeley FreeToken roundup post. 1M-token context, FP4+FP8 mixed. | 2.8-3.4 ([FreeToken](https://github.com/FlashML-org/FreeToken), RTX 3060 12GB + 64GB RAM (Overspill), ~85GB setup + NVMe page-cache cold experts)<br>22 ([FreeToken](https://github.com/FlashML-org/FreeToken), 32GB GPU, FP4+FP8 / MoE offload (6 of 256 experts active))<br>22 ([FreeToken](https://github.com/FlashML-org/FreeToken), 32GB GPU, MoE + RAM expert offload) | — | 32GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 2.8-3.4 (2026-09-28); [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (2026-09-27); [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (2026-09-27) |
| 5 | **GLM-5.2** | GLM-5.2 | [link](https://huggingface.co/zai-org/GLM-5.2) | Z.ai flagship 753B MoE at 14.9 t/s on a 96GB GPU via FreeToken — the largest model in this week's General roundup (96GB is above the headline 8-48GB VRAM scope, kept as it's a real, high-engagement real-world figure). Directed at long-horizon tasks. (est VRAM) | 14.9 ([FreeToken](https://github.com/FlashML-org/FreeToken), 96GB GPU, MoE offload)<br>14.9 ([FreeToken](https://github.com/FlashML-org/FreeToken), 96GB GPU, MoE + RAM expert offload) | — | 96GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 14.9 (2026-09-27); [FreeToken](https://github.com/FlashML-org/FreeToken) 14.9 (2026-09-27) |
| 6 | **Swift 1.5 (Qwen3.8-27B)** | Swift-1.5-Qwen3.8-27b | [link](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b) | UkisAI reasoning-efficient Qwen3.8-27B derivative; ~15% decode bump over Swift 1.0, ~55 tok/s on a single RTX 3090, fewer wasted thinking tokens for agentic use. | ~55 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3090, BF16 / GGUF) | — | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~55 (2026-09-26) |
| 7 | **Qwen2.5-7B-Instruct** | Qwen2.5-7B-Instruct | [link](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | Qwen2.5-7B-Instruct (4-bit AWQ) on vLLM running free on a Kaggle T4: ~38 t/s single user, first token 0.8s, up to ~215 output t/s across 16 parallel requests (server-side, no network). Real measured numbers from a 'free GPU' serving writeup. | ~38 (1 user); peak ~215 output t/s across 16 parallel ([vLLM](https://github.com/vllm-project/vllm), Kaggle T4 16GB (free GPU), 4-bit AWQ) | — | 16GB | [vLLM](https://github.com/vllm-project/vllm) ~38 (1 user); peak ~215 output t/s across 16 parallel (2026-09-28) |
| 8 | **Qwen3-30B-A3B** | Qwen3-30B-A3B-Instruct | [link](https://huggingface.co/Qwen/Qwen3-30B-A3B) | MoE that streams cold experts from flash/storage on CPU-only devices; cold experts stay on flash and are re-read only when the router picks them, so a 30B-total Q2 model runs on a 12GB phone (llama.cpp, KleidiAI). | a few (est) ([llama.cpp](https://github.com/ggml-org/llama.cpp), Android phone 12GB RAM (arm64, KleidiAI CPU), UD-Q2_K_XL (11.8 GB))<br>5.2 ([llama.cpp](https://github.com/ggml-org/llama.cpp), 12GB phone, plain CPU (BigMoeOnEdge flash-streamed MoE), flash-streamed experts) | — | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) a few (est) (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 5.2 (2026-08-13) |
| 9 | **Gemma 3 4B** | Gemma-3-4B-it | [link](https://huggingface.co/google/gemma-3-4b-it) | Default model for offline local-knowledge apps; single GGUF file that fits a 6GB phone and runs fully on-device on CPU with no INTERNET permission (Vitanom, llama.cpp). | a few (est) ([llama.cpp](https://github.com/ggml-org/llama.cpp), Android phone 6GB RAM (arm64, KleidiAI CPU, mmap weights off flash), Q4_K_M (2.5 GB)) | — | 6GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) a few (est) (2026-09-29) |
| 10 | **Qwen2.5 0.5B** | Qwen2.5-0.5B | [link](https://huggingface.co/Qwen/Qwen2.5-0.5B) | Fast cheap-openweight semantic classifier/router on CPU (~74-76 tok/s); noticeably better than Needle at general semantic classification, with label-bias caveats. | ~74-76 ([llama.cpp](https://github.com/ggml-org/llama.cpp), CPU-only, (n/q)) | — | 4GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~74-76 (2026-09-28) |
| 11 | **Ling 3.0 Tiny** | Ling-3.0-tiny | [link](https://huggingface.co/inclusionAI/Ling-3.0-tiny) | Lightweight hybrid reasoning MoE; ~40 tok/s CPU-only while still doing real coding and structured reasoning - a useful CPU-side sweet spot when the GPU is busy with a larger model. | ~40 ([llama.cpp](https://github.com/ggml-org/llama.cpp), CPU-only, (n/q)) | — | 8GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~40 (2026-09-28) |
| 12 | **Qwen3.6-35B** | Qwen3.6-35B-A3B | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | UC Berkeley FreeToken serves this 35B MoE on an 8GB GPU at 39.3 tok/s by keeping hot experts in VRAM and streaming the rest from RAM. | 39.3 ([FreeToken](https://github.com/FlashML-org/FreeToken), 8GB GPU, MoE + RAM expert offload) | — | 8GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-27) |
| 13 | **Phi-3.5-mini** | Phi-3.5-mini-instruct | [link](https://huggingface.co/microsoft/Phi-3.5-mini-instruct) | Small model running in-browser via WebLLM at 71.1 t/s on an M3 Max (~80% of native). Quick edge-inference pick from the same WebLLM (MLC-LLM) roundup post. | — | 71.1 (WebLLM, Apple M3 Max (in-browser, WebGPU), browser WebGPU) | 8GB | WebLLM 71.1 (2026-09-29) |
| 14 | **Llama-3.1-8B-Instruct** | Llama-3.1-8B-Instruct | [link](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | 8B model running fully in-browser via WebLLM (MLC-LLM/TVM, WebGPU) at 41.1 t/s on an M3 Max — ~71% of native. No server, no API key. New engine worth tracking for edge/local inference. 19,200 GitHub stars. | — | 41.1 (WebLLM, Apple M3 Max (in-browser, WebGPU), q4f32_1 (browser WebGPU)) | 16GB | WebLLM 41.1 (2026-09-29) |
| 15 | **Nemotron Lightning 30B-A3B** | NVIDIA-Nemotron-3.5-Lightning-30B-A3B | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16) | NVIDIA's compact 30B-A3B Lightning MoE using its native MTP head; on TensorFold MLX 4-bit it is the fastest Metal measurement this window at 188-206 tok/s on Apple Silicon. | — | 188-206 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon, MLX 4-bit) | 24GB | [TensorFold](https://github.com/ashhart/TensorFold) 188-206 (2026-09-27) |
| 16 | **Qwen3.8-Flash-Next** | Qwen3.8-Flash-Next | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | Qwen's mid-tier multimodal MoE. On TensorFold MLX 4-bit it hits 88-92 tok/s on Apple Silicon, and ~80 tok/s decode at 64K context via oMLX MTP on M5 Ultra. | — | 88-92 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon, MLX 4-bit) | 48GB | [TensorFold](https://github.com/ashhart/TensorFold) 88-92 (2026-09-27) |
| 17 | **Qwen3 14B** | Qwen3-14B | [link](https://huggingface.co/Qwen/Qwen3-14B) | 2M HF downloads. The community mid-size favorite. | 65 ([Ollama](https://github.com/ollama/ollama), RTX 3090, Q4_K_M) | — | 9GB | [Ollama](https://github.com/ollama/ollama) 65 (2026-09-15) |
| 18 | **Gemma 4 12B** | gemma-4-12B-it | [link](https://huggingface.co/google/gemma-4-12B-it) | Best overall personal-agent model. Multimodal + audio, 256K ctx. | 99.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4090 Laptop, Q4) | 49.67 ([llama.cpp](https://github.com/ggml-org/llama.cpp), Apple Silicon, Q4) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 99.7 (2026-09-19); [llama.cpp](https://github.com/ggml-org/llama.cpp) 49.67 (2026-09-19) |
| 19 | **Qwen3 8B** | Qwen3-8B | [link](https://huggingface.co/Qwen/Qwen3-8B) | The default 8 GB pick. Fast, Apache 2.0. | 100 ([Ollama](https://github.com/ollama/ollama), RTX 4060, Q4_K_M) | — | 8GB | [Ollama](https://github.com/ollama/ollama) 100 (2026-09-12) |
| 20 | **Qwen 3.6 27B** | Qwen3.6-27B | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | Strongest local coding model (SWE-bench 77.2%). | 37 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3090, Q4_K_M) | — | 18GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 37 (2026-09-10) |
| 21 | **Muse Glimmer 30B** | Muse-Glimmer-30B | [link](https://huggingface.co/meta/Muse-Glimmer-30B) | Meta Superintelligence 30B agentic model, Apache 2.0. Fits 24/32 GB at 4-bit (<20GB weights + KV + vision + spec draft). DFlash drafter gives 3.1x decode on RTX 5090. | 233 (DFlash spec-decode), 74.9 stock ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, 4-bit) | 50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), M5 Max (Apple Silicon), 4-bit) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 233 (DFlash spec-decode), 74.9 stock (2026-08-10); [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (2026-08-10) |

---

# 🟦 CUDA — NVIDIA GPUs (8–48 GB)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 233 (DFlash spec-decode), 74.9 stock (2026-08-10) |
| **Qwen2.5-7B-Instruct** | 7B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | 16GB | [vLLM](https://github.com/vllm-project/vllm) ~38 (1 user); peak ~215 output t/s across 16 parallel (2026-09-28) |
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~50 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 67-71 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 60-91 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) ~50 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-18) |
| **Qwen3 8B** | 8B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-8B) | 8GB | [Ollama](https://github.com/ollama/ollama) 100 (2026-09-12) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 99.7 (2026-09-19) |
| **Qwen3 14B** | 14B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-14B) | 9GB | [Ollama](https://github.com/ollama/ollama) 65 (2026-09-15) |
| **Swift 1.5 (Qwen3.8-27B)** | 27B | Swift Open License v1.0 | [link](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~55 (2026-09-26) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [DFlash2](https://github.com/z-lab/dflash) 44 (3.6x spec-decode; ~12 stock) (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 35.5-43.7 (2026-09-18) |
| **Qwen3.6-35B-A3B** | 35B (3B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 8GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-27) |
| **Qwen3.6-35B** | 35B (3B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 8GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-27) |
| **Qwen 3.6 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | 18GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 37 (2026-09-10) |
| **DeepSeek-V4-Flash** | 284B (13B active) | MIT (DeepSeek) | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | 32GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 2.8-3.4 (2026-09-28); [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (2026-09-27); [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (2026-09-27) |
| **GLM-5.2** | 753B | GLM (Z.ai) | [link](https://huggingface.co/zai-org/GLM-5.2) | 96GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 14.9 (2026-09-27); [FreeToken](https://github.com/FlashML-org/FreeToken) 14.9 (2026-09-27) |

---

# 🟨 CPU — no GPU

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Qwen2.5 0.5B** | 0.5B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen2.5-0.5B) | 4GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~74-76 (2026-09-28) |
| **Ling 3.0 Tiny** | 7.9B (1.3B active) | Apache 2.0 | [link](https://huggingface.co/inclusionAI/Ling-3.0-tiny) | 8GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) ~40 (2026-09-28) |
| **Qwen3-30B-A3B** | 30B (3B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-30B-A3B) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) a few (est) (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 5.2 (2026-08-13) |
| **Gemma 3 4B** | 4B | Gemma | [link](https://huggingface.co/google/gemma-3-4b-it) | 6GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) a few (est) (2026-09-29) |

> CPU inference is **memory-bandwidth bound**. Use Q4 quant + a fast CPU build (AVX-512/AMX).

---

# 🟩 Metal — Apple Silicon (unified memory)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) ~237 decode (2026-09-26) |
| **Nemotron Lightning 30B-A3B** | 30B-A3B | Apache 2.0 | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16) | 24GB | [TensorFold](https://github.com/ashhart/TensorFold) 188-206 (2026-09-27) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [TensorFold](https://github.com/ashhart/TensorFold) 61.9 code / 30.8 chat (6.1x / 3.0x w/ DFlash2 draft) (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 40.0 prose / 41.5 code (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 120-124 (2026-09-20) |
| **Qwen3.8-Flash-Next** | ~177B-A18B (8.7B active via MLX mixed) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 48GB | [TensorFold](https://github.com/ashhart/TensorFold) 88-92 (2026-09-27) |
| **Phi-3.5-mini** | 3.8B | MIT (Microsoft) | [link](https://huggingface.co/microsoft/Phi-3.5-mini-instruct) | 8GB | WebLLM 71.1 (2026-09-29) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (2026-08-10) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 49.67 (2026-09-19) |
| **Llama-3.1-8B-Instruct** | 8B | Llama 3.1 (Meta) | [link](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | 16GB | WebLLM 41.1 (2026-09-29) |

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

**Quick picks:** Ollama (just works) · llama.cpp (gaming laptop, max speed) · FreeToken (big MoE on small GPU) · MLX + TensorFold + MLX-fast (Mac) · Strata (125B MoE on 12–24 GB) · vLLM + DFlash2 (spec decode) · llama.cpp CPU (tiny/edge).

---

## How to contribute

- Update `data/models.json` (add/refresh a model row with real X-sourced engagement and per-engine t/s), then run `python3 scripts/update_trending.py` to regenerate the README.
- Include: full model name, HF link, license, params, type, VRAM tier, a **measured** t/s + **engine + hardware + quant**, and the source X post.
- Prefer numbers from real X benchmark posts over vendor claims. Data is **community-reported on X** — directional, not lab-grade; mark projections `(est)`.
- All changes go through a **feature branch + PR**; automation never pushes to/merges `master` directly.

## License

Apache License 2.0. See [LICENSE](LICENSE).
