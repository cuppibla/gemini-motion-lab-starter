from typing import Any


# Location/theme metadata — background environment descriptions for Veo
_LOCATION_META: dict[str, dict[str, str]] = {
    "lunar-surface": {
        "name": "Lunar Surface",
        "background": (
            "on the dramatic surface of the Moon at the edge of a crater, photorealistic grey "
            "lunar regolith terrain with crisp texture, vivid blue-silver Earth rising on the horizon "
            "with cloud formations visible, breathtaking star field, cosmic dust particles catching "
            "silver light, dramatic rim lighting casting long sharp shadows across crater walls, "
            "blue-white volumetric glow from Earth's reflected light"
        ),
    },
    "golden-desert": {
        "name": "Golden Desert",
        "background": (
            "in a sweeping epic desert canyon with ancient stone ruins partially buried in golden "
            "sand dunes, blazing golden hour sunlight with dramatic god-rays piercing through dusty air, "
            "warm amber and orange tones, vivid sky gradient from deep cerulean blue to amber at the "
            "horizon, sand particles suspended and catching golden light, epic scale with towering "
            "cliff formations in the distance"
        ),
    },
    "neon-city": {
        "name": "Neon City",
        "background": (
            "on a rain-slicked futuristic cyberpunk city street at night, vivid magenta and cyan neon "
            "signs reflecting on wet asphalt, holographic billboards broadcasting above towering "
            "skyscrapers, flying vehicles leaving light trails, rain falling in shafts of neon-lit light, "
            "electric blue and hot pink light reflections shimmering in puddles, energetic and alive"
        ),
    },
    "space-station": {
        "name": "Space Station",
        "background": (
            "inside a sleek futuristic orbital space station with large panoramic curved viewports "
            "showing Earth below and a brilliant star field, vibrant electric blue holographic interface "
            "panels floating in zero gravity, clean white and silver metallic surfaces with dramatic rim "
            "lighting, Earth's glow casting soft blue-white light through the viewports"
        ),
    },
    "enchanted-forest": {
        "name": "Enchanted Forest",
        "background": (
            "in an ancient mystical forest with enormous gnarled trees reaching high, vivid bioluminescent "
            "emerald and teal glowing plants and mushrooms, thousands of golden fireflies drifting between "
            "massive tree trunks, dramatic golden-green light shafts filtering through a dense forest "
            "canopy, rich saturated deep emerald and amber tones, soft volumetric mist near the ground"
        ),
    },
    "underwater-palace": {
        "name": "Underwater Palace",
        "background": (
            "inside a grand ancient palace submerged underwater, ornate stone columns and archways with "
            "intricate carvings, brilliant turquoise and aqua water with perfect volumetric light caustics "
            "shimmering across stone surfaces, golden shafts of sunlight streaming diagonally from the "
            "surface above, vivid colorful tropical coral and bioluminescent sea plants growing on ancient "
            "stone, dramatic underwater atmospheric perspective with depth haze"
        ),
    },
}

_DEFAULT_BACKGROUND = "a clean neutral studio background with soft ambient lighting"

# Style metadata used when building Veo prompts
_STYLE_META: dict[str, dict[str, str]] = {
    "pixel-hero": {
        "name": "Pixel Hero",
        "camera": "medium shot",
        "description": "animated retro 16-bit pixel art video game character, blocky pixelated body, bright primary colors, clearly NOT a real human",
        "atmosphere": "vivid pixel art colors, sharp pixel edges, retro arcade game aesthetic, pixelated animation style",
    },
    "cyber-nova": {
        "name": "Cyber Nova",
        "camera": "low-angle medium shot",
        "description": "animated futuristic sci-fi character in sleek silver nano-tech power armor with glowing blue energy core, holographic visor, clearly NOT a real human",
        "atmosphere": "neon blue glow, dark background, holographic light trails, cinematic volumetric lighting, sci-fi animated character",
    },
    "watercolor-dream": {
        "name": "Watercolor Dream",
        "camera": "soft front-facing medium shot",
        "description": "animated watercolor illustration character, soft painterly brushstrokes, dreamy pastel figure with flowing edges, clearly an illustration NOT a real human",
        "atmosphere": "soft pastel watercolor washes, painterly brushstroke edges, dreamy ethereal illustrated aesthetic",
    },
    "3d-figurine": {
        "name": "3D Figurine",
        "camera": "front-facing medium shot",
        "description": "animated 3D rendered chibi figurine character with oversized head and small body, smooth matte plastic texture, big expressive eyes, clearly a toy figure NOT a real human",
        "atmosphere": "smooth clay-like plastic rendering, soft studio lighting, pastel color palette, blind box collectible toy aesthetic",
    },
    "manga-ink": {
        "name": "Manga Ink",
        "camera": "medium shot",
        "description": "animated black and white manga illustration character, bold confident ink strokes, high contrast pure B&W with screentone shading, clearly a manga drawing NOT a real human",
        "atmosphere": "pure black and white ink art, halftone screentone shading, Japanese manga aesthetic, elegant pen and ink animation",
    },
    "brick-build": {
        "name": "Brick Build",
        "camera": "front-facing medium shot",
        "description": "animated character made entirely of colorful interlocking plastic building bricks, blocky geometric form with visible brick studs, clearly a toy brick figure NOT a real human",
        "atmosphere": "colorful plastic bricks with realistic sheen, visible studs and block edges, toy product aesthetic, stop-motion toy animation style",
    },
}

_DEFAULT_STYLE = _STYLE_META["pixel-hero"]


def build_video_prompt(
    motion_analysis: dict[str, Any],
    avatar_style: str,
    location_theme: str = "",
) -> str:
    """Construct a Veo generation prompt from motion analysis, avatar style, and location theme."""
    meta = _STYLE_META.get(avatar_style, _DEFAULT_STYLE)
    style_name = meta["name"]
    description = meta["description"]
    atmosphere = meta["atmosphere"]
    camera_angle = motion_analysis.get("camera_angle") or meta["camera"]
    veo_prompt_from_gemini = motion_analysis.get("veo_prompt") or "fluid, expressive movement"
    overall_style = motion_analysis.get("overall_style") or "smooth and fluid"

    location = _LOCATION_META.get(location_theme)
    background = location["background"] if location else _DEFAULT_BACKGROUND

    phases = motion_analysis.get("phases", [])
    choreography = _build_choreography(phases)

    prompt = (
        f"Animation only, no real humans. "
        f"A {description} performs the following movement sequence. "
        f"CRITICAL: The first 3 seconds of this video must faithfully replicate the exact choreography below — "
        f"matching each body part, direction, timing, and spatial range as precisely as possible. "
        f"Begin the movement immediately from the very first frame with no delay or idle pause. "
        f"{veo_prompt_from_gemini} "
    )

    if choreography:
        prompt += (
            f"Exact movement timing for the first 3 seconds (replicate precisely): {choreography} "
        )

    prompt += (
        f"The motion quality is {overall_style}. "
        f"Setting: {background}. "
        f"{camera_angle}, smooth and consistent animation. "
        f"{atmosphere}. "
        f"The character is fully animated in {style_name} style throughout, not realistic or photographic. "
        f"Seamless motion, no cuts."
    )

    return prompt


def _build_choreography(phases: list[Any]) -> str:
    """Convert motion phases into a concise choreography description for Veo."""
    if not phases:
        return ""

    parts = []
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        time_range = phase.get("time_range", "")
        action = phase.get("action", "")
        tempo = phase.get("tempo", "")
        energy = phase.get("energy", "")

        if time_range and action:
            detail = f"{time_range}: {action}"
            if tempo and energy:
                detail += f" ({tempo} tempo, {energy} energy)"
            parts.append(detail)

    return "; ".join(parts) + "." if parts else ""


def _dominant_tempo(motion_analysis: dict[str, Any]) -> str:
    phases = motion_analysis.get("phases", [])
    if not phases:
        return "medium"
    tempos = [
        p.get("tempo", "medium")
        for p in phases
        if isinstance(p, dict) and p.get("tempo")
    ]
    if not tempos:
        return "medium"
    return max(set(tempos), key=tempos.count)
