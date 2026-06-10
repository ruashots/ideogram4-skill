# ideogram4 skill

Teach an AI agent to drive **Ideogram 4** (the open-weight text-to-image model)
**locally through ComfyUI** — writing the model's structured JSON captions
directly, with no helper LLM in the loop.

Ideogram 4 is prompted with a JSON schema (regions, bboxes, palettes, literal
text) rather than plain language. Most workflows bolt on a local Gemma model to
convert natural language → JSON. If an agent (Claude, or any capable LLM) is
already driving, that middleman is redundant: the agent writes better JSON,
sees the conversation context, and — unlike the helper model — can **look at
the output** and iterate.

## What's here

| File | Purpose |
|---|---|
| `SKILL.md` | Claude Code skill entry — the write→validate→generate→inspect loop |
| `HANDOFF.md` | Agent-agnostic version of the same contract |
| `references/schema.md` | The canonical caption schema (key orders, bbox format, palettes) |
| `references/craft.md` | Composition craft: element granularity, bbox behavioral semantics, z-order, img2img denoise ranges, block-card triage |
| `references/genres.md` | Per-genre vocabulary (photo vs art_style variants) |
| `scripts/validate.py` | Schema validator/canonicalizer (stdlib; CaptionVerifier-parity) |
| `scripts/generate.py` | Renders via ComfyUI's HTTP API with a minimal **core-nodes-only** dual-model graph (t2i + latent i2i) |

## Requirements

- A running [ComfyUI](https://github.com/comfyanonymous/ComfyUI) with Ideogram 4
  day-0 support and the model files from
  [Comfy-Org/Ideogram-4](https://huggingface.co/Comfy-Org/Ideogram-4) +
  qwen3vl text encoder + flux2 VAE (~36GB total, 24GB+ VRAM recommended).
- `python3` — scripts are stdlib-only.

## Quick start

```bash
python3 scripts/validate.py my_caption.json          # schema check
python3 scripts/generate.py --prompt-file my_caption.json --out renders/
python3 scripts/generate.py --prompt-file cap.json --image photo.png --denoise 0.6  # img2img
```

## License note

The Ideogram 4 **weights are licensed non-commercial** (the inference code is
Apache-2.0). This skill is for personal/research use of the model; commercial
use of outputs requires a license from Ideogram. This repo contains no model
weights and no Ideogram code — only original documentation and glue scripts (MIT).
