# HANDOFF — ideogram4 for any agent

Written **for an AI agent** (not a human operator). If you can run shell
commands and read images, this is how you generate images with a local
Ideogram 4 through ComfyUI. Claude Code users have a tailored entry in
`SKILL.md`; humans should read `README.md`. This file stands alone.

## The capability

Ideogram 4 wants **structured JSON captions** (schema in
`references/schema.md`). YOU write that JSON from the user's intent — there is
no helper model. Then:

```bash
# 1. validate (returns minified caption on stdout; nonzero exit on schema errors)
python3 scripts/validate.py caption.json

# 2. render (text-to-image)
python3 scripts/generate.py --prompt-file caption.json \
    --width 1024 --height 1024 --preset default --out ./renders
# └ prints the saved PNG path(s) on stdout

# 2b. img2img instead: describe the FULL target image in the caption, then
python3 scripts/generate.py --prompt-file caption.json --image in.png --denoise 0.6

# 3. read the PNG with your image-input tool, compare vs the caption, iterate.
```

## Contract details

- **Prerequisites:** `python3` (stdlib only) + a running ComfyUI (≥ Ideogram 4
  day-0 support) with the 5 model files installed (`ideogram4_fp8_scaled`,
  `ideogram4_unconditional_fp8_scaled`, `qwen3vl_8b_fp8_scaled`, `flux2-vae`).
  Endpoint defaults to `http://localhost:8188`; override with `--url` or `COMFY_URL`.
- **Knowledge files:** `references/schema.md` (exact format — key orders are
  load-bearing), `references/craft.md` (bbox semantics, element granularity,
  i2i denoise ranges, block-card triage), `references/genres.md` (vocab).
  Read schema.md + craft.md before writing your first caption.
- **Iteration:** keep `--seed` fixed while adjusting composition; randomize for
  final picks. `--preset turbo` (12 steps) for drafts, `quality` (48) for finals.
- **Failure triage:** gray "blocked by safety filter" card → validate the
  caption first (schema errors render as that same card); `generate.py` dies
  with the ComfyUI node error on graph problems; timeout default 1200s covers
  the first ~27GB model load.
- **License:** weights are non-commercial. Refuse commercial/production asks.

## Tool-name mapping

| Need | Claude Code | Other runtimes |
|---|---|---|
| Run scripts | `Bash` | your shell/exec tool |
| See the render | `Read` (PNG path) | your image-input mechanism |
