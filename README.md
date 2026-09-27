# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment. Every figure is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware it was measured on. Data spans **June–September 2026**.

**Structure:** GPU type first (CUDA / CPU / Metal), then VRAM tier (6 → 512 GB), each tier sorted by **highest t/s**, with the **one specific engine** that runs it best.

**Your reference machine:** RTX 4090 Laptop GPU (16 GB VRAM).

---

## 🏆 Top trending open-weight models on X (ranked by buzz)

| # | Model | Full name | HF link | Why it's trending |
|---|---|---|---|---|
| 1 | **Qwen3.8-27B** | Qwen3.8-27B-Instruct | [huggingface.co/Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) | The flagship local model. 384K views on release. 262K ctx (1M via YaRN), Apache 2.0. |
| 2 | **Qwen3 14B** | Qwen3-14B | [huggingface.co/Qwen/Qwen3-14B](https://huggingface.co/Qwen/Qwen3-14B) | 2M HF downloads. The community mid-size favorite. |
| 3 | **Gemma 4 12B** | gemma-4-12B-it | [huggingface.co/google/gemma-4-12B-it](https://huggingface.co/google/gemma-4-12B-it) | "Best overall personal-agent model." Multimodal + audio, 256K ctx. |
| 4 | **Qwen3 8B** | Qwen3-8B | [huggingface.co/Qwen/Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) | The default 8 GB pick. Fast, Apache 2.0. |
| 5 | **Qwen 3.6 27B** | Qwen3.6-27B | [huggingface.co/Qwen/Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B) | "Strongest local coding model" (SWE-bench 77.2%). |
| 6 | **Bonsai 2** | Ternary-Bonsai-2-27B | [huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 27B in 5.9 GB (ternary), 98.2% of full-precision. Viral. |
| 7 | **DeepSeek-R1 32B** | DeepSeek-R1-Distill-Qwen-32B | [huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B) | "Strongest local reasoning." MIT. |
| 8 | **Qwen3.5 35B-A3B** | Qwen3.5-35B-A3B | [huggingface.co/Qwen/Qwen3.5-35B-A3B](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) | MoE (3B active) — big-model quality at small-model speed. |
| 9 | **Gemma 4 26B A4B** | gemma-4-26B-A4B | [huggingface.co/google/gemma-4-26B-A4B](https://huggingface.co/google/gemma-4-26B-A4B) | MoE (4B active). Powers Google's Antigravity SDK agents. |
| 10 | **MiniCPM5-2B** | MiniCPM5-2B | [huggingface.co/openbmb/MiniCPM5-2B](https://huggingface.co/openbmb/MiniCPM5-2B) | Highest Intelligence Index of any <4B open model. |
| 11 | **gpt-oss-20b** | gpt-oss-20b | [huggingface.co/openai/gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b) | OpenAI's open model. Can't disable thinking → slower. |
| 12 | **Qwen3 32B** | Qwen3-32B | [huggingface.co/Qwen/Qwen3-32B](https://huggingface.co/Qwen/Qwen3-32B) | Strong general-purpose default for 24 GB. |

---

# 🟦 CUDA — NVIDIA GPUs

## 6 GB VRAM

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **MiniCPM5-2B** | 2.6B | Apache 2.0 | [link](https://huggingface.co/openbmb/MiniCPM5-2B) | — | llama.cpp |
| **Gemma 4 12B** (TurboQuant) | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | **30 tok/s** (RTX 4060 8 GB) | llama.cpp (TurboQuant) |

## 8 GB VRAM

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Qwen3 8B** | 8B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-8B) | ~100+ tok/s | Ollama |
| **Gemma 4 12B** (IQ4_XS) | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | **57.5 tok/s** (RTX 3080 10 GB) | llama.cpp |
| **MiniCPM5-2B** | 2.6B | Apache 2.0 | [link](https://huggingface.co/openbmb/MiniCPM5-2B) | — | llama.cpp |

## 12 GB VRAM

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Bonsai 2** (Qwen3.8-27B ternary) | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | **~50 tok/s** (RTX 3060 12 GB) | llama.cpp |
| **Qwen3.8-27B** (Mirai 2.4-bit) | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | **~40 tok/s** decode, ~1,000 prefill (RTX 3090 @12 GB) | llama.cpp (Mirai) |
| **Qwen3 14B** | 14B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-14B) | — | Ollama |

## 16 GB VRAM — your tier

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | **99.7 tok/s** (RTX 4090 Laptop) | llama.cpp |
| **Qwen3.8-27B** (Mirai 2.4-bit) | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | **85 tok/s** code, 57 prose (Q8 KV + MTP) | llama.cpp (Mirai) |
| **Qwen3 14B** | 14B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-14B) | ~65 tok/s (est) | Ollama |
| **Bonsai 2** (Qwen3.8-27B ternary) | 27B | Apache 2.0 | [link](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | ~50 tok/s | llama.cpp |

## 24 GB VRAM

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Qwen 3.6 35B-A3B** (MoE) | 35B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) | **~100+ tok/s** (RTX 3090) | llama.cpp |
| **Qwen 3.6 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | **~37 tok/s**, 60–80 with MTP (RTX 3090) | llama.cpp |
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | ~37 tok/s (est) | llama.cpp |
| **Qwen3 32B** | 32B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-32B) | ~32 tok/s (est) | llama.cpp |
| **DeepSeek-R1 32B** | 32B | MIT | [link](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B) | — | llama.cpp |
| **Gemma 4 26B A4B** (MoE) | 26B | Gemma | [link](https://huggingface.co/google/gemma-4-26B-A4B) | **22.9 tok/s** (IQ2_M, RTX 3080 10 GB) | llama.cpp |

## 32 GB VRAM (RTX 5090, Arc Pro B70)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Qwen 3.6 35B-A3B** (MoE) | 35B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) | **54.7 tok/s** (Arc Pro B70) | vLLM |
| **Qwen 3.6 27B** (Q8) | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | — | vLLM |

## 48 GB VRAM (RTX 6000 Ada, 2× RTX 3090)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Nemotron-3-Super 120B** (Q3) | 120B | NVIDIA | [link](https://huggingface.co/collections/nvidia/nvidia-nemotron-v3) | — | llama.cpp |

## 64 GB VRAM (4× RX 9070 XT — tinybox)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **70B-class** (Q4) | 70B | varies | — | — | tinygrad |

## 96 GB VRAM (RTX PRO 6000 Blackwell)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Nemotron-3-Super 120B** (Q4) | 120B | NVIDIA | [link](https://huggingface.co/collections/nvidia/nvidia-nemotron-v3) | — | llama.cpp |

## 128 GB VRAM (2× RTX PRO 6000)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Qwen3-235B-A22B** (MoE) | 235B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-235B-A22B) | — | vLLM |

## 256 GB VRAM (2× DGX Spark)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Qwen3-235B-A22B** (MoE) | 235B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-235B-A22B) | **17 tok/s** (b=1), 36 (b=4) | vLLM |
| **MiniMax-M3** (MoE) | 428B | MiniMax | [link](https://huggingface.co/MiniMaxAI/MiniMax-M3) | **13.7 tok/s** prose, 15 code, 20 peak (EAGLE3) | vLLM |

## 384 GB VRAM (4× RTX PRO 6000)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Qwen3.5-397B-A17B** (MoE) | 397B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.5-397B-A17B) | **152 tok/s** (MTP5) | vLLM |
| **MiniMax-M2.5** (MoE) | 456B | MiniMax | [link](https://huggingface.co/MiniMaxAI/MiniMax-M2.5) | **85–89 tok/s** | vLLM |

## 512 GB VRAM (4× DGX Spark)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **GLM-5.2** | 753B | MIT | [link](https://huggingface.co/zai-org/GLM-5.2) | **22–24 tok/s**, ~28 agentic (NVFP4) | vLLM |

## 576 GB VRAM (6× RTX PRO 6000)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **GLM-5.2** | 753B | MIT | [link](https://huggingface.co/zai-org/GLM-5.2) | **120 tok/s** | vLLM |

---

# 🟨 CPU — no GPU

| Model | Params | License | HF | Expected t/s | Engine |
|---|---|---|---|---|---|
| **MiniCPM5-2B** | 2.6B | Apache 2.0 | [link](https://huggingface.co/openbmb/MiniCPM5-2B) | 15–30 tok/s | llama.cpp (CPU) |
| **Qwen3 8B** | 8B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-8B) | 5–15 tok/s | llama.cpp (CPU) |
| **Gemma 4 12B** | 12B | Gemma | [link](https://huggingface.co/google/gemma-4-12B-it) | 3–8 tok/s | llama.cpp (CPU) |
| **Qwen3 14B** | 14B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-14B) | 2–5 tok/s | llama.cpp (CPU) |

> CPU inference is **memory-bandwidth bound**. Use Q4 quant + a fast CPU build (AVX-512/AMX). Fine for batch/offline, not interactive.

---

# 🟩 Metal — Apple Silicon (unified memory)

## 48 GB (Mac Mini M4 Pro)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Qwen 3.6 35B-A3B** (MoE) | 35B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) | — | MLX |
| **Qwen 3.6 27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | **~17 tok/s**, ~32 with MTP | MLX |

## 64 GB (Mac Mini M4 Pro)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Qwen 3.6 35B-A3B** (MoE) | 35B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) | — | MLX |

## 96 GB (Mac Studio M3 Ultra)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Qwen 3.6 27B** (Q8) | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.6-27B) | — | MLX |
| **70B-class** (Q4) | 70B | varies | — | — | MLX |

## 128 GB (MacBook Pro M5 Max)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Qwen3.8-27B** | 27B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-27B) | **120–124 tok/s** (TensorFold) | TensorFold |
| **Nemotron Lightning 30B-A3B** | 30B | NVIDIA | [link](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16) | **188–206 tok/s** | TensorFold |
| **Qwen3.8-Flash-Next** | 125B/6B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | **88–92 tok/s** | TensorFold |
| **70B-class** (Q4) | 70B | varies | — | ~14 tok/s, ~27 with MTP | MLX |
| **Qwen3-235B-A22B** (MoE) | 235B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-235B-A22B) | — | MLX |

## 256 GB (Mac Studio M3 Ultra)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **Qwen3-235B-A22B** (MoE) | 235B | Apache 2.0 | [link](https://huggingface.co/Qwen/Qwen3-235B-A22B) | — | MLX |
| **GLM-5.2** (Q2) | 753B | MIT | [link](https://huggingface.co/zai-org/GLM-5.2) | 15–20 tok/s (est) | MLX |

## 512 GB (Mac Studio M3 Ultra)

| Model | Params | License | HF | t/s | Engine |
|---|---|---|---|---|---|
| **GLM-5.2** (Q3/Q4) | 753B | MIT | [link](https://huggingface.co/zai-org/GLM-5.2) | — | MLX |
| **Kimi K2.5** | 1T | Modified MIT | [link](https://huggingface.co/moonshotai/Kimi-K2.5) | 5–10 tok/s | MLX |

> On Apple Silicon, **MLX** is the fastest engine; **TensorFold** adds speculative decoding (3–6x on memory-bound Macs). Prefill is the weak spot — use prefix caching.

---

## 📈 Speed evolution over several months

**Qwen3.8-27B on Apple Silicon** — same model, faster engines:

| Date | Engine | Hardware | Decode t/s |
|---|---|---|---|
| Jun 2026 | MLX (baseline) | M5 Max | ~26 |
| Aug 2026 | mlx.fast (speculative) | M5 Max | **87.9** |
| Sep 2026 | TensorFold (MLX 4-bit) | Mac mini M6 | **120–124** |

> **3.3x in 7 days** (Aug), then another jump with TensorFold — driven by custom MTP heads + speculative decoding, not new hardware.

---

## ⚙️ Inference engine / server guide

| Engine | Backend | Best for | Notes |
|---|---|---|---|
| **Ollama** | CUDA / CPU / Metal | Easiest start | One command to pull + run a GGUF. |
| **llama.cpp** | CUDA / CPU / Metal | Max control, custom quants | Use for Bonsai 2 / Mirai 2.4-bit (custom kernels). |
| **vLLM** | CUDA | Production serving, high throughput | Best for concurrent requests / big MoE. |
| **SGLang** | CUDA | High-throughput serving | vLLM alternative; strong batching. |
| **MLX** | Metal | Fastest on Apple Silicon | Apple's native framework. |
| **TensorFold** | Metal | Speculative decoding on Mac | 3–6x speedup on memory-bound Macs. |
| **TensorRT-LLM** | CUDA | Max NVIDIA perf | Most setup; best raw speed. |
| **LiteRT** | CUDA / Metal | Google's local runtime | For Gemma 4 + Antigravity SDK agents. |

**Quick picks:** Ollama (just works) · llama.cpp (gaming laptop, max speed) · MLX + TensorFold (Mac) · llama.cpp CPU (tiny/edge).

---

## How to contribute

- Open a PR adding a model that genuinely changes the local-LLM landscape.
- Include: full model name, HF link, license, params, RAM, a **measured** t/s figure with the hardware + quant it was run on, and the **one** engine.
- Prefer numbers from real X benchmark posts over vendor claims.

## License

Apache License 2.0. See [LICENSE](LICENSE).
