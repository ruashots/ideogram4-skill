# Per-genre guidance + vocabulary

Pick the variant first (photo vs non-photo, see `schema.md`), then apply the
genre notes. Vocab lists are starters, not limits.

## Photo variant genres
Realistic/cinematic shots, portraits, fashion, product photography, documentary,
editorial, macro, food, architecture, film stills, realistic fantasy/sci-fi/horror.

- `medium: "photograph"`, believable camera language, real textures, physically
  plausible anatomy/props unless surrealism is requested.
- `aesthetics` vocab: cinematic, hyper-realistic, editorial, documentary,
  commercial, luxury, gritty, raw, moody, atmospheric, high/low contrast, clean,
  minimal, dreamlike, dramatic, glossy, vintage, analog film, heroic, brutalist,
  futuristic, cozy, sterile, elegant, painterly realism.
- `lighting` recipe: source + direction + quality + color + shadows/highlights
  (+ rim/fill/bounce, haze, flare). e.g. "large softbox key from upper left,
  cool blue rim light behind, subtle bounce fill, soft cinematic shadows" ·
  "warm golden-hour backlight, long soft shadows, glowing haze, gentle flare" ·
  "cold fluorescent overheads, harsh under-eye shadows, sterile metal reflections".
- `photo` recipe: lens + aperture/DoF + focus + angle/framing (+ grain, motion
  blur, film-stock feel). e.g. "85mm portrait lens, shallow DoF, sharp focus on
  the eyes, creamy bokeh, eye-level" · "24mm wide-angle, low-angle, deep focus,
  dramatic foreground exaggeration" · "35mm film still, slight grain, handheld".

## Non-photo variant genres

### Anime / manga / illustration
Describe linework, rendering, shading, eye style, hair shape, silhouette, color
blocking. `art_style` e.g. "semi-realistic anime illustration, expressive eyes,
polished rendering, clean linework, soft gradients".

### Concept art / painting
"cinematic fantasy concept art, painterly brushwork, detailed costume design,
dramatic atmospheric depth" · "dark surreal oil painting, visible brush texture,
symbolic composition, muted tones".

### 3D / product render
`medium: "3D render"` or `"product render"`. Describe materials, shaders,
surface finish, reflections, bevels; studio vs environmental lighting; clear
camera perspective. "high-end 3D render, glossy materials, realistic
reflections, bevelled edges, studio lighting".

### Graphic design / logos / posters / covers / UI
`medium`: `"graphic_design"`, `"logo design"`, `"poster_design"`, `"packaging
design"`, `"book cover design"`, `"album cover design"`, `"UI design"`.
- Layout hierarchy first; text as separate `text` elements with clean bboxes.
- Deliberate negative space; describe alignment, margins, balance.
- Ideogram's text rendering is best-in-class — exploit it, but keep strings
  short and high-contrast for guaranteed legibility.
- "flat vector design, bold geometric shapes, clean sans-serif typography,
  balanced negative space" · "vintage poster illustration, screen-print texture,
  limited palette" · "comic book cover art, heavy ink outlines, halftone texture".

### Product images
Product = the main element: exact angle, material, surface finish, reflections,
shadows. Clean background unless lifestyle is asked. Label text only if needed.

### Character design
Face, hair, clothing (+materials/colors), pose, expression, accessories,
silhouette, personality; framing per request (full body / half / close-up);
powers/weapons/symbolic items explicitly.

### Scenes / environments
Rich `background`; promote major environmental features to elements when they
matter; foreground objects for depth; atmosphere/weather/texture; distant
shapes for scale.

## Steps presets (sampling quality)

| Preset | Steps | Use |
|---|---|---|
| TURBO | 12 | fast drafts, composition checks |
| DEFAULT | 20–28 | good everyday quality |
| QUALITY | 48 | final renders |
