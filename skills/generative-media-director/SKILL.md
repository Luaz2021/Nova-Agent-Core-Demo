---
name: generative-media-director
description: "Direccion y generacion de imagenes, videos, style frames y anuncios sociales con flujos multi-proveedor e IA."
---

# Generative Media Director

## Workflow

1. Define the job:
   - audience
   - surface
   - output format
   - desired viewer action
   - brand role

2. Decide the source of truth:
   - product UI: code and browser capture
   - static visual direction: imagegen/GPT Image
   - cinematic generated clip: Sora, Grok, Veo, Luma, Runway, or Higgsfield
   - exact typography/layout/video package: Remotion
   - export/compression: ffmpeg

3. Write the still-frame prompt before the video prompt.

4. Generate or select style frames.

5. Write the video prompt:
   - source frame
   - camera
   - subject motion
   - environmental motion
   - audio
   - beginning/middle/end
   - constraints

6. Route providers:
   - Sora for OpenAI-first cinematic video and image-to-video.
   - Veo for high-fidelity controlled video, native audio, first/last-frame workflows.
   - Grok Imagine for fast social/audio-synced clips and stylized tests.
   - Luma for cinematic exploration and creative-agent workflows.
   - Runway for production editing and existing-video transformation.
   - Higgsfield for creator/social/ad variants.
   - Remotion for final deterministic finishing.

7. Finish:
   - captions
   - title cards
   - logo lockups
   - CTA
   - aspect-ratio variants
   - GIF/MP4/WebM exports

8. QA:
   - first frame works as still
   - crop works on target channels
   - text is readable
   - loop resolves cleanly
   - audio is intentional
   - file size is acceptable
   - provenance is complete

## Image Prompt Shape

```text
Use case:
Asset type:
Primary request:
Input images:
Scene/backdrop:
Subject:
Style/medium:
Composition/framing:
Lighting/mood:
Color palette:
Materials/textures:
Text (verbatim):
Constraints:
Avoid:
```

## Video Prompt Shape

```text
Output:
Aspect ratio:
Duration:
Provider candidates:
Source frame:
Subject:
Setting:
Camera:
Subject motion:
Environmental motion:
Audio:
Beginning:
Middle:
End:
Style:
Constraints:
Avoid:
```

## Output Shape

Return:

- creative diagnosis
- recommended workflow
- provider routing
- still-frame prompt
- video prompt
- finishing plan
- QA checklist
- provenance template

## Free Generative Arsenal & Hybrid Workflow (Zero Cost / Free Tiers)

Consult references/free-generative-arsenal.md for zero-cost and daily renewable providers:
- Video B-Roll: PixVerse, Kling AI, Hailuo / Minimax, Dreamina, Luma Dream Machine, Viggle.
- Images / Backgrounds: Pollinations.ai (FLUX direct REST API without API key), Cloudflare Workers AI.
- Voice / Audio: edge-tts (Microsoft Neural Voices CLI in local, unlimited & zero tokens, outputs .vtt timestamps) and ElevenLabs free tier.
- Music / SFX: Suno, Udio, Freesound.
- Scripts & Transcription: Groq (Llama 3.3 70B & Whisper large-v3), Google AI Studio.
