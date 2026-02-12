# MLX Optimization for M1-M4 Macs

## Quick Setup for Family & Friends

1. Open Executive Assistant app
2. Click **Settings** (top right)
3. Change "AI Model" to: **Llama 3.2 MLX (M1-M4 Optimized) ⚡**
4. Click **Save Settings**
5. Reload page

**Result:** 3-5x faster responses using your Mac's Neural Engine!

---

## What is MLX?

MLX is Apple's machine learning framework optimized for M1-M4 chips.
Uses the Neural Engine instead of CPU for much faster AI processing.

---

## Install MLX Models

```bash
ollama pull llama3.2:latest-mlx
ollama pull qwen2.5:7b-instruct-mlx

---

## Model Recommendations

- **Mom (75):** llama3.2:latest-mlx (simple, fast)
- **Nephew (15):** llama3.2:latest-mlx or codellama-mlx
- **Power users:** llama3.2:70b-mlx (most capable)

---

## Performance

| Setup | Speed |
|-------|-------|
| CPU only | 1x |
| MLX + Neural Engine | 3-5x faster ⚡ |
