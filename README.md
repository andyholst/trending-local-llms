# Trending Local LLMs

A living list of **open-weight** LLMs that actually make a difference for local deployment — focused on the low end: models people genuinely run and recommend on a gaming laptop with an 8, 16, or 24 GB GPU.

Numbers below are **community-reported on X** (real benchmark posts, not vendor claims). Hardware is noted per figure. Your reference machine is an **RTX 4090 Laptop GPU (16 GB VRAM)**.

## 8 GB VRAM — small cards, laptops, iGPU

| Model | Params | License | Measured speed (X) | Hardware | Notes |
|---|---|---|---|---|---|
| **Gemma 4 12B** (IQ4_XS) | 12B | Gemma | **57.5 tok/s** decode, 1,816 tok/s prompt | RTX 3080 10 GB | "Best overall personal-agent model" on 10 GB |
| **Gemma 4 12B** (TurboQuant) | 12B | Gemma | **30 tok/s** decode, 25K ctx | RTX 4060 8 GB | Agentic/coding finetune; any 6 GB+ GPU |
| **Qwen3 8B** | 8B | Apache 2.0 | ~100+ tok/s | 8 GB | The default 8 GB pick |
| **MiniCPM5-2B** | 2.6B | Apache 2.0 | — | 8 GB | Highest Intelligence Index of any <4B open model |

## 16 GB VRAM — RTX 4090 Laptop, RTX 4080, RTX 3090 (your tier)

| Model | Params | License | Measured speed (X) | Hardware | Notes |
|---|---|---|---|---|---|
| **Qwen3 14B** | 14B | Apache 2.0 | — | 12 GB VRAM | 2M HF downloads; "the little engine that fucks"; the community mid-size favorite |
| **Gemma 4 12B** | 12B | Gemma | — | ~16 GB | MMLU-Pro 77.2%, GPQA 78.8%, 256K ctx, multimodal + audio |
| **Bonsai 2** (Qwen3.8-27B, ternary) | 27B | Apache 2.0 | **~50 tok/s** fresh, ~22 avg | RTX 3060 12 GB | 5.9 GB weights, 98.2% of full-precision, 125K ctx |
| **Qwen3.8-27B** (Mirai 2.4-bit) | 27B | Apache 2.0 | **85 tok/s** code, 57 prose | 16 GB (Q8 KV + MTP) | 128K ctx at 14.6 GB; ~40 tok/s decode on 12 GB |

## 24 GB VRAM — RTX 4090 desktop, RTX 3090, RX 7900 XTX

| Model | Params | License | Measured speed (X) | Hardware | Notes |
|---|---|---|---|---|---|
| **Qwen3.8-27B** | 27B | Apache 2.0 | **120–124 tok/s** (MLX 4-bit, TensorFold) | Mac mini M6 | The flagship local model; 262K ctx, 1M via YaRN; huge X buzz |
| **Qwen 3.6 27B** | 27B | Apache 2.0 | — | 24 GB | "Strongest local coding model" (SWE-bench 77.2%) |
| **DeepSeek-R1 32B** | 32B | MIT | — | 24 GB | "Strongest local reasoning" |
| **Qwen3.5 35B-A3B** (MoE) | 35B | Apache 2.0 | — | 21 GB | Fast + smart; fits 24 GB |
| **Qwen3 32B** | 32B | Apache 2.0 | — | ~20 GB (Q4) | Strong general-purpose default |
| **Gemma 4 26B A4B** (MoE) | 26B | Gemma | **22.9 tok/s** (IQ2_M) | RTX 3080 10 GB | LiteRT + Antigravity SDK local agents; Google recommends >24 GB |

## Picks by goal (community consensus on X)

- **Best all-rounder on 16 GB:** Qwen3 14B (the crowd favorite) or Gemma 4 12B
- **Best quality that fits 16 GB:** Bonsai 2 / Qwen3.8-27B (2.4-bit) — 27B-class in ~6 GB
- **Best on 24 GB:** Qwen3.8-27B
- **Best tiny / 8 GB:** Gemma 4 12B (IQ4_XS) or MiniCPM5-2B

## How to contribute

- Open a PR adding a model that genuinely changes the local-LLM landscape.
- Include: provider, license, params, VRAM, and a **measured** t/s figure with the hardware it was run on.
- Prefer numbers from real X benchmark posts over vendor claims.

## License

Apache License 2.0. See [LICENSE](LICENSE).
