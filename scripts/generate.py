#!/usr/bin/env python3
"""generate.py — render an Ideogram 4 caption via a local ComfyUI (core nodes only).

Builds the minimal dual-model Ideogram 4 graph (no custom nodes, no Gemma, no
mega-workflow) and submits it to ComfyUI's HTTP API. Supports text-to-image and
latent img2img.

Graph: UNETLoader(ideogram4) + UNETLoader(unconditional) -> ModelSamplingAuraFlow(shift 5)
-> CFGOverride(cfg 3 @ 70-100%) -> DualModelGuider(cfg 5, negative=ConditioningZeroOut)
-> SamplerCustomAdvanced(euler, simple) -> flux2 VAE. Prompt goes verbatim into
CLIPTextEncode on the qwen3vl-8b ideogram4 CLIP.

Usage:
    generate.py --prompt-file caption.json
    generate.py --prompt '<minified json>' --width 1344 --height 768
    generate.py --prompt-file cap.json --preset quality --seed 42
    generate.py --prompt-file cap.json --image input.png --denoise 0.6   # img2img
    generate.py --prompt-file cap.json --out ./renders --url http://localhost:8188

Presets (steps): turbo=12, default=28, quality=48.
Stdlib only. The model is NON-COMMERCIAL licensed — personal use.
"""

import argparse
import json
import mimetypes
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

PRESETS = {"turbo": 12, "default": 28, "quality": 48}

MODELS = {
    "unet": "ideogram4_fp8_scaled.safetensors",
    "unet_neg": "ideogram4_unconditional_fp8_scaled.safetensors",
    "clip": "qwen3vl_8b_fp8_scaled.safetensors",
    "vae": "flux2-vae.safetensors",
}


def die(msg, code=1):
    print(f"generate.py: error: {msg}", file=sys.stderr)
    sys.exit(code)


def api(url, path, payload=None, raw=False):
    req = urllib.request.Request(url + path)
    if payload is not None:
        req.data = json.dumps(payload).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            return data if raw else json.loads(data)
    except urllib.error.URLError as e:
        die(f"ComfyUI unreachable at {url} ({e}). Is ComfyUI running?")


def upload_image(url, path):
    """POST /upload/image multipart; returns server-side filename."""
    boundary = uuid.uuid4().hex
    fname = os.path.basename(path)
    ctype = mimetypes.guess_type(fname)[0] or "application/octet-stream"
    with open(path, "rb") as fh:
        filedata = fh.read()
    body = b""
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; "
             f"filename=\"{fname}\"\r\nContent-Type: {ctype}\r\n\r\n").encode() + filedata + b"\r\n"
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n").encode()
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(url + "/upload/image", data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=60) as r:
        info = json.loads(r.read())
    name = info["name"]
    if info.get("subfolder"):
        name = info["subfolder"] + "/" + name
    return name


def build_graph(prompt_text, width, height, steps, seed, denoise, input_image=None,
                sampler="euler", scheduler="simple", cfg_main=5.0, cfg_tail=3.0,
                tail_start=0.7, shift=5.0, prefix="ideogram4"):
    g = {
        "unet": {"class_type": "UNETLoader",
                 "inputs": {"unet_name": MODELS["unet"], "weight_dtype": "default"}},
        "unet_neg": {"class_type": "UNETLoader",
                     "inputs": {"unet_name": MODELS["unet_neg"], "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader",
                 "inputs": {"clip_name": MODELS["clip"], "type": "ideogram4", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": MODELS["vae"]}},
        "encode": {"class_type": "CLIPTextEncode",
                   "inputs": {"text": prompt_text, "clip": ["clip", 0]}},
        "zero": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["encode", 0]}},
        "msaf": {"class_type": "ModelSamplingAuraFlow",
                 "inputs": {"shift": shift, "model": ["unet", 0]}},
        "cfgo": {"class_type": "CFGOverride",
                 "inputs": {"model": ["msaf", 0], "cfg": cfg_tail,
                            "start_percent": tail_start, "end_percent": 1.0}},
        "guider": {"class_type": "DualModelGuider",
                   "inputs": {"model": ["cfgo", 0], "positive": ["encode", 0], "cfg": cfg_main,
                              "model_negative": ["unet_neg", 0], "negative": ["zero", 0]}},
        "sched": {"class_type": "BasicScheduler",
                  "inputs": {"model": ["msaf", 0], "scheduler": scheduler,
                             "steps": steps, "denoise": denoise}},
        "ksel": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": sampler}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "sampler": {"class_type": "SamplerCustomAdvanced",
                    "inputs": {"noise": ["noise", 0], "guider": ["guider", 0],
                               "sampler": ["ksel", 0], "sigmas": ["sched", 0],
                               "latent_image": ["latent", 0]}},
        "decode": {"class_type": "VAEDecode",
                   "inputs": {"samples": ["sampler", 0], "vae": ["vae", 0]}},
        "save": {"class_type": "SaveImage",
                 "inputs": {"images": ["decode", 0], "filename_prefix": prefix}},
    }
    if input_image:
        g["load"] = {"class_type": "LoadImage", "inputs": {"image": input_image}}
        g["scale"] = {"class_type": "ImageScale",
                      "inputs": {"image": ["load", 0], "upscale_method": "lanczos",
                                 "width": width, "height": height, "crop": "center"}}
        g["latent"] = {"class_type": "VAEEncode",
                       "inputs": {"pixels": ["scale", 0], "vae": ["vae", 0]}}
    else:
        g["latent"] = {"class_type": "EmptyFlux2LatentImage",
                       "inputs": {"width": width, "height": height, "batch_size": 1}}
    return g


def main():
    ap = argparse.ArgumentParser(description="Render an Ideogram 4 caption via local ComfyUI.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--prompt", help="caption JSON as a string (or plain text — JSON strongly preferred)")
    src.add_argument("--prompt-file", help="path to caption JSON file ('-' for stdin)")
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--preset", choices=PRESETS, default="default",
                    help="steps preset: turbo=12 default=28 quality=48")
    ap.add_argument("--steps", type=int, default=None, help="override preset steps")
    ap.add_argument("--seed", type=int, default=None, help="noise seed (default: random)")
    ap.add_argument("--image", default=None, help="input image path -> latent img2img")
    ap.add_argument("--denoise", type=float, default=0.6,
                    help="img2img strength 0-1 (only with --image; default 0.6)")
    ap.add_argument("--url", default=os.environ.get("COMFY_URL", "http://localhost:8188"))
    ap.add_argument("--out", default=".", help="directory to save the result image")
    ap.add_argument("--timeout", type=int, default=1200,
                    help="seconds to wait for the render (first run loads ~27GB; default 1200)")
    ap.add_argument("--prefix", default="ideogram4", help="SaveImage filename prefix")
    args = ap.parse_args()

    if args.prompt_file:
        prompt_text = sys.stdin.read() if args.prompt_file == "-" else open(args.prompt_file, encoding="utf-8").read()
    else:
        prompt_text = args.prompt
    prompt_text = prompt_text.strip()
    # If it's JSON, re-minify (canonical serialization the model expects)
    try:
        prompt_text = json.dumps(json.loads(prompt_text), separators=(",", ":"), ensure_ascii=False)
    except json.JSONDecodeError:
        print("note: prompt is not JSON — plain text works but quality and safety-filter "
              "false positives are worse; prefer a validated JSON caption", file=sys.stderr)

    steps = args.steps or PRESETS[args.preset]
    seed = args.seed if args.seed is not None else random.randrange(2**48)
    denoise = args.denoise if args.image else 1.0
    if args.width % 16 or args.height % 16:
        print("warn: width/height not multiples of 16 — may degrade/fail", file=sys.stderr)

    input_name = None
    if args.image:
        if not os.path.isfile(args.image):
            die(f"no such image: {args.image}")
        input_name = upload_image(args.url, args.image)
        print(f"uploaded input image as {input_name!r}", file=sys.stderr)

    graph = build_graph(prompt_text, args.width, args.height, steps, seed, denoise,
                        input_image=input_name, prefix=args.prefix)

    client_id = uuid.uuid4().hex
    resp = api(args.url, "/prompt", {"prompt": graph, "client_id": client_id})
    if "error" in resp:
        die(f"ComfyUI rejected the graph: {json.dumps(resp, indent=2)[:2000]}")
    pid = resp["prompt_id"]
    mode = f"img2img denoise={denoise}" if args.image else "txt2img"
    print(f"queued {pid}  [{mode}  {args.width}x{args.height}  {steps} steps  seed {seed}]",
          file=sys.stderr)

    t0 = time.time()
    while True:
        time.sleep(2.0)
        hist = api(args.url, f"/history/{pid}")
        if pid in hist:
            entry = hist[pid]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                msgs = [m for m in status.get("messages", []) if m[0] == "execution_error"]
                die(f"execution error: {json.dumps(msgs, indent=2)[:2000]}")
            outputs = entry.get("outputs", {})
            if outputs:
                break
        if time.time() - t0 > args.timeout:
            die(f"timed out after {args.timeout}s (queue still running — check ComfyUI)")

    os.makedirs(args.out, exist_ok=True)
    saved = []
    for node_out in outputs.values():
        for img in node_out.get("images", []):
            q = urllib.parse.urlencode({"filename": img["filename"],
                                        "subfolder": img.get("subfolder", ""),
                                        "type": img.get("type", "output")})
            data = api(args.url, f"/view?{q}", raw=True)
            dest = os.path.join(args.out, img["filename"])
            with open(dest, "wb") as fh:
                fh.write(data)
            saved.append(dest)
    el = time.time() - t0
    for p in saved:
        print(p)
    print(f"done in {el:.1f}s — seed {seed}. Read the image to verify it matches the caption.",
          file=sys.stderr)


if __name__ == "__main__":
    main()
