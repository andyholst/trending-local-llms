# Trending Local LLMs

A curated, living list of **open-weight** LLMs that actually make a difference for local deployment — focused on the low end: models you can run effectively on a gaming laptop with an 8, 16, or 24 GB GPU.

The reference machine is an **RTX 4090 Laptop GPU (16 GB VRAM)** — the sweet spot for "run it on a gaming laptop." Speeds are marked **measured** (real benchmark runs) vs **estimated** (bandwidth-based projections). Always check the model card before trusting a number.

## The low-end tier: 8 / 16 / 24 GB

### 8 GB VRAM — small cards, laptops, iGPU

| Model | Params | License | VRAM (Q4) | Speed | Notes |
|---|---|---|---|---|---|
| **Qwen3 8B** | 8B | Apache 2.0 | ~4–8 GB | ~117 tok/s (est, 24 GB card) | The default 8 GB pick; strong general use |
| **Gemma 4 E2B** | 2B | Gemma | ~2 GB | — | Best tiny model; runs on iGPU/edge |
| **Phi-4-mini** | 3.8B | MIT | ~3 GB | — | Best CPU-only / low-RAM option |
| **Gemma 3 4B** | 4B | Gemma | ~3 GB | — | Solid entry point for 8 GB laptops |

### 16 GB VRAM — RTX 4090 Laptop, RTX 4080, RTX 3090 (your tier)

| Model | Params | License | VRAM | Speed | Notes |
|---|---|---|---|---|---|
| **Gemma 4 12B it** | 12B | Gemma | 8.6 GB @32k | **99.7 tok/s** (measured, RTX 4090 Laptop) | Best tested all-rounder for 16 GB |
| **Qwen3 14B** | 14B | Apache 2.0 | ~8–9 GB | ~65 tok/s (est) | Sweet spot for coding & analysis |
| **DeepSeek-R1-Distill-14B** | 14B | MIT | ~9–10 GB | — | Reasoning-focused; strong math |
| **Qwen3.5 35B-A3B** (MoE) | 35B | Apache 2.0 | ~16 GB (Q4) | — | Best quality that still fits 16 GB; use Q4_K_XL |
| **Qwen3.8-27B** | 27B | Apache 2.0 | 18.2 GB @32k | — | Fits 16 GB only at reduced context |

### 24 GB VRAM — RTX 4090 desktop, RTX 3090, RX 7900 XTX

| Model | Params | License | VRAM | Speed | Notes |
|---|---|---|---|---|---|
| **Gemma 4 26B-A4B** (MoE) | 26B | Gemma | ~16 GB | ~85 tok/s (est) | Best balance on 24 GB; vision + tools |
| **LFM2 24B-A2B** (MoE) | 24B | — | ~16 GB | ~118 tok/s (est) | Fastest MoE in this class |
| **GPT-OSS 20B** | 20B | — | ~16 GB | ~87 tok/s (est) | Strong open alternative |
| **Qwen3.8 27B** | 27B | Apache 2.0 | ~18 GB | ~37 tok/s (est) | Frontier-adjacent quality |
| **Qwen3 32B** | 32B | Apache 2.0 | ~17 GB (INT4) | ~32 tok/s (est) | Strong general-purpose default |
| **Gemma 4 31B** | 31B | Gemma | ~24 GB | — | Frontier-adjacent (AIME 89.2%, GPQA 84.3%) |
| **Mistral Small 4** | 119B/6B | Apache 2.0 | ~24 GB | — | Enterprise multilingual, multimodal |

## Picks by goal

- **Best all-rounder on a 16 GB gaming laptop:** Gemma 4 12B it (~100 tok/s measured)
- **Best coding on 16 GB:** Qwen3 14B
- **Best quality that still fits 16 GB:** Qwen3.5 35B-A3B (MoE, Q4)
- **Best on 24 GB:** Gemma 4 26B-A4B
- **Best tiny / CPU-only:** Phi-4-mini, Gemma 4 E2B

## How to contribute

- Open a PR adding a model that genuinely changes the local-LLM landscape.
- Include: provider, license, params, VRAM, and a **measured** t/s figure with the hardware it was run on (label estimates as such).
- Keep it to models with **open weights** and a **permissive or practical license** — no API-only models.

## License

Apache License 2.0. See [LICENSE](LICENSE).
