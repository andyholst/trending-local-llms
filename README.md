# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment. Every figure is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware and engine it was measured on. This README is **automatically regenerated** from `data/models.json` — see [AGENTS.md](AGENTS.md) and `skills/gather-data.md`.

**Ranked by 7-day X engagement** (likes/comments/views), retained through a 30-day window. Within a rank, models sort by **highest t/s** with the **one engine** that produced it. t/s is always shown **per engine**.

> Last generated: 2026-09-30 23:54 UTC. Source: lightbrd.com mirror (X posts).

---

## ❤️ Most loved open-weight models on X (ranked by 7-day engagement)

| Model | Full name | HF link | Why people love it | CUDA t/s (engine) | Metal t/s (engine) | VRAM |
|---|---|---|---|---|---|---|
| **Qwen3.8-27B** | Qwen3.8-27B-Instruct | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | Flagship local model. 384K views on release. 262K ctx (1M via YaRN). | 381 ([DFlash2](https://github.com/z-lab/dflash), RTX 3090 24GB, DFlash2 + lookup drafting + prefix caching)<br>43.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090 Laptop, Q4_K_M) | 189 ([TensorFold](https://github.com/ashhart/TensorFold), M5 Max, MLX 4-bit)<br>124 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon (MLX 4-bit), MLX 4-bit)<br>61.9 ([TensorFold](https://github.com/ashhart/TensorFold), Mac mini M6, MLX 4-bit)<br>41.5 ([MLX](https://github.com/ml-explore/mlx), M3 Max 96GB, mlx-community 4-bit + z-lab DFlash2 8-bit drafter) | 16GB |
| **Qwen3.8-Flash-Next** | Qwen3.8-Flash-Next | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | Open-weight 125B MoE (6B active) preview of the Qwen4 architecture: runs on 8GB+ AMD via Strata offload at 52-60 out tok/s (vLLM identity). | 1250 ([Strata](https://github.com/Niko1221/Strata), AMD RX 7900 XTX (8GB+), MoE experts offload)<br>65.1 ([Strata](https://github.com/Niko1221/Strata), RTX 5070 12GB + 64GB DDR5, RCO-GSQ quants (Q2_0/IQ2_XS/IQ3_XXS)) | 92 ([TensorFold](https://github.com/ashhart/TensorFold), Apple Silicon (MLX 4-bit), MLX 4-bit) | 24GB |
| **DeepSeek-V4-Flash** | DeepSeek-V4-Flash | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | 284B MoE (13B active per token) runs on a single 32GB GPU at 22 tok/s via FreeToken expert offload. | 85 ([FreeToken](https://github.com/FlashML-org/FreeToken), RTX 3060 12GB + 64GB RAM, MXFP4 (est))<br>22 ([FreeToken](https://github.com/FlashML-org/FreeToken), 32GB GPU, NVFP4 (est)) | — | 32GB |
| **Nemotron 3.5 Lightning** | NVIDIA-Nemotron-3.5-Lightning-30B-A3B | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4) | Fast spec-decoded MoE on Apple Silicon via TensorFold; 188-206 tok/s on M5 Max in MLX 4-bit. | — | 206 ([TensorFold](https://github.com/ashhart/TensorFold), M5 Max, MLX 4-bit) | 48GB |
| **Qwen3.6-35B-A3B** | Qwen3.6-35B-A3B | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 35B MoE (3B active) served on an 8GB GPU at 39.3 tok/s by FreeToken's dual GPU/CPU expert-offload + checkpointed agent-prefill. | 39.3 ([FreeToken](https://github.com/FlashML-org/FreeToken), 8GB GPU, MXFP4/NVFP4) | — | 8GB |
| **Bonsai 2 27B** | Ternary-Bonsai-2-27B | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | PrismML 1.75-bit ternary compression of Qwen3.8-27B; ~98.2% capability in 5.9 GB. 11,792 downloads in 5 days. Runs big-VRAM-quality (262K ctx, MTP, vision on 16 GB) on old low-end cards. | 42.8 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 Ti 8GB, ternary + Qwen3.8 MTP head)<br>71 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5060 Ti 16GB, MTP head)<br>91 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4070 12GB, PTQ1_0-mtp-lean (6.3 GB))<br>50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3060 12GB, MTP + kernel fix)<br>143 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, ternary) | 237 ([MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine), Apple Silicon 16GB Mac, mlx.fast 4-bit) | 12GB |
| **Ornith 1.5 35B-A3B** | Ornith-1.5-35B-A3B | [link](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B-MLX) | 4.6x faster decode than dense Qwen3.8-27B on the same Mac; runs 50+ tok/s on M5 Pro in MLX 4-bit. | — | 50 ([MLX](https://github.com/ml-explore/mlx), MacBook Pro M5 48GB, MLX 4-bit) | 24GB |
| **RavenX-Conjecture-Qwen3-8B** | RavenX-Conjecture-Qwen3-8B-MLX | [link](https://huggingface.co/deadbydawn101/RavenX-Conjecture-Qwen3-8B-MLX) | Fast local router for multi-step tool calls; 42 tok/s on M3, staying coherent. | — | 42 ([MLX](https://github.com/ml-explore/mlx), Apple Silicon M3, MLX) | 8GB |
| **Llama 3.1 8B** | Llama-3.1-8B | [link](https://huggingface.co/meta-llama/Llama-3.1-8B) | 8B model runs at 41.1 tok/s in-browser via WebLLM (WebGPU, ~71% of native Mac speed) with WebAssembly CPU fallback. | — | 41.1 ([WebLLM](https://github.com/mlc-ai/web-llm), Apple M3 Max (in-browser WebGPU), compiled MLC) | 8GB |
| **Qwen3 8B** | Qwen3-8B | [link](https://huggingface.co/Qwen/Qwen3-8B) | The default 8 GB pick. Fast, Apache 2.0. | 100 ([Ollama](https://github.com/ollama/ollama), RTX 4060, Q4_K_M) | — | 8GB |
| **Gemma 4 12B** | gemma-4-12B-it | [link](https://huggingface.co/google/gemma-4-12B-it) | Best overall personal-agent model. Multimodal + audio, 256K ctx. | 99.7 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 4090 Laptop, Q4) | 49.67 ([llama.cpp](https://github.com/ggml-org/llama.cpp), Apple Silicon, Q4) | 9GB |
| **Gemma 4 E2B** | Google Gemma 4 E2B | [link](https://huggingface.co/google/gemma-4-E2B) | Google's official edge path: LiteRT + Gemma 4 E2B on a Raspberry Pi 5 — 99 t/s prefill and 9 t/s decode at only 1432 MB peak, fully on-device (voice demo ~300 words/min). | 99 ([LiteRT](https://github.com/google-ai-edge/LiteRT), Raspberry Pi 5 CPU (VideoCore VII GPU split for vision/audio), on-device (1432 MB peak)) | — | 2GB |
| **Qwen3 14B** | Qwen3-14B | [link](https://huggingface.co/Qwen/Qwen3-14B) | 2M HF downloads. The community mid-size favorite. | 65 ([Ollama](https://github.com/ollama/ollama), RTX 3090, Q4_K_M) | — | 9GB |
| **Qwen 3.6 27B** | Qwen3.6-27B | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | Strongest local coding model (SWE-bench 77.2%). | 37 ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 3090, Q4_K_M) | — | 18GB |
| **Muse Glimmer 30B** | Muse-Glimmer-30B | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | Meta Superintelligence 30B agentic model, Apache 2.0. Fits 24/32 GB at 4-bit (<20GB weights + KV + vision + spec draft). DFlash drafter gives 3.1x decode on RTX 5090. | 233 (DFlash spec-decode), 74.9 stock ([llama.cpp](https://github.com/ggml-org/llama.cpp), RTX 5090, 4-bit) | 50 ([llama.cpp](https://github.com/ggml-org/llama.cpp), M5 Max (Apple Silicon), 4-bit) | 24GB |
| **Qwen3-30B-A3B** | Qwen3-30B-A3B Instruct (MoE, 3B active) | [link](https://huggingface.co/Qwen/Qwen3-30B-A3B) | MoE that a phone CPU can stream from flash: 128 experts/8 active, ~3B of work per token. BigMoeOnEdge ran it at 5.2 t/s offline on a 12 GB phone with no GPU/NPU; also the default second model in the llama.cpp Vitanom offline Android app. | 5.2 ([llama.cpp](https://github.com/ggml-org/llama.cpp), 12 GB phone CPU (flash-streamed, no GPU/NPU), Q4 / UD-Q2_K_XL) | — | 12GB |
| **DeepSeek R1 1.5B** | DeepSeek-R1-Distill-Qwen-1.5B | [link](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B) | Fully offline LLM on a $35 2019 Raspberry Pi 4B (2 GB) under Ollama at ~4 t/s for ~5 W — the canonical tiny-edge/CPU deployment. | 4 ([Ollama](https://github.com/ollama/ollama), Raspberry Pi 4B (2 GB LPDDR4), Q4) | — | 2GB |
| **gpt-oss-120b** | OpenAI gpt-oss-120b (MoE) | [link](https://huggingface.co/openai/gpt-oss-120b) | BigMoeOnEdge streams only the experts each token needs straight from flash on plain CPU: 60 GB model, 2.2 t/s on a 12 GB phone that is 5x smaller than the weights. 14x faster than mmap (0.09 t/s), byte-identical output. | 2.2 ([llama.cpp](https://github.com/ggml-org/llama.cpp), 12 GB phone CPU (4 cores, flash-streamed, no GPU/NPU), streamed (60 GB on disk)) | — | 12GB |

---

# 🟦 CUDA — NVIDIA GPUs (8–48 GB)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Qwen3.8-Flash-Next** | 125B MoE (6B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 24GB | [Strata](https://github.com/Niko1221/Strata) 1250 (2026-09-29); [Strata](https://github.com/Niko1221/Strata) 65.1 (2026-09-26) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [DFlash2](https://github.com/z-lab/dflash) 381 (2026-09-19); [llama.cpp](https://github.com/ggml-org/llama.cpp) 43.7 (2026-09-18) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 233 (DFlash spec-decode), 74.9 stock (2026-08-10) |
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 42.8 (2026-09-29); [llama.cpp](https://github.com/ggml-org/llama.cpp) 71 (2026-09-27); [llama.cpp](https://github.com/ggml-org/llama.cpp) 91 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (2026-09-26); [llama.cpp](https://github.com/ggml-org/llama.cpp) 143 (2026-09-18) |
| **Qwen3 8B** | 8B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-8B) | 8GB | [Ollama](https://github.com/ollama/ollama) 100 (2026-09-12) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 99.7 (2026-09-19) |
| **DeepSeek-V4-Flash** | 284B MoE (13B active) | MIT | [link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | 32GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 85 (2026-09-28); [FreeToken](https://github.com/FlashML-org/FreeToken) 22 (2026-09-27) |
| **Qwen3 14B** | 14B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-14B) | 9GB | [Ollama](https://github.com/ollama/ollama) 65 (2026-09-15) |
| **Qwen3.6-35B-A3B** | 35B MoE (3B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 8GB | [FreeToken](https://github.com/FlashML-org/FreeToken) 39.3 (2026-09-27) |
| **Qwen 3.6 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | 18GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 37 (2026-09-10) |
| **DeepSeek R1 1.5B** | 1.5B | MIT | [link](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B) | 2GB | [Ollama](https://github.com/ollama/ollama) 4 (2026-06-25) |

---

# 🟨 CPU — no GPU

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Gemma 4 E2B** | 2B | Gemma Terms of Use | [link](https://huggingface.co/google/gemma-4-E2B) | 2GB | [LiteRT](https://github.com/google-ai-edge/LiteRT) 99 (2026-09-05) |
| **Qwen3-30B-A3B** | 30B (3B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-30B-A3B) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 5.2 (2026-08-13) |
| **gpt-oss-120b** | 120B (5x phone RAM) | Apache 2.0 | [link](https://huggingface.co/openai/gpt-oss-120b) | 12GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 2.2 (2026-08-13) |

> CPU inference is **memory-bandwidth bound**. Use Q4 quant + a fast CPU build (AVX-512/AMX).

---

# 🟩 Metal — Apple Silicon (unified memory)

| Model | Params | License | HF | VRAM | t/s per engine |
|---|---|---|---|---|---|
| **Bonsai 2 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 12GB | [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) 237 (2026-09-26) |
| **Nemotron 3.5 Lightning** | 30B-A3B | NVIDIA Open Model License | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4) | 48GB | [TensorFold](https://github.com/ashhart/TensorFold) 206 (2026-09-30) |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | 16GB | [TensorFold](https://github.com/ashhart/TensorFold) 189 (2026-09-30); [TensorFold](https://github.com/ashhart/TensorFold) 124 (2026-09-27); [TensorFold](https://github.com/ashhart/TensorFold) 61.9 (2026-09-27); [MLX](https://github.com/ml-explore/mlx) 41.5 (2026-09-27) |
| **Qwen3.8-Flash-Next** | 125B MoE (6B active) | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 24GB | [TensorFold](https://github.com/ashhart/TensorFold) 92 (2026-09-27) |
| **Ornith 1.5 35B-A3B** | 35B-A3B | Apache 2.0 | [link](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B-MLX) | 24GB | [MLX](https://github.com/ml-explore/mlx) 50 (2026-09-29) |
| **Muse Glimmer 30B** | 30B | Apache 2.0 | [link](https://huggingface.co/meta-models/Muse-Glimmer-30B) | 24GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 50 (2026-08-10) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 9GB | [llama.cpp](https://github.com/ggml-org/llama.cpp) 49.67 (2026-09-19) |
| **RavenX-Conjecture-Qwen3-8B** | 8B | Apache 2.0 | [link](https://huggingface.co/deadbydawn101/RavenX-Conjecture-Qwen3-8B-MLX) | 8GB | [MLX](https://github.com/ml-explore/mlx) 42 (2026-09-29) |
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
