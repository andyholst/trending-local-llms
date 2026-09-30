# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment. Every figure is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware and engine it was measured on. This README is **automatically regenerated** from `data/models.json` — see [AGENTS.md](AGENTS.md) and `skills/gather-data.md`.

**Ranked by 7-day X engagement** (likes/comments/views), retained through a 30-day window. Within a rank, models sort by **highest t/s** with the **one engine** that produced it. t/s is always shown **per engine**.

> Last generated: 2026-09-30 19:07 UTC. Source: lightbrd.com mirror (X posts).

---

## ❤️ Most loved open-weight models on X (ranked by 7-day engagement)

| Model | Full name | HF link | Why people love it | CUDA t/s (engine) | Metal t/s (engine) | VRAM |
|---|---|---|---|---|---|---|
| **Bonsai 2 27B** | Ternary-Bonsai-2-27B | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | PrismML 1.75-bit ternary compression of Qwen3.8-27B; ~98.2% capability in 5.9 GB. 11,792 downloads in 5 days. Runs big-VRAM-quality (262K ctx, MTP, vision on 16 GB) on old low-end cards. | 42.8 (98k ctx) ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 Ti 8GB, ternary + MTP head)<br>50 (MTP) ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 12GB, ternary + MTP head)<br>67 (MTP, 262k ctx) ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5060 Ti 16GB, ternary + MTP head)<br>67-71 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5060 Ti 16GB, MTP head)<br>60-91 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4070 12GB, PTQ1_0-mtp-lean (6.3 GB))<br>~50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 12GB, MTP + kernel fix)<br>143 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, ternary) | ~237.4 decode ([MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine), Apple Silicon 16GB Mac, mlx.fast speed-challenge run)<br>~237 decode ([MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine), Apple Silicon 16GB Mac, mlx.fast 4-bit)<br>~47 ([MLX](https://github.com/ml-explore/mlx), M5 Max, 2-bit MLX (5.9GB)) | 12GB |
| **DeepSeek-V4-Flash** | DeepSeek-V4-Flash | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | FreeToken runs this 284B MoE (13B active, 6-of-256 experts/token) on a 32GB GPU at 22 tok/s by splitting expert misses between GPU and CPU. Daily Dose of Data Science, Sep 27 2026. | 2.8-3.4 (Overspill, ~85GB setup) ([FreeToken](https://github.com/FlashML-org/FreeToken), RTX 3060 12GB + 64GB RAM, FP8)<br>22 ([FreeToken](https://github.com/FlashML-org/FreeToken), 32GB GPU, 4-bit) | — | 32GB |
| **Qwen3.8-27B** | Qwen3.8-27B-Instruct | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | Flagship local model. 384K views on release. 262K ctx (1M via YaRN). | ~133 chat; ~381 context-lookup (16-token verify) ([DFlash2](https://github.com/z-lab/dflash), RTX 3090 24GB ~250W, quantized KV/heads/acts)<br>35.5-43.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090 Laptop, Q4_K_M) | 120-189 ([TensorFold](https://github.com/ashhart/TensorFold), M5 Max, MLX 4-bit + DFlash2 drafter)<br>40.0 prose / 41.5 code ([TensorFold](https://github.com/ashhart/TensorFold), M3 Max 96GB, mlx-community 4-bit + z-lab DFlash2 8-bit)<br>120-124 ([TensorFold](https://github.com/ashhart/TensorFold), MacBook Pro M5 Max, 4-bit MLX) | 16GB |
| **Qwen3.6-35B-A3B** | Qwen3.6-35B-A3B | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | UC Berkeley open-source FreeToken serves this 35B MoE (~3B active) on an 8GB GPU at 39.3 tok/s by dynamically routing experts across GPU + system RAM. Daily Dose of Data Science, Sep 27 2026. | 39.3 ([FreeToken](https://github.com/FlashML-org/FreeToken), 8GB GPU, 4-bit) | — | 8GB |
| **Nemotron 3.5 Lightning** | NVIDIA-Nemotron-3.5-Lightning-30B-A3B | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16) | NVIDIA's fast active-parameter MoE (30B-A3B) hits 188-206 tok/s on Apple Silicon M5 Max via TensorFold MLX 4-bit — among the fastest open-weight LLMs measured on a Mac. | — | 188-206 ([TensorFold](https://github.com/ashhart/TensorFold), M5 Max, MLX 4-bit) | 32GB |
| **Qwen3.8-Flash-Next** | Qwen3.8-Flash-Next | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | Big MoE (125B-A3B) that TensorFold serves at 88-92 tok/s on M5 Max MLX 4-bit on Apple Silicon. | 37.7 decode / 1310 prefill (NVFP4) ([FreeToken](https://github.com/FlashML-org/FreeToken), RTX PRO 4000 Blackwell 24GB + 1TB RAM, NVFP4)<br>51.0 decode / 3637 prefill (NVFP4-RadixArk) ([FreeToken](https://github.com/FlashML-org/FreeToken), RTX 5090 + 128GB RAM, NVFP4) | 88-92 ([TensorFold](https://github.com/ashhart/TensorFold), M5 Max, MLX 4-bit) | 64GB |
| **RavenX-Conjecture-Qwen3-8B-MLX** | RavenX-Conjecture-Qwen3-8B-MLX | [link](https://huggingface.co/deadbydawn101/RavenX-Conjecture-Qwen3-8B-MLX) | RavenX-Conjecture Qwen3-8B tuned to run at 42 tok/s coherently on M3 MLX, a solid fast local routing/tool-call model before handing off to larger models. | — | 42 ([MLX](https://github.com/ml-explore/mlx), M3, MLX) | 8GB |
| **Llama 3.1 8B** | Meta-Llama-3.1-8B-Instruct | [link](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | In-browser edge inference: WebLLM runs Llama-3.1-8B at 41.1 tok/s (about 71% of native speed) with no server and no API key. | 41.1 ([WebLLM](https://github.com/mlc-ai/web-llm), in-browser WebGPU (M3 Max), WebAssembly for CPU-side) | — | 8GB |
| **Qwen2.5-7B-Instruct** | Qwen2.5-7B-Instruct | [link](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | Qwen2.5-7B-Instruct 4-bit AWQ served on vLLM on a free Kaggle T4 (16GB): ~38 tok/s single user, ~25 tok/s at 4 users, ~215 tok/s peak across 16 parallel requests. Omkar Chebale, Sep 28 2026. | ~38 ([vLLM](https://github.com/vllm-project/vllm), Kaggle T4 16GB (free), 4-bit AWQ) | — | 8GB |
| **GLM-5.2** | GLM-5.2 | [link](https://huggingface.co/zai-org/GLM-5.2) | FreeToken moves this 753B MoE runnable on a single 96GB datacenter GPU at 14.9 tok/s (cross GPU+RAM expert routing). Daily Dose of Data Science, Sep 27 2026. Measured figure from a real X post, datacenter-class GPU. | 14.9 ([FreeToken](https://github.com/FlashML-org/FreeToken), 96GB GPU) | — | 96GB |
| **Qwen3 8B** | Qwen3-8B | [link](https://huggingface.co/Qwen/Qwen3-8B) | The default 8 GB pick. Fast, Apache 2.0. | 100 ([Ollama](https://github.com/ollama/ollama), RTX 4060, Q4_K_M) | — | 8GB |
| **Gemma 4 12B** | gemma-4-12B-it | [link](https://huggingface.co/google/gemma-4-12B-it) | Best overall personal-agent model. Multimodal + audio, 256K ctx. | 99.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4090 Laptop, Q4) | 49.67 ([llama.cpp](https://github.com/ggml-org/llama.cpp), Apple Silicon, Q4) | 9GB |
| **Gemma 4 E2B** | Gemma-4-E2B | [link](https://huggingface.co/google/gemma-4-E2B) | Google's on-device LiteRT path: Gemma 4 E2B hits 99 tok/s prefill / 9 tok/s decode on a Raspberry Pi 5 for edge AI (Reachy Mini voice demo). | 99 prefill / 9 decode ([LiteRT](https://github.com/google-ai-edge/LiteRT), Raspberry Pi 5, CPU (1432 MB peak)) | — | 4GB |
| **Qwen3 14B** | Qwen3-14B | [link](https://huggingface.co/Qwen/Qwen3-14B) | 2M HF downloads. The community mid-size favorite. | 65 ([Ollama](https://github.com/ollama/ollama), RTX 3090, Q4_K_M) | — | 9GB |
| **Qwen 3.6 27B** | Qwen3.6-27B | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | Strongest local coding model (SWE-bench 77.2%). | 37 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3090, Q4_K_M) | — | 18GB |
| **Muse Glimmer 30B** | Muse-Glimmer-30B | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | Meta Superintelligence 30B agentic model, Apache 2.0. Fits 24/32 GB at 4-bit (<20GB weights + KV + vision + spec draft). DFlash drafter gives 3.1x decode on RTX 5090. | 233 (DFlash spec-decode), 74.9 stock ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, 4-bit) | 50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), M5 Max (Apple Silicon), 4-bit) | 24GB |
| **Qwen3 30B A3B** | Qwen3-30B-A3B | [link](https://huggingface.co/Qwen/Qwen3-30B-A3B) | Edge MoE streamed from flash: a 30B model runs on a 12 GB phone CPU at 5.2 tok/s via BigMoeOnEdge (stock llama.cpp). | 5.2 ([llama.cpp](https://github.com/ggml-org/llama.cpp), 12 GB phone, plain CPU (experts streamed from flash, no GPU/NPU)) | — | 12GB |
| **Gemma 4 26B** | Gemma-4-26B-A4B | [link](https://huggingface.co/google/gemma-4-26B-A4B) | Edge MoE: Gemma-4-26B-A4B runs on a 12 GB phone CPU at 4.1 tok/s via BigMoeOnEdge. | 4.1 ([llama.cpp](https://github.com/ggml-org/llama.cpp), 12 GB phone, plain CPU (experts streamed from flash, no GPU/NPU)) | — | 12GB |
| **DeepSeek R1 1.5B** | DeepSeek-R1-Distill-Qwen-1.5B | [link](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B) | Tiny offline edge stack: deepseek-r1 1.5B runs at 4 tok/s on a $35 Raspberry Pi 4B 2GB, fully offline at 5W. | 4 ([Ollama](https://github.com/ollama/ollama), Raspberry Pi 4B 2GB (CPU, ~5W)) | — | 4GB |
| **GPT-OSS 120B** | gpt-oss-120b | [link](https://huggingface.co/openai/gpt-oss-120b) | Edge MoE: gpt-oss-120b (60 GB) runs on a 12 GB phone CPU at 2.2 tok/s, ~14x faster than mmap (0.09 tok/s), byte-identical output. | 2.2 ([llama.cpp](https://github.com/ggml-org/llama.cpp), 12 GB phone, plain CPU, 4 cores (60 GB model streamed from flash)) | — | 12GB |

---

# 🟦 CUDA — NVIDIA GPUs (8–48 GB)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Qwen3.8-Flash-Next** | 125B-A3B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 64GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 37.7 decode / 1310 prefill (NVFP4) (2026-09-21); [FreeToken](https://github.com/FlashML-org/FreeToken) 51.0 decode / 3637 prefill (NVFP4-RadixArk) (2026-09-20) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [DFlash2](https://github.com/z-lab/dflash) ~133 chat; ~381 context-lookup (16-token verify) (2026-09-20); [llama.cpp](https://github.com/ggml-org/llama.cpp) 35.5-43.7 (2026-09-18) |
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 42.8 (98k ctx) (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (MTP) (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 67 (MTP, 262k ctx) (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 67-71 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 60-91 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) ~50 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-18) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 233 (DFlash spec-decode), 74.9 stock (2026-08-10) |
| **Qwen3 8B** | 8B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-8B) | 8GB | [Ollama](https://github.com/ollama/ollama) 100 (2026-09-12) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 99.7 (2026-09-19) |
| **DeepSeek-V4-Flash** | 284B (13B active, 6/256 experts) | MIT | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | 32GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 2.8-3.4 (Overspill, ~85GB setup) (2026-09-28); [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (2026-09-27) |
| **Qwen3 14B** | 14B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-14B) | 9GB | [Ollama](https://github.com/ollama/ollama) 65 (2026-09-15) |
| **Qwen3.6-35B-A3B** | 35B (3B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 8GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-27) |
| **Qwen2.5-7B-Instruct** | 7B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | 8GB | [vLLM](https://github.com/vllm-project/vllm) ~38 (2026-09-28) |
| **Qwen 3.6 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | 18GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 37 (2026-09-10) |
| **GLM-5.2** | 753B | Zhipu AI GLM license | [link](https://huggingface.co/zai-org/GLM-5.2) | 96GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 14.9 (2026-09-27) |

---

# 🟨 CPU — no GPU

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Gemma 4 E2B** | 2B | Apache 2.0 | [link](https://huggingface.co/google/gemma-4-E2B) | 4GB | [LiteRT](https://github.com/google-ai-edge/LiteRT) 99 prefill / 9 decode (2026-09-05) |
| **Llama 3.1 8B** | 8B | Llama 3.1 Community License | [link](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | 8GB | [WebLLM](https://github.com/mlc-ai/web-llm) 41.1 (2026-09-29) |
| **Qwen3 30B A3B** | 30B-A3B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-30B-A3B) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 5.2 (2026-08-13) |
| **Gemma 4 26B** | 26B-A4B | Apache 2.0 | [link](https://huggingface.co/google/gemma-4-26B-A4B) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 4.1 (2026-08-13) |
| **DeepSeek R1 1.5B** | 1.5B | MIT | [link](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B) | 4GB | [Ollama](https://github.com/ollama/ollama) 4 (2026-06-25) |
| **GPT-OSS 120B** | 120B-A4B | Apache 2.0 | [link](https://huggingface.co/openai/gpt-oss-120b) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 2.2 (2026-08-13) |

> CPU inference is **memory-bandwidth bound**. Use Q4 quant + a fast CPU build (AVX-512/AMX).

---

# 🟩 Metal — Apple Silicon (unified memory)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) ~237.4 decode (2026-09-27); [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) ~237 decode (2026-09-26); [MLX](https://github.com/ml-explore/mlx) ~47 (2026-09-26) |
| **Nemotron 3.5 Lightning** | 30B-A3B | NVIDIA Open Model | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16) | 32GB | [TensorFold](https://github.com/ashhart/TensorFold) 188-206 (2026-09-30) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [TensorFold](https://github.com/ashhart/TensorFold) 120-189 (2026-09-30); [TensorFold](https://github.com/ashhart/TensorFold) 40.0 prose / 41.5 code (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 120-124 (2026-09-20) |
| **Qwen3.8-Flash-Next** | 125B-A3B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 64GB | [TensorFold](https://github.com/ashhart/TensorFold) 88-92 (2026-09-27) |
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
