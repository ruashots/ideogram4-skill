# Composition craft — what makes Ideogram 4 captions actually good

Schema correctness is table stakes (see `schema.md`). Image quality comes from
the decisions below. Sources: official magic-prompt `v1.txt`, community
behavioral research, and dissected production workflows.

## Element granularity — the #1 LLM mistake

**Single subject = single element.** One person, animal, vehicle, building,
plant, machine = ONE `obj`. Parts (limbs, wheels, windows, petals) are
attributes inside that element's `desc`, never separate elements.

- FORBIDDEN: a bee as 8 elements (thorax/wings/legs…), a person as 7, a car as 6.
- Multiple distinct subjects (a person AND a dog; three runners) → one element each.
- **Transparent enclosure + featured contents = ONE element** (snow globe, aquarium, display case).
- **Configured parts + revealed interior = ONE element** (car with open door, machine with raised hood).
- Test: *part-of-one-thing → that thing's desc. Separate thing → its own element.*

Default density: **4–7 elements**. Fewer for clean/minimal; more only for
posters/UI/text-heavy layouts. ~60 elements physically place fine, but the
2048-token cap is the real limit — budget tokens, not element count.

**Counts inside a desc are unreliable.** "three coins in her hand" or "three
lanterns" inside one element's desc renders as "some" — sub-element counting is
the model's known frontier (verified in a 10-element stress test where every
element placed correctly but small-item counts drifted). If an exact count
matters, **promote each countable to its own element with its own bbox**;
otherwise write quantities loosely ("a few", "a cluster of").

## bbox semantics (behavioral, not documented)

- A bbox acts as **midpoint placement + approximate extent hint**, NOT a hard
  stretch-to-fit box. The model centers the subject there at roughly that scale;
  it won't distort to fill the box exactly.
- **Element array order = z-order.** Earlier ≈ farther/behind, later ≈ nearer/in
  front. Order background-ish elements first, foreground last.
- bbox is optional — omit it when placement doesn't matter and the model
  composes freely (often better for single-subject images).
- Make bboxes agree with the prose: "on the left" → low x values; "foreground" →
  larger box, lower in frame; "wide shot" → smaller subject box, more
  background; "close-up/macro" → box fills most of the canvas.

### Placement cheat table (0–1000, [y1,x1,y2,x2])

| Intent | bbox |
|---|---|
| Centered portrait close-up | `[40,220,960,780]` |
| Centered medium shot | `[120,250,980,750]` |
| Full body centered | `[80,320,980,680]` |
| Subject on left / right third | `[100,80,950,480]` / `[100,520,950,930]` |
| Two characters facing each other | L `[120,80,950,460]` + R `[120,540,950,920]` |
| Product centered | `[180,240,850,760]` |
| Landscape horizon band | `[380,0,520,1000]` |
| Title text top / bottom center | `[40,120,190,880]` / `[780,120,940,880]` |
| Small logo top corner | `[30,40,130,180]` |
| Foreground object across bottom | `[720,0,1000,1000]` |

Adapt for the actual aspect ratio — these assume roughly square; in 9:16 stretch
y-ranges, in 16:9 stretch x-ranges.

## desc checklists (what to actually describe)

- **Characters**: identity, pose, body orientation, expression, gaze, action,
  clothing + materials, hair, accessories, relationship to camera and to other
  elements, lighting interaction.
- **Products**: type, shape, material, surface finish, angle, reflections,
  scale, presentation.
- **Environment pieces**: position in frame, size, material, texture, light
  interaction, perspective.
- **Effects** (fire, magic, neon): shape, color, intensity, transparency, glow,
  direction, how it lights nearby surfaces.
- **Text elements**: exact string in `text` (verbatim, preserve the user's
  casing/characters); `desc` covers font style/weight/size/color/placement/
  effects. Big readable text wants a big bbox + high contrast. No text elements
  unless the image type needs them or the user asked. "no text" → zero text elements.

## Palettes

- Global: 3–8 colors normally (16 max for complex scenes). Include background,
  subject, highlight, shadow, accent. Dark scene → include the darks.
- Per element: 2–5 colors describing THAT element, harmonizing with the global.
- Uppercase `#RRGGBB` only.

## Negative constraints

No `negative_prompt` key exists. Fold exclusions into prose naturally:
"a clean polished sword, no blood or gore visible" / "clean minimal studio
background, no clutter, no extra objects".

## Block cards & safety

A gray "Image blocked by safety filter" card is returned for NSFW — but the
**same card appears for schema/format errors**, and false-positive rates are
officially higher for non-JSON/malformed prompts. So when you see a block:
1) `validate.py` the caption, 2) check it's minified proper JSON, 3) only then
suspect actual content filtering. The open local weights still contain this
baked-in filter; a low refusal-card rate is normal for borderline content.

## img2img (latent)

There is no edit-instruction mode. i2i = VAE-encode the input image and
re-denoise toward the caption:

- The caption must describe the **full desired final image** (same format as
  t2i), NOT the change ("make the hat red" fails; describe the person *with*
  the red hat and everything else you want kept).
- The input image contributes structure only through the latent; **the LLM/text
  side never sees it.** You must describe what's in it that should survive.
- `denoise` is the strength knob: **0.35–0.45** subtle restyle · **0.55–0.65**
  real changes, composition kept · **0.75+** mostly new image guided by old layout.
- Masks/inpainting: not supported in this graph — a painted mask is silently ignored.
- **Identity drifts.** i2i preserves composition and rough likeness, but a real
  person's face is NOT faithfully kept at denoise ≥0.5 (verified: 8-view
  turnaround sheet at 0.55 → "same family, different person"). Targeted region
  edits (e.g. recolor one garment) also only partially take — the latent fights
  large dark/light priors. For face-faithful work on a specific person, use a
  character LoRA (Ideogram 4 LoRAs exist; needs LoraLoaderModelOnly in the
  graph) or an identity-conditioned model — text+latent alone won't do it.
- **Don't expect flat backgrounds to repaint preferentially.** Verified failure:
  portrait on a plain gray studio backdrop, captioned into a spaceship cockpit —
  at denoise 0.6 the gray backdrop SURVIVED almost untouched (large uniform
  regions are strong latent structure too) while the face still drifted; the
  scene only formed at 0.75 with identity mostly gone. Scene-swap-around-a-person
  has no good denoise value — it's a LoRA/instruct-edit job, full stop.

## Iteration loop

Generate → **read the output image** → compare against the caption element by
element → fix the caption (placement? missing element? palette drift?) →
re-validate → regenerate. Keep the seed fixed while iterating composition;
randomize once composition is right and you're fishing for the best take.


## The "football" curse (hard-won, three strikes)

In any US-adjacent or northern-Mexico context (norteño, carne asada, backyard,
tailgate vibes), the words "football" / "football jersey" / "football scarf"
resolve AMERICAN: pigskin balls, shoulder-pad jerseys. Struck three times in
one day (eagle poster ball, barrio kid ball, norteño/asada jerseys).
RULE: for fútbol content always write "classic black-and-white hexagonal-panel
soccer ball", "short-sleeved soccer kit jersey, no shoulder pads", "soccer fan
scarf" — and put `american football, rugby ball` in the negative prompt.


## Pose control via limb-bbox decomposition (discovered 2026-06-11)

Pose WORDS don't move limbs reliably ("knee bent", "legs scissored" get averaged
away); bbox GEOMETRY does. For animation frames / distinct poses of the same
character, split each figure into 2+ elements — torso+head box and a legs box —
and encode the pose in the BOX SHAPES: a wide+low legs box forces a stride,
a narrow legs box forces legs-together, raising the torso box ~40/1000 creates
the walk bounce. Five same-size single-element figures in bands = five near
-identical poses (failed walk cycle); three figures with torso/legs boxes shaped
per phase = a real contact/passing/contact cycle (worked first try).
Fewer, larger frames beat many small ones for pose fidelity. Character identity
stays consistent across frames within one generation; style may still drift
from a separately generated reference (see the football curse note: every
generation is its own casting call).