# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment — focused on the low end: models people genuinely run and recommend on a gaming laptop with an 8, 16, or 24 GB GPU.

Every figure below is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware it was measured on. Models are ranked by **X popularity** (views, likes, comments, HF downloads). Data spans **June–September 2026** so you can see how speeds evolved.

**Your reference machine:** RTX 4090 Laptop GPU (16 GB VRAM).

---

## How to read this

- **Backend** = where the model runs: **CUDA** (NVIDIA GPU), **CPU** (no GPU), **Metal** (Apple Silicon).
- **Engine** = the inference server/runtime you actually run. Pick per backend (see the engine guide at the bottom).
- **t/s** = tokens per second (decode/generation speed). Higher is better. Always tied to a specific quant + hardware.
- **RAM** = VRAM (GPU) or unified memory (Mac) needed to run it comfortably.

---

## 🏆 Top trending open-weight models on X (ranked by buzz)

| # | Model | Full name | HF link | Why it's trending |
|---|---|---|---|---|
| 1 | **Qwen3.8-27B** | Qwen3.8-27B-Instruct | [huggingface.co/Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) | The flagship local model. 384K views on the release post. 262K ctx (1M via YaRN), Apache 2.0. |
| 2 | **Qwen3 14B** | Qwen3-14B | [huggingface.co/Qwen/Qwen3-14B](https://huggingface.co/Qwen/Qwen3-14B) | 2M HF downloads. The community mid-size favorite — "the little engine that fucks." |
| 3 | **Gemma 4 12B** | gemma-4-12B-it | [huggingface.co/google/gemma-4-12B-it](https://huggingface.co/google/gemma-4-12B-it) | "Best overall personal-agent model." Multimodal + audio, 256K ctx. Multiple independent benchmark posts. |
| 4 | **Qwen3 8B** | Qwen3-8B | [huggingface.co/Qwen/Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) | The default 8 GB pick. Fast, Apache 2.0, huge ecosystem. |
| 5 | **Qwen 3.6 27B** | Qwen3.6-27B | [huggingface.co/Qwen/Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B) | "Strongest local coding model" (SWE-bench 77.2%). Fits 24 GB. |
| 6 | **Bonsai 2** | Ternary-Bonsai-2-27B | [huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 27B squeezed to 5.9 GB (ternary), 98.2% of full-precision. Viral — 4K downloads in 3 days. |
| 7 | **DeepSeek-R1 32B** | DeepSeek-R1-Distill-Qwen-32B | [huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B) | "Strongest local reasoning." MIT license. |
| 8 | **Qwen3.5 35B-A3B** | Qwen3.5-35B-A3B | [huggingface.co/Qwen/Qwen3.5-35B-A3B](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) | MoE (3B active) — big-model quality at small-model speed. Fits 24 GB. |
| 9 | **Gemma 4 26B A4B** | gemma-4-26B-A4B | [huggingface.co/google/gemma-4-26B-A4B](https://huggingface.co/google/gemma-4-26B-A4B) | MoE (4B active). Powers Google's Antigravity SDK local agents. |
| 10 | **MiniCPM5-2B** | MiniCPM5-2B | [huggingface.co/openbmb/MiniCPM5-2B](https://huggingface.co/openbmb/MiniCPM5-2B) | Highest Intelligence Index of any <4B open model. Best tiny/edge pick. |
| 11 | **gpt-oss-20b** | gpt-oss-20b | [huggingface.co/openai/gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b) | OpenAI's open model. Note: can't disable thinking → slower. |
| 12 | **Qwen3 32B** | Qwen3-32B | [huggingface.co/Qwen/Qwen3-32B](https://huggingface.co/Qwen/Qwen3-32B) | Strong general-purpose default for 24 GB. |

---

## 🟦 CUDA — NVIDIA GPUs (by VRAM tier)

### 8 GB VRAM (RTX 4060, RTX 3060, RTX 3080 10 GB)

| Model | Params | License | RAM | Measured t/s (X) | Engine |
|---|---|---|---|---|---|
| **Gemma 4 12B** (IQ4_XS) | 12B | Gemma | ~8 GB | **57.5 tok/s** decode, 1,816 tok/s prompt (RTX 3080 10 GB) | llama.cpp / Ollama |
| **Gemma 4 12B** (TurboQuant) | 12B | Gemma | ~8 GB | **30 tok/s** decode, 25K ctx (RTX 4060 8 GB) | llama.cpp (TurboQuant fork) |
| **Qwen3 8B** | 8B | Apache 2.0 | ~4–8 GB | ~100+ tok/s | Ollama / llama.cpp |
| **MiniCPM5-2B** | 2.6B | Apache 2.0 | ~2 GB | — | llama.cpp / Ollama |

### 12 GB VRAM (RTX 3060 12 GB, RTX 4070)

| Model | Params | License | RAM | Measured t/s (X) | Engine |
|---|---|---|---|---|---|
| **Qwen3 14B** | 14B | Apache 2.0 | ~9 GB | — | Ollama / llama.cpp |
| **Bonsai 2** (Qwen3.8-27B ternary) | 27B | Apache 2.0 | ~6 GB | **~50 tok/s** fresh, ~22 avg, 125K ctx (RTX 3060 12 GB) | llama.cpp (custom kernels) |
| **Qwen3.8-27B** (Mirai 2.4-bit) | 27B | Apache 2.0 | ~12 GB | **~40 tok/s** decode, ~1,000 tok/s prefill, 128K ctx (RTX 3090 @12 GB cap) | llama.cpp (Mirai port) |

### 16 GB VRAM (RTX 4090 Laptop, RTX 4080, RTX 3090) — your tier

| Model | Params | License | RAM | Measured t/s (X) | Engine |
|---|---|---|---|---|---|
| **Qwen3 14B** | 14B | Apache 2.0 | ~9 GB | ~65 tok/s (est) | Ollama / llama.cpp / vLLM |
| **Gemma 4 12B** | 12B | Gemma | ~9 GB | **99.7 tok/s** (RTX 4090 Laptop) | llama.cpp / Ollama |
| **Bonsai 2** (Qwen3.8-27B ternary) | 27B | Apache 2.0 | ~6 GB | ~50 tok/s fresh | llama.cpp |
| **Qwen3.8-27B** (Mirai 2.4-bit) | 27B | Apache 2.0 | ~15 GB | **85 tok/s** code, 57 prose, 128K ctx (Q8 KV + MTP) | llama.cpp (Mirai port) |
| **qwen2.5-coder:14b** | 14B | Apache 2.0 | ~8.4 GB | — | Ollama (time-shared) |

### 24 GB VRAM (RTX 4090 desktop, RTX 3090, RX 7900 XTX)

| Model | Params | License | RAM | Measured t/s (X) | Engine |
|---|---|---|---|---|---|
| **Qwen3.8-27B** | 27B | Apache 2.0 | ~18 GB | ~37 tok/s (est) | llama.cpp / Ollama / vLLM |
| **Qwen 3.6 27B** | 27B | Apache 2.0 | ~18 GB | — | llama.cpp / Ollama / vLLM |
| **DeepSeek-R1 32B** | 32B | MIT | ~20 GB | — | llama.cpp / Ollama / vLLM |
| **Qwen3.5 35B-A3B** (MoE) | 35B | Apache 2.0 | ~21 GB | — | llama.cpp / Ollama / vLLM |
| **Qwen3 32B** | 32B | Apache 2.0 | ~20 GB | ~32 tok/s (est) | llama.cpp / Ollama / vLLM |
| **Gemma 4 26B A4B** (MoE) | 26B | Gemma | ~16 GB | **22.9 tok/s** (IQ2_M, RTX 3080 10 GB) | llama.cpp / Ollama / LiteRT |

### 48 GB+ / multi-GPU (beyond the laptop, for context)

| Model | Params | License | RAM | Measured t/s (X) | Engine |
|---|---|---|---|---|---|
| **Qwen3.8-27B** (Q8_0) | 27B | Apache 2.0 | 2×24 GB | 150K ctx, MTP n=2 (2× RTX 3090 @300 W) | llama.cpp |
| **Qwen3-235B-A22B** (MoE) | 235B | Apache 2.0 | 2×128 GB | **17 tok/s** (b=1), 36 (b=4) (2× DGX Spark) | vLLM / SGLang |
| **MiniMax-M3** (MoE) | 428B | MiniMax | 2×128 GB | **13.7 tok/s** prose, 15 code, 20 peak (EAGLE3) | vLLM / SGLang |
| **Nemotron-3-Super 120B** | 120B | NVIDIA | ~58 GB (Q3) | — | llama.cpp / vLLM |

---

## 🟨 CPU-only (no GPU)

| Model | Params | License | RAM | Expected t/s | Engine |
|---|---|---|---|---|---|
| **MiniCPM5-2B** | 2.6B | Apache 2.0 | ~4 GB | 15–30 tok/s | llama.cpp (CPU) / Ollama |
| **Qwen3 8B** | 8B | Apache 2.0 | ~8 GB | 5–15 tok/s | llama.cpp (CPU) / Ollama |
| **Gemma 4 12B** | 12B | Gemma | ~12 GB | 3–8 tok/s | llama.cpp (CPU) |
| **Qwen3 14B** | 14B | Apache 2.0 | ~14 GB | 2–5 tok/s | llama.cpp (CPU) |

> CPU inference is **memory-bandwidth bound** — expect 5–15 tok/s for 8B-class, less for bigger. Use Q4 quant and a fast CPU build (AVX-512 / AMX). Fine for batch/offline, not interactive.

---

## 🟩 Metal — Apple Silicon (unified memory)

| Model | Params | License | RAM | Measured t/s (X) | Engine |
|---|---|---|---|---|---|
| **Qwen3.8-27B** | 27B | Apache 2.0 | ~16 GB | **120–124 tok/s** (MLX 4-bit, TensorFold, Mac mini M6) | MLX / TensorFold |
| **Qwen3.8-27B** | 27B | Apache 2.0 | ~16 GB | **87.9 tok/s** median, 971.8 tok/s prefill (M5 Max, mlx.fast) | MLX |
| **Nemotron Lightning 30B-A3B** | 30B | NVIDIA | ~16 GB | **188–206 tok/s** (MLX 4-bit, TensorFold) | MLX / TensorFold |
| **Qwen3.8-Flash-Next** | 125B/6B | Apache 2.0 | ~75 GB (1-bit) | **88–92 tok/s** (MLX 4-bit, TensorFold) | MLX / TensorFold |
| **Gemma 4 12B** | 12B | Gemma | ~12 GB | **49.67 tok/s** (M1 Ultra VM) | MLX / llama.cpp (Metal) |
| **Qwen3 14B** | 14B | Apache 2.0 | ~14 GB | — | MLX / llama.cpp (Metal) |
| **MiniCPM5-2B** | 2.6B | Apache 2.0 | ~4 GB | — | MLX / llama.cpp (Metal) |

> On Apple Silicon, **MLX** is the fastest engine (Apple's native framework). Speculative decoding (TensorFold/DFlash) gives the biggest speedups because Macs are memory-bandwidth bound.

---

## 📈 Speed evolution over several months (the aggregation)

How the same model got faster as inference engines improved — all community-measured on X:

### Qwen3.8-27B on Apple Silicon (Metal)

| Date | Engine | Hardware | Decode t/s | Prefill t/s |
|---|---|---|---|---|
| Jun 2026 | MLX (baseline) | M5 Max | ~26 | — |
| Aug 2026 | mlx.fast (speculative) | M5 Max | **87.9** (median) | ~971.8 |
| Sep 2026 | TensorFold (MLX 4-bit) | Mac mini M6 | **120–124** | — |

> **3.3x in 7 days** (Aug), then another jump with TensorFold. Dense models on Mac went from "slow" to "usable" in one quarter — driven by custom MTP heads + speculative decoding, not new hardware.

### Apple Silicon generation gap (prompt processing)

| Chip | Prompt t/s |
|---|---|
| M4 | 210 |
| M6 | **742** (253% faster) |

### CUDA / multi-GPU (frontier-scale, for context)

| Model | Setup | t/s |
|---|---|---|
| Qwen3-235B-A22B | 2× DGX Spark (256 GB) | 17 (b=1) / 36 (b=4) |
| MiniMax-M3 | 2× DGX Spark | 13.7 prose / 15 code / 20 peak |

---

## ⚙️ Inference engine / server guide

Pick the engine for your backend:

| Engine | Backend | Best for | Notes |
|---|---|---|---|
| **Ollama** | CUDA / CPU / Metal | Easiest start | One command to pull + run a GGUF. Great default. |
| **llama.cpp** | CUDA / CPU / Metal | Max control, custom quants | The reference runtime. Use for Bonsai 2 / Mirai 2.4-bit (custom kernels). |
| **LM Studio** | CUDA / CPU / Metal | GUI, no CLI | Point-and-click local models. |
| **vLLM** | CUDA | Production serving, high throughput | Best for concurrent requests / APIs. Needs more VRAM. |
| **SGLang** | CUDA | High-throughput serving | vLLM alternative; strong batching. |
| **MLX** | Metal | Fastest on Apple Silicon | Apple's native framework. Use for Qwen3.8-27B on Mac. |
| **TensorFold** | Metal | Speculative decoding on Mac | Draft-and-verify; 3–6x speedup on memory-bound Macs. |
| **TensorRT-LLM** | CUDA | Max NVIDIA perf | Most work to set up; best raw speed on NVIDIA. |
| **LiteRT** | CUDA / Metal | Google's local runtime | For Gemma 4 + Antigravity SDK agents. |

**Quick picks:**
- **Just want it to work:** Ollama.
- **Gaming laptop (CUDA), max speed:** llama.cpp (or vLLM if serving many requests).
- **MacBook (Metal):** MLX + TensorFold for the big speedups.
- **Tiny/edge/CPU:** llama.cpp CPU build.

---

## How to contribute

- Open a PR adding a model that genuinely changes the local-LLM landscape.
- Include: full model name, HF link, license, params, RAM, a **measured** t/s figure with the hardware + quant it was run on, and the engine.
- Prefer numbers from real X benchmark posts over vendor claims.

## License

Apache License 2.0. See [LICENSE](LICENSE).
