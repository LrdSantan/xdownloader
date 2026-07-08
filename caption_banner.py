"""
Renders a caption banner (author name, handle, tweet text) as a PNG image,
sized to match the video's width, so it can be stacked on top of the video
with ffmpeg — producing a single combined file like a screenshot + clip.
"""

from PIL import Image, ImageDraw, ImageFont
import textwrap

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
BG_COLOR = (20, 18, 26)       # matches --ink
TEXT_COLOR = (237, 234, 227)  # matches --paper
HANDLE_COLOR = (138, 132, 148)  # matches --muted
PADDING = 40
LINE_SPACING = 10


def _load_font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(f"{FONT_DIR}/{name}", size)
    except Exception:
        return ImageFont.load_default()


def render_caption_banner(width: int, author_name: str, author_handle: str, caption: str) -> Image.Image:
    """
    Returns a PIL Image sized `width` wide, with author info and caption
    text wrapped to fit, on a dark background matching the app's theme.
    """
    name_font = _load_font(bold=True, size=34)
    handle_font = _load_font(bold=False, size=26)
    body_font = _load_font(bold=False, size=30)

    # Estimate characters per line based on width and font size
    avg_char_width = body_font.getlength("x") or 15
    max_chars = max(10, int((width - PADDING * 2) / avg_char_width))
    wrapped = textwrap.wrap(caption or "", width=max_chars) or [""]

    header_height = 70
    line_height = body_font.getbbox("Ag")[3] + LINE_SPACING
    text_block_height = line_height * len(wrapped)
    total_height = PADDING + header_height + text_block_height + PADDING

    img = Image.new("RGB", (width, total_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Author name + handle
    draw.text((PADDING, PADDING), author_name or "", font=name_font, fill=TEXT_COLOR)
    name_width = name_font.getlength(author_name or "")
    draw.text(
        (PADDING + name_width + 16, PADDING + 6),
        f"@{author_handle}" if author_handle else "",
        font=handle_font,
        fill=HANDLE_COLOR,
    )

    # Caption text, wrapped
    y = PADDING + header_height
    for line in wrapped:
        draw.text((PADDING, y), line, font=body_font, fill=TEXT_COLOR)
        y += line_height

    return img
