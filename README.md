# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment. Every figure is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware and engine it was measured on. This README is **automatically regenerated** from `data/models.json` — see [AGENTS.md](AGENTS.md) and `skills/gather-data.md`.

**How the ranking works.** Models are grouped 🔥 **trending** (seen in the last 7 days) → 🕑 **recent** (last 30 days) → 💤 **stale** (older, kept with their last measurement date). Within a group they rank by **Trend = buzz + speed**:
- **buzz** — for every distinct X post in the last 7 days: 1 + 0.5×log2(1 + likes + 2×comments + 3×reshares) + 0.25×log10(1 + views). Every post counts, so a model many people are posting about beats one post with a few interactions; engagement adds on top with diminishing returns.
- **speed** — log2(1 + t/s ÷ 10) for the model's fastest measurement on consumer hardware (GPUs up to 48 GB, Apple Silicon, CPU; datacenter parts never count), only while it is trending: 10 t/s → +1, 70 → +3, 150 → +4.

Ties go to more posts, then the highest t/s. t/s is always shown **per engine**, with the hardware and quant it was measured on.

> Last generated: 2026-10-02 02:23 UTC. Source: lightbrd.com mirror (X posts).

---

## ❤️ Most loved open-weight models on X (ranked by trend: 7-day buzz + speed)

Best measured t/s per backend; the full list of measurements is in the backend tables below.

| Model | Status | Trend | CUDA t/s (best) | Metal t/s (best) | CPU t/s (best) | VRAM | Why people love it |
|---|---|---|---|---|---|---|---|
| [**Qwen3.8-27B**](https://huggingface.co/Qwen/Qwen3.8-27B)<br><sub>Qwen3.8-27B-Instruct · 27B · Apache 2.0</sub> | 🔥 trending<br><sub>last seen 2026-10-01</sub> | **14.2**<br><sub>buzz 9.9 · 3 posts · speed +4.3 (189 t/s, M5 Max)</sub> | **44** t/s<br>[SGLang](https://github.com/sgl-project/sglang) · DGX Spark · DFlash2 spec-decode draft head<br><sub>+2 more</sub> | **189** t/s<br>[TensorFold](https://github.com/ashhart/TensorFold) · M5 Max · 4-bit MLX, DFlash2 drafter<br><sub>+2 more</sub> | — | 16GB | Flagship local model. 384K views on release. 262K ctx (1M via YaRN). |
| [**Bonsai 2 27B**](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf)<br><sub>Ternary-Bonsai-2-27B · 27B · Apache 2.0</sub> | 🔥 trending<br><sub>last seen 2026-10-01</sub> | **10.6**<br><sub>buzz 6 · 5 posts · speed +4.6 (237 t/s, Apple Silicon 16GB Mac)</sub> | **143** t/s<br>[llama.cpp (PrismML fork)](https://github.com/PrismML-Eng/llama.cpp) · RTX 5090 · ternary<br><sub>+4 more</sub> | **237** t/s<br>[MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) · Apple Silicon 16GB Mac · mlx.fast 4-bit | — | 12GB | PrismML 1.75-bit ternary compression of Qwen3.8-27B; ~98.2% capability in 5.9 GB. 11,792 downloads in 5 days. Runs big-VRAM-quality (262K ctx, MTP, vision on 16 GB) on old low-end cards. |
| [**Nemotron 3.5 Lightning 30B**](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16)<br><sub>NVIDIA-Nemotron-3.5-Lightning-30B-A3B · 30B (3B active) · OpenMDW 1.1</sub> | 🔥 trending<br><sub>last seen 2026-09-30</sub> | **7**<br><sub>buzz 2.6 · 1 post · speed +4.4 (206 t/s, M5 Max)</sub> | — | **206** t/s<br>[TensorFold](https://github.com/ashhart/TensorFold) · M5 Max · 4-bit MLX | — | 16GB | NVIDIA-Nemotron-3.5-Lightning-30B-A3B — see source posts. |
| [**RavenX-Conjecture-Qwen3-8B-MLX**](https://huggingface.co/deadbydawn101/RavenX-Conjecture-Qwen3-8B-MLX)<br><sub>RavenX-Conjecture-Qwen3-8B-MLX · 8B · Apache 2.0</sub> | 🔥 trending<br><sub>last seen 2026-09-29</sub> | **6.1**<br><sub>buzz 3.7 · 1 post · speed +2.4 (42 t/s, M3)</sub> | — | **42** t/s<br>[MLX](https://github.com/ml-explore/mlx) · M3 · MLX | — | 8GB | RavenX-Conjecture-Qwen3-8B-MLX — see source posts. |
| [**GLM-5.3**](https://huggingface.co/audnai/penclaw-GLM-5.3-abliterated)<br><sub>GLM-5.3-NVFP4 (abliterated) · 753B · Unknown</sub> | 🔥 trending<br><sub>last seen 2026-10-01</sub> | **5.9**<br><sub>buzz 4.4 · 1 post · speed +1.5 (18 t/s, CPU hybrid inference)</sub> | — | — | **18** t/s<br>DeepSeekHarness · CPU hybrid inference · NVFP4, 256K context, KV precache (170 t/s prefill) | CPU | GLM-5.3-NVFP4 (abliterated 'Warlock') runs on CPU hybrid inference via DeepSeekHarness at 18 t/s decode with 170 t/s prefill, using a KV precache strategy so an 11K-token head processes in seconds. |
| [**Qwen3.8-Flash-Next 125B**](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)<br><sub>Qwen3.8-Flash-Next-125B · 125B (MoE) · Apache 2.0</sub> | 🔥 trending<br><sub>last seen 2026-10-01</sub> | **5.8**<br><sub>buzz 2.4 · 1 post · speed +3.4 (93 t/s, RTX 5070 12GB)</sub> | **93** t/s<br>[Strata](https://github.com/Niko1221/Strata) · RTX 5070 12GB · MoE, experts across GPU/RAM/SSD | — | — | 12GB | Qwen3.8-Flash-Next-125B — see source posts. |
| [**Ornith 1.5 35B**](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B-MLX)<br><sub>Ornith-1.5-35B-A3B · 35B (3B active) · Apache 2.0</sub> | 🔥 trending<br><sub>last seen 2026-09-29</sub> | **4.8**<br><sub>buzz 2.2 · 1 post · speed +2.6 (50 t/s, MacBook Pro M5 48GB)</sub> | — | **50** t/s<br>[MLX](https://github.com/ml-explore/mlx) · MacBook Pro M5 48GB · 4-bit MLX | — | 16GB | Ornith-1.5-35B-A3B — see source posts. |
| [**Qwen3 8B**](https://huggingface.co/Qwen/Qwen3-8B)<br><sub>Qwen3-8B · 8B · Apache 2.0</sub> | 🕑 recent<br><sub>last seen 2026-09-12</sub> | **0**<br><sub>no posts in 7 days</sub> | **100** t/s<br>[Ollama](https://github.com/ollama/ollama) · RTX 4060 · Q4_K_M | — | — | 8GB | The default 8 GB pick. Fast, Apache 2.0. |
| [**Gemma 4 12B**](https://huggingface.co/google/gemma-4-12B-it)<br><sub>gemma-4-12B-it · 12B · Gemma</sub> | 🕑 recent<br><sub>last seen 2026-09-19</sub> | **0**<br><sub>no posts in 7 days</sub> | **99.7** t/s<br>[llama.cpp](https://github.com/ggml-org/llama.cpp) · RTX 4090 Laptop · Q4 | **49.67** t/s<br>[llama.cpp](https://github.com/ggml-org/llama.cpp) · Apple Silicon · Q4 | — | 9GB | Best overall personal-agent model. Multimodal + audio, 256K ctx. |
| [**Qwen3 14B**](https://huggingface.co/Qwen/Qwen3-14B)<br><sub>Qwen3-14B · 14B · Apache 2.0</sub> | 🕑 recent<br><sub>last seen 2026-09-15</sub> | **0**<br><sub>no posts in 7 days</sub> | **65** t/s<br>[Ollama](https://github.com/ollama/ollama) · RTX 3090 · Q4_K_M | — | — | 9GB | 2M HF downloads. The community mid-size favorite. |
| [**Quillan-Ronin**](https://huggingface.co/CrashOverrideX/Quillan-Ronin)<br><sub>Quillan-Ronin v5.4.0-oni · 4.57B · apache-2.0</sub> | 🕑 recent<br><sub>last seen 2026-09-24</sub> | **0**<br><sub>no posts in 7 days</sub> | — | — | **43** t/s<br>quillan.cpp · PC (CPU) · BitNet 1.58-bit, 23-43 tok/s | 4GB | Quillan-Ronin is a BitNet 1.58-bit ternary H-NMoE built for consumer hardware (i5-7000 / GTX 1050 Ti class, CPU). Its custom quillan.cpp CPU inference engine lifts tokens/s from 14-16 to 23-43 on a PC. |
| [**Qwen 3.6 27B**](https://huggingface.co/Qwen/Qwen3.6-27B)<br><sub>Qwen3.6-27B · 27B · Apache 2.0</sub> | 🕑 recent<br><sub>last seen 2026-09-10</sub> | **0**<br><sub>no posts in 7 days</sub> | **37** t/s<br>[llama.cpp](https://github.com/ggml-org/llama.cpp) · RTX 3090 · Q4_K_M | — | — | 18GB | Strongest local coding model (SWE-bench 77.2%). |
| [**Gemma 4 E2B**](https://huggingface.co/google/gemma-4-E2B)<br><sub>gemma-4-E2B · 2B · Gemma</sub> | 🕑 recent<br><sub>last seen 2026-09-05</sub> | **0**<br><sub>no posts in 7 days</sub> | — | — | **9** t/s<br>[LiteRT](https://github.com/google-ai-edge/LiteRT) · Raspberry Pi 5 (CPU) · 1432 MB peak RAM | 2GB | Google's compact Gemma 4 edge model runs on-device via LiteRT on a Raspberry Pi 5: 99 tok/s prefill and 9 tok/s decode at 1432 MB peak RAM, fully offline. |
| [**Muse Glimmer 30B**](https://huggingface.co/meta-models/Muse-Glimmer-30B)<br><sub>Muse-Glimmer-30B · 30B · Apache 2.0</sub> | 💤 stale<br><sub>last seen 2026-08-10</sub> | **0**<br><sub>no posts in 7 days</sub> | **233** t/s<br>[llama.cpp](https://github.com/ggml-org/llama.cpp) · RTX 5090 · 4-bit | **50** t/s<br>[llama.cpp](https://github.com/ggml-org/llama.cpp) · M5 Max (Apple Silicon) · 4-bit | — | 24GB | Meta Superintelligence 30B agentic model, Apache 2.0. Fits 24/32 GB at 4-bit (<20GB weights + KV + vision + spec draft). DFlash drafter gives 3.1x decode on RTX 5090. |
| [**DeepSeek R1 1.5B**](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B)<br><sub>DeepSeek-R1-Distill-Qwen-1.5B · 1.5B · MIT</sub> | 💤 stale<br><sub>last seen 2026-06-25</sub> | **0**<br><sub>no posts in 7 days</sub> | — | — | **4** t/s<br>[Ollama](https://github.com/ollama/ollama) · Raspberry Pi 4B 2GB (CPU) · quantized | 2GB | DeepSeek R1 1.5B served fully offline by Ollama on a 7-year-old Raspberry Pi 4B at 4 tok/s under 5 W, no network or API needed. |

---

## 🧭 Which inference engine runs what

Best measured t/s per model on each engine (🟦 CUDA · 🟩 Metal · 🟨 CPU). Only engines with at least one measurement are shown.

| Model | [llama.cpp](https://github.com/ggml-org/llama.cpp) | [Ollama](https://github.com/ollama/ollama) | [MLX](https://github.com/ml-explore/mlx) | [TensorFold](https://github.com/ashhart/TensorFold) | DeepSeekHarness | [LiteRT](https://github.com/google-ai-edge/LiteRT) | [llama.cpp (PrismML fork)](https://github.com/PrismML-Eng/llama.cpp) | [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) | quillan.cpp | [SGLang](https://github.com/sgl-project/sglang) | [Strata](https://github.com/Niko1221/Strata) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Qwen3.8-27B** | 🟦 43.7 | — | — | 🟩 189 | — | — | — | — | — | 🟦 44 | — |
| **Bonsai 2 27B** | — | — | — | — | — | — | 🟦 143 | 🟩 237 | — | — | — |
| **Nemotron 3.5 Lightning 30B** | — | — | — | 🟩 206 | — | — | — | — | — | — | — |
| **RavenX-Conjecture-Qwen3-8B-MLX** | — | — | 🟩 42 | — | — | — | — | — | — | — | — |
| **GLM-5.3** | — | — | — | — | 🟨 18 | — | — | — | — | — | — |
| **Qwen3.8-Flash-Next 125B** | — | — | — | — | — | — | — | — | — | — | 🟦 93 |
| **Ornith 1.5 35B** | — | — | 🟩 50 | — | — | — | — | — | — | — | — |
| **Qwen3 8B** | — | 🟦 100 | — | — | — | — | — | — | — | — | — |
| **Gemma 4 12B** | 🟦 99.7<br>🟩 49.67 | — | — | — | — | — | — | — | — | — | — |
| **Qwen3 14B** | — | 🟦 65 | — | — | — | — | — | — | — | — | — |
| **Quillan-Ronin** | — | — | — | — | — | — | — | — | 🟨 43 | — | — |
| **Qwen 3.6 27B** | 🟦 37 | — | — | — | — | — | — | — | — | — | — |
| **Gemma 4 E2B** | — | — | — | — | — | 🟨 9 | — | — | — | — | — |
| **Muse Glimmer 30B** | 🟦 233<br>🟩 50 | — | — | — | — | — | — | — | — | — | — |
| **DeepSeek R1 1.5B** | — | 🟨 4 | — | — | — | — | — | — | — | — | — |

---

# 🟦 CUDA — NVIDIA GPUs (8–48 GB)

| Model | Params | License | VRAM | Peak t/s | Measurements (engine · t/s · hardware · quant · date) |
|---|---|---|---|---|---|
| [**Muse Glimmer 30B**](https://huggingface.co/meta-models/Muse-Glimmer-30B) | 30B | Apache 2.0 | 24GB | 233 | [llama.cpp](https://github.com/ggml-org/llama.cpp) **233** · RTX 5090 · 4-bit · 2026-08-10 |
| [**Bonsai 2 27B**](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 27B | Apache 2.0 | 12GB | 143 | [llama.cpp (PrismML fork)](https://github.com/PrismML-Eng/llama.cpp) **143** · RTX 5090 · ternary · 2026-09-18<br>[llama.cpp (PrismML fork)](https://github.com/PrismML-Eng/llama.cpp) **91** · RTX 4070 12GB · PTQ1_0-mtp-lean (6.3 GB) · 2026-09-26<br>[llama.cpp (PrismML fork)](https://github.com/PrismML-Eng/llama.cpp) **71** · RTX 5060 Ti 16GB · ternary, author conditions · 2026-10-01<br>[llama.cpp (PrismML fork)](https://github.com/PrismML-Eng/llama.cpp) **54.1** · RTX 5060 Ti 16GB · ternary, Japanese text · 2026-10-01<br>[llama.cpp (PrismML fork)](https://github.com/PrismML-Eng/llama.cpp) **50** · RTX 3060 12GB · MTP + kernel fix · 2026-09-26 |
| [**Qwen3 8B**](https://huggingface.co/Qwen/Qwen3-8B) | 8B | Apache 2.0 | 8GB | 100 | [Ollama](https://github.com/ollama/ollama) **100** · RTX 4060 · Q4_K_M · 2026-09-12 |
| [**Gemma 4 12B**](https://huggingface.co/google/gemma-4-12B-it) | 12B | Gemma | 9GB | 99.7 | [llama.cpp](https://github.com/ggml-org/llama.cpp) **99.7** · RTX 4090 Laptop · Q4 · 2026-09-19 |
| [**Qwen3.8-Flash-Next 125B**](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 125B (MoE) | Apache 2.0 | 12GB | 93 | [Strata](https://github.com/Niko1221/Strata) **93** · RTX 5070 12GB · MoE, experts across GPU/RAM/SSD · 2026-10-01 |
| [**Qwen3 14B**](https://huggingface.co/Qwen/Qwen3-14B) | 14B | Apache 2.0 | 9GB | 65 | [Ollama](https://github.com/ollama/ollama) **65** · RTX 3090 · Q4_K_M · 2026-09-15 |
| [**Qwen3.8-27B**](https://huggingface.co/Qwen/Qwen3.8-27B) | 27B | Apache 2.0 | 16GB | 44 | [SGLang](https://github.com/sgl-project/sglang) **44** · DGX Spark · DFlash2 spec-decode draft head · 2026-09-29<br>[llama.cpp](https://github.com/ggml-org/llama.cpp) **43.7** · RTX 5090 Laptop · Q4_K_M · 2026-09-18<br>[SGLang](https://github.com/sgl-project/sglang) **12** · DGX Spark · no spec-decode · 2026-09-29 |
| [**Qwen 3.6 27B**](https://huggingface.co/Qwen/Qwen3.6-27B) | 27B | Apache 2.0 | 18GB | 37 | [llama.cpp](https://github.com/ggml-org/llama.cpp) **37** · RTX 3090 · Q4_K_M · 2026-09-10 |

---

# 🟨 CPU — no GPU

| Model | Params | License | VRAM | Peak t/s | Measurements (engine · t/s · hardware · quant · date) |
|---|---|---|---|---|---|
| [**Quillan-Ronin**](https://huggingface.co/CrashOverrideX/Quillan-Ronin) | 4.57B | apache-2.0 | 4GB | 43 | quillan.cpp **43** · PC (CPU) · BitNet 1.58-bit, 23-43 tok/s · 2026-09-24 |
| [**GLM-5.3**](https://huggingface.co/audnai/penclaw-GLM-5.3-abliterated) | 753B | Unknown | CPU | 18 | DeepSeekHarness **18** · CPU hybrid inference · NVFP4, 256K context, KV precache (170 t/s prefill) · 2026-10-01 |
| [**Gemma 4 E2B**](https://huggingface.co/google/gemma-4-E2B) | 2B | Gemma | 2GB | 9 | [LiteRT](https://github.com/google-ai-edge/LiteRT) **9** · Raspberry Pi 5 (CPU) · 1432 MB peak RAM · 2026-09-05 |
| [**DeepSeek R1 1.5B**](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B) | 1.5B | MIT | 2GB | 4 | [Ollama](https://github.com/ollama/ollama) **4** · Raspberry Pi 4B 2GB (CPU) · quantized · 2026-06-25 |

> CPU inference is **memory-bandwidth bound**. Use Q4 quant + a fast CPU build (AVX-512/AMX).

---

# 🟩 Metal — Apple Silicon (unified memory)

| Model | Params | License | VRAM | Peak t/s | Measurements (engine · t/s · hardware · quant · date) |
|---|---|---|---|---|---|
| [**Bonsai 2 27B**](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) | 27B | Apache 2.0 | 12GB | 237 | [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) **237** · Apple Silicon 16GB Mac · mlx.fast 4-bit · 2026-09-26 |
| [**Nemotron 3.5 Lightning 30B**](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16) | 30B (3B active) | OpenMDW 1.1 | 16GB | 206 | [TensorFold](https://github.com/ashhart/TensorFold) **206** · M5 Max · 4-bit MLX · 2026-09-30 |
| [**Qwen3.8-27B**](https://huggingface.co/Qwen/Qwen3.8-27B) | 27B | Apache 2.0 | 16GB | 189 | [TensorFold](https://github.com/ashhart/TensorFold) **189** · M5 Max · 4-bit MLX, DFlash2 drafter · 2026-09-30<br>[TensorFold](https://github.com/ashhart/TensorFold) **154** · M4 Max · 4-bit MLX, DFlash drafter · 2026-10-01<br>[TensorFold](https://github.com/ashhart/TensorFold) **124** · MacBook Pro M5 Max · 4-bit MLX · 2026-09-20 |
| [**Ornith 1.5 35B**](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B-MLX) | 35B (3B active) | Apache 2.0 | 16GB | 50 | [MLX](https://github.com/ml-explore/mlx) **50** · MacBook Pro M5 48GB · 4-bit MLX · 2026-09-29 |
| [**Muse Glimmer 30B**](https://huggingface.co/meta-models/Muse-Glimmer-30B) | 30B | Apache 2.0 | 24GB | 50 | [llama.cpp](https://github.com/ggml-org/llama.cpp) **50** · M5 Max (Apple Silicon) · 4-bit · 2026-08-10 |
| [**Gemma 4 12B**](https://huggingface.co/google/gemma-4-12B-it) | 12B | Gemma | 9GB | 49.67 | [llama.cpp](https://github.com/ggml-org/llama.cpp) **49.67** · Apple Silicon · Q4 · 2026-09-19 |
| [**RavenX-Conjecture-Qwen3-8B-MLX**](https://huggingface.co/deadbydawn101/RavenX-Conjecture-Qwen3-8B-MLX) | 8B | Apache 2.0 | 8GB | 42 | [MLX](https://github.com/ml-explore/mlx) **42** · M3 · MLX · 2026-09-29 |

> On Apple Silicon, **MLX** is the fastest engine; **TensorFold** adds speculative decoding (3–6x on memory-bound Macs); **MLX-fast Bonsai 2** (Layr-Labs/mlxfast-bonsai2-27b-engine) pushes Ternary Bonsai 2 27B to ~237 tok/s on a 16 GB Mac.

---

## ⚙️ Inference engine / server guide

| Engine | Backend | Models measured | Best for |
|---|---|---|---|
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | CUDA / CPU / Metal | 4 | Max control, custom quants |
| [llama.cpp (PrismML fork)](https://github.com/PrismML-Eng/llama.cpp) | CUDA / CPU / Metal | 1 | PrismML's llama.cpp fork (prism branch) — required for Ternary Bonsai 2 PTQ1_0/PQ2_0 (stock llama.cpp rejects them) |
| [Ollama](https://github.com/ollama/ollama) | CUDA / CPU / Metal | 3 | Easiest start |
| [FreeToken](https://github.com/FlashML-org/FreeToken) | CUDA | 0 | Big MoE on small GPUs |
| [vLLM](https://github.com/vllm-project/vllm) | CUDA | 0 | Production serving, high throughput |
| [SGLang](https://github.com/sgl-project/sglang) | CUDA | 1 | High-throughput serving |
| [MLX](https://github.com/ml-explore/mlx) | Metal | 2 | Fastest on Apple Silicon |
| [TensorFold](https://github.com/ashhart/TensorFold) | Metal | 2 | Speculative decoding on Mac, 3-6x |
| [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) | CUDA | 0 | Max NVIDIA perf |
| [LiteRT](https://github.com/google-ai-edge/LiteRT) | CUDA / Metal | 1 | Google local runtime |
| [Strata](https://github.com/Niko1221/Strata) | CUDA | 1 | Runs big MoE (Qwen3.8-Flash-Next 125B) on 8-48 GB NVIDIA GPUs; experts across GPU/RAM/SSD, speculative decoding ~1.6-1.8x |
| [MLX-fast (Bonsai 2)](https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine) | Metal | 1 | Speedup benchmark engine for Ternary Bonsai 2 27B on Apple Silicon; ~237 tok/s decode on 16 GB Mac (mlx.fast, Yukon/Layr-Labs) |
| [DFlash2](https://github.com/z-lab/dflash) | CUDA | 0 | Speculative decoding + context-lookup (Inco AI / syv-ai); Qwen3.8-27B ~118-133 tok/s chat, up to ~381 tok/s context-lookup on 24 GB RTX 3090 |
| [WebLLM](https://github.com/mlc-ai/web-llm) | CUDA / Metal | 0 | In-browser LLM inference accelerated with WebGPU (MLC-LLM). |

**Quick picks:** Ollama (just works) · llama.cpp (gaming laptop, max speed) · FreeToken (big MoE on small GPU) · MLX + TensorFold + MLX-fast (Mac) · Strata (125B MoE on 12–24 GB) · vLLM + DFlash2 (spec decode) · llama.cpp CPU (tiny/edge).

---

## How to contribute

- Update `data/models.json` (add/refresh a model row with real X-sourced engagement and per-engine t/s), then run `python3 scripts/update_trending.py` to regenerate the README.
- Include: full model name, HF link, license, params, type, VRAM tier, a **measured** t/s + **engine + hardware + quant**, and the source X post (a `…/status/<id>` URL, so engagement is counted once per post).
- Prefer numbers from real X benchmark posts over vendor claims. Data is **community-reported on X** — directional, not lab-grade; mark projections `(est)`.
- All changes go through a **feature branch + PR**; automation never pushes to/merges `master` directly.

## License

Apache License 2.0. See [LICENSE](LICENSE).
