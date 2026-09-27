# Trending Local LLMs

A curated, living list of open-weight large language models that actually make a difference for local deployment and self-hosting. The goal is to track models worth running yourself — not every release, just the ones that move the needle on quality, efficiency, or licensing.

## Why this list exists

Open-weight models are the only way to run LLMs fully on your own hardware, keep your data private, and avoid per-token API costs. This repo tracks the models that are genuinely worth watching: strong benchmarks, permissive licenses, and practical local deployment.

## The list

| Model | Provider | License | Params (total / active) | Why it matters |
|---|---|---|---|---|
| **DeepSeek-V4-Pro** | DeepSeek | MIT | 1.6T / 49B | Frontier-level coding and reasoning; fully open weights, unrestricted fine-tuning |
| **DeepSeek-V4-Flash** | DeepSeek | MIT | 284B / 13B | Cheapest frontier-class inference; efficient MoE |
| **DeepSeek-R1** | DeepSeek | MIT | 671B / 37B | The reasoning model that kicked off the open-R1 wave |
| **GLM-5.2** | Zhipu AI | MIT | 753B / 40B | Best-in-class reasoning (GPQA Diamond 91.2%); 1M context |
| **Kimi K2.6 / K2.7 Code** | Moonshot | Modified MIT | 1T / 32B | Strong agentic computer-use and long-running coding agents |
| **MiniMax M3** | MiniMax | MiniMax Community | 428B / 23B | Top-tier real-world bug fixing (SWE-bench 80.5%) |
| **Hunyuan Hy3** | Tencent | Apache 2.0 | 295B / 21B | Strong all-rounder under a clean Apache license |
| **Step-3.7-Flash** | Stepfun | Apache 2.0 | 198B / 11B | Low-cost algorithmic tasks; Apache 2.0 |
| **Qwen3.6-27B** | Qwen | Apache 2.0 | 27B / 27B | Best practical model for 24GB systems; coding + tool calling |
| **Nemotron 3 Super / Ultra** | NVIDIA | OpenMDW-1.1 | 550B / 55B | Open weights, datasets, and training recipes; auditable agents |
| **Gemma 4** | Google | Gemma / Apache 2.0 | 12B / 31B | Best single-GPU and laptop/edge deployment |
| **Mistral Small 4** | Mistral | Apache 2.0 | 119B / 6B | Enterprise multilingual, multimodal, document workflows |
| **LLaMA 4** | Meta | Llama License | — | The reference open-weight family; huge ecosystem |

## How to contribute

- Open a PR adding a model that genuinely changes the local-LLM landscape.
- Include: provider, license, parameter count, and one line on why it matters.
- Keep it to models with **open weights** and a **permissive or practical license** — no API-only models.

## License

Apache License 2.0. See [LICENSE](LICENSE).
