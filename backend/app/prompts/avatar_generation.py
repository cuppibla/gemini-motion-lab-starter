AVATAR_STYLES: dict[str, dict] = {
    "pixel-hero": {
        "name": "Pixel Hero",
        "description": "Retro 16-bit pixel art hero. Blocky pixels with vibrant primary colors, classic arcade game aesthetic like vintage side-scrollers. Bold heroic character with dynamic action pose, sharp pixel edges, no anti-aliasing, dramatic pixel shading.",
        "emoji": "🎮",
    },
    "cyber-nova": {
        "name": "Cyber Nova",
        "description": "Futuristic sci-fi powered armor suit. Sleek silver and dark grey nano-tech armor with glowing blue energy core on chest, holographic HUD visor, jet boots with blue repulsor flame, intricate panel detail with blue neon accent lines, cinematic volumetric lighting.",
        "emoji": "🤖",
    },
    "watercolor-dream": {
        "name": "Watercolor Dream",
        "description": "Soft watercolor painting on textured paper. Flowing edges that bleed slightly, visible brush strokes, pastel and muted tones with occasional vibrant splashes. Dreamy ethereal quality with gentle sunlight, whimsical nostalgic atmosphere.",
        "emoji": "🎨",
    },
    "3d-figurine": {
        "name": "3D Figurine",
        "description": "3D rendered miniature collectible figurine, blind box designer vinyl toy style. Chibi proportions with oversized head and small body, smooth matte clay-like plastic texture, standing on a circular display pedestal. Trendy casual outfit, big expressive eyes, pastel color palette. Professional product photography with soft studio lighting, shallow depth of field.",
        "emoji": "🧸",
    },
    "manga-ink": {
        "name": "Manga Ink",
        "description": "Black and white Japanese manga illustration. Bold confident ink strokes, expressive linework, high contrast pure black and white with screentone halftone shading for midtones. Stylish relaxed pose with expressive eyes, clean and elegant character design. Pen and ink on white paper quality.",
        "emoji": "✒️",
    },
    "brick-build": {
        "name": "Brick Build",
        "description": "Transform the person into a miniature figure made entirely of colorful interlocking plastic building bricks. Preserve the person's recognizable features — face shape, hair color and style, skin tone, and clothing colors — translated into blocky geometric brick form. Visible brick studs and realistic plastic sheen throughout. Standing in a neutral pose with expressive brick-built eyes. Clean white studio background, professional toy product photography.",
        "emoji": "🧱",
    },
}

AVATAR_PROMPT_TEMPLATE = """Look at this photo of a person. Generate a new image of this same person transformed into {STYLE_NAME} art style.

Keep recognizable from the original:
- Face shape, expression, and key facial features
- Hair style and color
- General body proportions
- Clothing style (adapted to the art style)

Style: {STYLE_DESCRIPTION}

Generate a full body portrait, standing in a neutral pose, clean solid color background, high quality, consistent art style throughout. The person should be clearly recognizable as a stylized version of themselves."""


def build_avatar_prompt(style_key: str, base_prompt_template: str = AVATAR_PROMPT_TEMPLATE) -> str:
    """Format the avatar generation prompt for the given style key."""
    style = AVATAR_STYLES.get(style_key)
    if not style:
        # Fall back to first defined style
        style = next(iter(AVATAR_STYLES.values()))
    return base_prompt_template.format(
        STYLE_NAME=style["name"],
        STYLE_DESCRIPTION=style["description"],
    )
