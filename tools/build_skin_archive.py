#!/usr/bin/env python3
"""Build the distributable CINÉVA ZIP with runtime-critical XML fixes."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import os
import struct
import tempfile
import time
import zlib
import binascii
import xml.etree.ElementTree as ET
import urllib.error
import urllib.request

ARCHIVE = Path(__file__).resolve().parents[1] / "skin.cineva-0.5.3.zip"


def fetch_asset(url, attempts=5):
    """Fetch a pinned build asset with bounded retries for transient GitHub/CDN errors."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "CINEVA-Skin-Builder/1.0"}
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in {408, 425, 429, 500, 502, 503, 504} or attempt == attempts - 1:
                raise
            retry_after = exc.headers.get("Retry-After")
            try:
                delay = min(30.0, max(1.0, float(retry_after))) if retry_after else min(16, 2 ** attempt)
            except ValueError:
                delay = min(16, 2 ** attempt)
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == attempts - 1:
                raise
            time.sleep(min(16, 2 ** attempt))
    raise RuntimeError(f"Could not download build asset after {attempts} attempts: {url}")


def png_chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF))


def hero_left_shade_png():
    """Create a deterministic left-to-right hero overlay with a soft bottom fade."""
    width, height = 1920, 440
    horizontal_alpha = [
        int(224 * max(0.0, 1.0 - x / (width * 0.82)) ** 1.55)
        for x in range(width)
    ]
    pixels = bytearray()
    for y in range(height):
        vertical = max(0.0, 1.0 - y / (height - 1)) ** 0.8
        pixels.append(0)  # PNG filter: None
        for base_alpha in horizontal_alpha:
            pixels.extend((5, 7, 12, int(base_alpha * vertical)))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", header)
            + png_chunk(b"IDAT", zlib.compress(bytes(pixels), 9))
            + png_chunk(b"IEND", b""))


def hero_topbar_shade_png():
    """Create a full-width top veil so navigation stays legible over bright fanart."""
    width, height = 1920, 180
    pixels = bytearray()
    for y in range(height):
        position = y / (height - 1)
        alpha = int(164 * max(0.0, 1.0 - position) ** 2.1)
        pixels.append(0)  # PNG filter: None
        for _ in range(width):
            pixels.extend((5, 7, 12, alpha))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", header)
            + png_chunk(b"IDAT", zlib.compress(bytes(pixels), 9))
            + png_chunk(b"IEND", b""))


def hero_bottom_fade_png():
    """Create a full-width fade that cleanly separates hero artwork from the shelves."""
    width, height = 1920, 430
    pixels = bytearray()
    for y in range(height):
        position = y / (height - 1)
        ramp = min(1.0, max(0.0, (position - 0.05) / 0.72))
        alpha = int(255 * ramp ** 1.2)
        pixels.append(0)  # PNG filter: None
        for _ in range(width):
            pixels.extend((5, 7, 12, alpha))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", header)
            + png_chunk(b"IDAT", zlib.compress(bytes(pixels), 9))
            + png_chunk(b"IEND", b""))


def hero_placeholder_png():
    """Create a restrained cinematic fallback for items without landscape fanart."""
    width, height = 1920, 750
    pixels = bytearray()
    for y in range(height):
        vertical = y / (height - 1)
        pixels.append(0)  # PNG filter: None
        for x in range(width):
            horizontal = x / (width - 1)
            # Keep the title-safe left third nearly black; place a soft crimson
            # lens glow and a muted cool halo on the far side of the composition.
            red_glow = max(
                0.0,
                1.0 - (((horizontal - 0.84) / 0.52) ** 2
                       + ((vertical - 0.46) / 0.92) ** 2)
            ) ** 2
            cool_glow = max(
                0.0,
                1.0 - (((horizontal - 0.66) / 0.48) ** 2
                       + ((vertical - 0.16) / 0.55) ** 2)
            ) ** 2
            beam_distance = abs(vertical - (0.13 + 0.48 * horizontal))
            beam = max(0.0, 1.0 - beam_distance / 0.026) ** 2
            beam *= max(0.0, (horizontal - 0.48) / 0.52)
            # Deterministic, very fine grain prevents the gradient from looking flat.
            grain = (((x * 73856093) ^ (y * 19349663)) & 3) - 1.5
            red = int(5 + 6 * horizontal + 31 * red_glow + 7 * beam + grain)
            green = int(7 + 4 * horizontal + 7 * red_glow + 2 * beam + grain)
            blue = int(13 + 8 * horizontal + 5 * red_glow + 12 * cool_glow + 3 * beam + grain)
            pixels.extend((
                max(0, min(255, red)),
                max(0, min(255, green)),
                max(0, min(255, blue)),
                255,
            ))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", header)
            + png_chunk(b"IDAT", zlib.compress(bytes(pixels), 9))
            + png_chunk(b"IEND", b""))


def rail_scroll_mask_png():
    """Create a long, low-contrast fade that avoids a hard black seam over the hero."""
    width, height = 1920, 430
    pixels = bytearray()
    for y in range(height):
        position = y / (height - 1)
        smooth = position * position * (3.0 - 2.0 * position)
        alpha = int(128 * smooth)
        pixels.append(0)  # PNG filter: None
        for _ in range(width):
            pixels.extend((5, 7, 12, alpha))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", header)
            + png_chunk(b"IDAT", zlib.compress(bytes(pixels), 9))
            + png_chunk(b"IEND", b""))


def resume_track_png():
    """Create a subtle charcoal progress track that blends into poster artwork."""
    width, height = 8, 8
    pixels = bytearray()
    for _ in range(height):
        pixels.append(0)  # PNG filter: None
        for _ in range(width):
            pixels.extend((39, 42, 48, 238))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", header)
            + png_chunk(b"IDAT", zlib.compress(bytes(pixels), 9))
            + png_chunk(b"IEND", b""))


def poster_focus_png():
    """Create a restrained crimson focus frame instead of a stark white poster box."""
    width, height = 8, 8
    pixels = bytearray()
    for y in range(height):
        pixels.append(0)  # PNG filter: None
        for x in range(width):
            edge = 1 <= x <= 6 and 1 <= y <= 6 and (x <= 2 or x >= 5 or y <= 2 or y >= 5)
            pixels.extend((229, 9, 20, 188) if edge else (0, 0, 0, 0))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", header)
            + png_chunk(b"IDAT", zlib.compress(bytes(pixels), 9))
            + png_chunk(b"IEND", b""))


def poster_placeholder_png():
    """Create cinematic abstract artwork when a provider has no poster."""
    width, height = 342, 513
    pixels = bytearray()
    for y in range(height):
        vertical = y / (height - 1)
        pixels.append(0)
        for x in range(width):
            horizontal = x / (width - 1)
            # Deep midnight gradient with restrained crimson and blue light leaks.
            red_glow = max(0.0, 1.0 - (((horizontal - 0.82) / 0.62) ** 2
                                      + ((vertical - 0.48) / 0.56) ** 2)) ** 2
            blue_glow = max(0.0, 1.0 - (((horizontal - 0.18) / 0.62) ** 2
                                       + ((vertical - 0.22) / 0.48) ** 2)) ** 2
            red = int(5 + 8 * horizontal + 31 * red_glow)
            green = int(8 + 7 * (1 - vertical) + 5 * red_glow)
            blue = int(17 + 17 * blue_glow + 10 * red_glow)
            pixels.extend((red, green, blue, 255))

    def pixel(x, y, color):
        if 0 <= x < width and 0 <= y < height:
            offset = y * (1 + width * 4) + 1 + x * 4
            pixels[offset:offset + 4] = bytes((*color, 255))

    def line(x1, y1, x2, y2, color, thickness=1):
        dx, sx = abs(x2 - x1), 1 if x1 < x2 else -1
        dy, sy = -abs(y2 - y1), 1 if y1 < y2 else -1
        error = dx + dy
        radius = max(0, (thickness - 1) // 2)
        while True:
            for oy in range(-radius, radius + 1):
                for ox in range(-radius, radius + 1):
                    pixel(x1 + ox, y1 + oy, color)
            if x1 == x2 and y1 == y2:
                break
            doubled = 2 * error
            if doubled >= dy:
                error += dy
                x1 += sx
            if doubled <= dx:
                error += dx
                y1 += sy

    # A distant horizon and layered angular silhouettes create a film-poster
    # composition without implying playback or pretending to be real artwork.
    horizon = 356
    for y in range(horizon, height):
        fade = (y - horizon) / (height - horizon)
        shade = int(9 + 9 * fade)
        for x in range(width):
            pixel(x, y, (shade + 3, shade + 5, shade + 13))
    skyline = [
        (0, 353), (38, 322), (70, 345), (108, 298), (143, 338),
        (178, 310), (213, 344), (258, 292), (296, 331), (342, 307)
    ]
    for index in range(len(skyline) - 1):
        x1, y1 = skyline[index]
        x2, y2 = skyline[index + 1]
        line(x1, y1, x2, y2, (17, 25, 39), 5)
    # A narrow vertical shaft of light gives the art a focal point.
    for y in range(90, 350):
        spread = max(1, int((y - 88) * 0.035))
        for x in range(246 - spread, 247 + spread):
            pixel(x, y, (24, 30, 48))
    line(246, 112, 246, 344, (76, 43, 55), 1)
    # Fine crimson horizon accent, deliberately understated.
    line(54, 420, 288, 420, (116, 25, 39), 2)
    line(54, 426, 154, 426, (54, 39, 53), 1)

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", header)
            + png_chunk(b"IDAT", zlib.compress(bytes(pixels), 9))
            + png_chunk(b"IEND", b""))

def hero_poster_vignette_png():
    """Blend a fitted 2:3 poster into the 640x750 fallback hero panel."""
    width, height = 640, 750
    # A 342x513 poster fitted to 750px height occupies 500px, centered
    # inside the 640px panel. Fade precisely across its two vertical edges.
    poster_width = height * 2 // 3
    poster_left = (width - poster_width) // 2
    poster_right = poster_left + poster_width
    fade_width = 72
    pixels = bytearray()
    for _ in range(height):
        pixels.append(0)  # PNG filter: None
        for x in range(width):
            if x < poster_left or x > poster_right:
                alpha = 232
            elif x < poster_left + fade_width:
                progress = (x - poster_left) / fade_width
                alpha = int(232 * (1.0 - progress) ** 1.8)
            elif x > poster_right - fade_width:
                progress = (poster_right - x) / fade_width
                alpha = int(232 * (1.0 - progress) ** 1.8)
            else:
                alpha = 0
            pixels.extend((5, 7, 12, alpha))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (bytes.fromhex("89504e470d0a1a0a")
            + png_chunk(b"IHDR", header)
            + png_chunk(b"IDAT", zlib.compress(bytes(pixels), 9))
            + png_chunk(b"IEND", b""))

def set_child_text(parent, tag, value):
    node = parent.find(tag)
    if node is None:
        node = ET.SubElement(parent, tag)
    node.text = str(value)


def remove_missing_no_focus_textures(root):
    """Remove dash placeholders that Kodi interprets as missing texture files."""
    for node in root.findall(".//control[@type='button']"):
        texture = node.find("texturenofocus")
        if texture is not None and (texture.text or "").strip() == "-":
            node.remove(texture)


def update_xml(data, path):
    root = ET.fromstring(data)
    if path == "skin.cineva/addon.xml":
        root.set("version", "0.5.3")
        for imp in root.findall("./requires/import"):
            if imp.get("addon") == "script.cineva.widgets":
                imp.set("version", "0.1.3")
    elif path == "skin.cineva/xml/Home.xml":
        default = root.find("defaultcontrol")
        if default is None:
            default = ET.Element("defaultcontrol", {"always": "true"})
            root.insert(0, default)
        default.set("always", "true")
        default.text = "1001"
        onload = root.find("onload")
        if onload is None:
            onload = ET.Element("onload")
            root.insert(0, onload)
        onload.attrib.clear()
        onload.text = "RunScript(script.cineva.widgets,action=init)"
        # Rebuild Home as a cinematic hero plus large, breathable content rails.
        # Keep the first rail fully visible and reveal a substantial preview of the next rail; remaining shelves stay reachable by D-pad navigation.
        controls = root.find("controls")
        if controls is None:
            raise SystemExit("Home.xml is missing its controls container")
        # The archive builder runs twice in CI. Unwrap an existing rail grouplist
        # before rebuilding it so the transformation remains idempotent.
        previous_rail_list = controls.find("./control[@type='grouplist'][@id='9050']")
        if previous_rail_list is not None:
            row_insert_index = list(controls).index(previous_rail_list)
            controls.remove(previous_rail_list)
            for child in list(previous_rail_list.findall("control")):
                previous_rail_list.remove(child)
                # Newer builds wrap each heading/shelf pair in a row group.
                # Unwrap those groups before rebuilding so two consecutive
                # archive builds remain structurally identical.
                if child.get("type") == "group" and child.get("id", "").startswith("906"):
                    for row_child in list(child.findall("control")):
                        child.remove(row_child)
                        # Row accents belong inside their shelf group. Older
                        # builds accidentally promoted them to screen-level
                        # controls, leaving red bars pinned to the top-left.
                        if (row_child.get("type") == "image"
                                and row_child.findtext("texture") == "focus-bar.png"
                                and row_child.findtext("visible", "") in {
                                    f"Control.HasFocus({focus_id})" for focus_id in (9001, 9002, 9003, 9004)
                                }):
                            continue
                        controls.insert(row_insert_index, row_child)
                        row_insert_index += 1
                else:
                    controls.insert(row_insert_index, child)
                    row_insert_index += 1
        # Clean up accents orphaned by earlier non-idempotent archive builds.
        # Only the 58x3 focus-bar controls tied to the four Home shelves match;
        # the navigation marker and focused-poster frame remain untouched.
        row_focus_conditions = {f"Control.HasFocus({focus_id})" for focus_id in (9001, 9002, 9003, 9004)}
        for orphan in list(controls.findall("control")):
            if (orphan.get("type") == "image"
                    and orphan.findtext("texture") == "focus-bar.png"
                    and orphan.findtext("visible", "") in row_focus_conditions
                    and (orphan.findtext("left"), orphan.findtext("width"), orphan.findtext("height")) == ("0", "58", "3")):
                controls.remove(orphan)
        # Rebuild the optional portrait-led fallback without accumulating controls
        # when the archive transformation is run more than once.
        generated_hero_ids = {str(control_id) for control_id in range(9140, 9148)}
        for stale in list(controls.findall("control")):
            if stale.get("id") in generated_hero_ids:
                controls.remove(stale)
        # Cinematic hero: give artwork room to breathe and fade it cleanly into the catalogue.
        for control in controls.findall("control"):
            texture = control.findtext("texture", "")
            if (control.get("type") == "image"
                    and texture.startswith("$INFO[Container(")
                    and ".ListItem.Art(fanart)]" in texture):
                # Keep a branded landscape visible even when a provider supplies
                # a poster but no fanart. The row-1 hero is always the initial
                # backdrop; later rows replace it only while their item/actions
                # are active, regardless of whether landscape art exists.
                set_child_text(control, "height", 750)
                texture_node = control.find("texture")
                if texture_node is None:
                    raise SystemExit("Home hero artwork control has no texture node")
                texture_node.set("fallback", "hero-placeholder.png")
                container_id = int(texture.split("Container(", 1)[1].split(")", 1)[0])
                if container_id == 9001:
                    # Row 1 owns the initial Home backdrop, including missing-art items.
                    visible = control.find("visible")
                    if visible is not None:
                        control.remove(visible)
                else:
                    play_id = 9111 + (container_id - 9001) * 2
                    action_focus = " | ".join(
                        f"Control.HasFocus({focus_id})"
                        for focus_id in (container_id, play_id, play_id + 1)
                    )
                    set_child_text(control, "visible", action_focus)
            if control.get("type") == "image" and texture == "hero-shade.png":
                set_child_text(control, "height", 750)
        # If the selected item has a poster but no landscape artwork, use that
        # portrait as a right-side key-art panel instead of leaving the hero empty.
        hero_artwork = [
            node for node in controls.findall("control")
            if node.get("type") == "image"
            and ".ListItem.Art(fanart)]" in node.findtext("texture", "")
        ]
        if len(hero_artwork) != 4:
            raise SystemExit(f"Home.xml must have four dynamic fanart layers, found {len(hero_artwork)}")
        poster_layers = []
        row1_exclusions = (9002, 9113, 9114, 9003, 9115, 9116, 9004, 9117, 9118)
        for row_index, container_id in enumerate((9001, 9002, 9003, 9004), start=1):
            art_conditions = (
                f"String.IsEmpty(Container({container_id}).ListItem.Art(fanart))",
                f"!String.IsEmpty(Container({container_id}).ListItem.Art(poster))",
            )
            if row_index == 1:
                visible = " + ".join(
                    [f"!Control.HasFocus({focus_id})" for focus_id in row1_exclusions]
                    + list(art_conditions)
                )
            else:
                play_id = 9111 + (row_index - 1) * 2
                visible = " | ".join(
                    " + ".join((f"Control.HasFocus({focus_id})",) + art_conditions)
                    for focus_id in (container_id, play_id, play_id + 1)
                )
            poster = ET.Element("control", {"type": "image", "id": str(9139 + row_index)})
            for tag, value in (
                ("left", 1280), ("top", 0), ("width", 640), ("height", 750),
                ("texture", f"$INFO[Container({container_id}).ListItem.Art(poster)]"),
                ("visible", visible),
            ):
                set_child_text(poster, tag, value)
            ET.SubElement(
                poster, "aspectratio", {"align": "center", "aligny": "center"}
            ).text = "keep"
            vignette = ET.Element("control", {"type": "image", "id": str(9143 + row_index)})
            for tag, value in (
                ("left", 1280), ("top", 0), ("width", 640), ("height", 750),
                ("texture", "hero-poster-vignette.png"), ("visible", visible),
            ):
                set_child_text(vignette, tag, value)
            set_child_text(vignette, "aspectratio", "scale")
            poster_layers.extend((poster, vignette))
        insert_at = list(controls).index(hero_artwork[-1]) + 1
        for layer in poster_layers:
            controls.insert(insert_at, layer)
            insert_at += 1
        # Add a mirrored top fade so the logo/date remain legible over bright fanart.
        hero_shade = next((node for node in controls.findall("control")
                           if node.get("type") == "image" and node.findtext("texture") == "hero-shade.png"), None)
        if hero_shade is None:
            raise SystemExit("Home.xml is missing the hero fade texture")
        previous_top_shade = controls.find("./control[@id='9100']")
        if previous_top_shade is not None:
            controls.remove(previous_top_shade)
        top_shade = ET.Element("control", {"type": "image", "id": "9100"})
        for tag, value in (("left", 0), ("top", 0), ("width", 1920), ("height", 320)):
            set_child_text(top_shade, tag, value)
        top_texture = ET.SubElement(top_shade, "texture", {"flipy": "true"})
        top_texture.text = "hero-shade.png"
        set_child_text(top_shade, "aspectratio", "scale")
        controls.insert(list(controls).index(hero_shade) + 1, top_shade)
        previous_left_shade = controls.find("./control[@id='9105']")
        if previous_left_shade is not None:
            controls.remove(previous_left_shade)
        left_shade = ET.Element("control", {"type": "image", "id": "9105"})
        for tag, value in (("left", 0), ("top", 0), ("width", 1920), ("height", 440)):
            set_child_text(left_shade, tag, value)
        ET.SubElement(left_shade, "texture").text = "hero-left-shade.png"
        set_child_text(left_shade, "aspectratio", "scale")
        controls.insert(list(controls).index(top_shade) + 1, left_shade)
        previous_bottom_shade = controls.find("./control[@id='9106']")
        if previous_bottom_shade is not None:
            controls.remove(previous_bottom_shade)
        bottom_shade = ET.Element("control", {"type": "image", "id": "9106"})
        for tag, value in (("left", 0), ("top", 320), ("width", 1920), ("height", 430)):
            set_child_text(bottom_shade, tag, value)
        ET.SubElement(bottom_shade, "texture").text = "hero-bottom-fade.png"
        set_child_text(bottom_shade, "aspectratio", "scale")
        controls.insert(list(controls).index(left_shade) + 1, bottom_shade)
        # A restrained full-width top veil keeps the logo, navigation and date
        # readable over bright fanart without dimming the cinematic title area.
        previous_topbar_shade = controls.find("./control[@id='9108']")
        if previous_topbar_shade is not None:
            controls.remove(previous_topbar_shade)
        topbar_shade = ET.Element("control", {"type": "image", "id": "9108"})
        for tag, value in (("left", 0), ("top", 0), ("width", 1920), ("height", 180)):
            set_child_text(topbar_shade, tag, value)
        ET.SubElement(topbar_shade, "texture").text = "hero-topbar-shade.png"
        set_child_text(topbar_shade, "aspectratio", "scale")
        controls.insert(list(controls).index(bottom_shade) + 1, topbar_shade)
        # Keep navigation above full-bleed artwork; it was previously painted first
        # and then hidden beneath the hero image controls.
        topbar = next((node for node in list(controls)
                       if node.tag == "include" and (node.text or "").strip() == "CinevaTopBar"), None)
        if topbar is not None:
            controls.remove(topbar)
            hero_end = max((i for i, node in enumerate(list(controls))
                            if node.tag == "control" and node.get("type") == "image"), default=-1)
            controls.insert(hero_end + 1, topbar)
        for group in controls.findall("control"):
            source_label = group.findtext("control/label", "")
            if group.get("type") == "group" and source_label.startswith("$INFO[Container("):
                set_child_text(group, "top", 118)
                labels = [child for child in group.findall("control") if child.get("type") == "label"]
                if labels:
                    # Title first, metadata second: separate vertical baselines.
                    set_child_text(labels[0], "top", 32)
                    set_child_text(labels[0], "height", 82)
                    set_child_text(labels[0], "textcolor", "white")
                    set_child_text(labels[0], "width", 1200)
                    set_child_text(labels[0], "font", "font20")
                    set_child_text(labels[0], "wrapmultiline", "true")
                    set_child_text(labels[0], "aligny", "center")
                    set_child_text(labels[0], "align", "left")
                if len(labels) > 1:
                    # Kodi's INFO prefix is emitted only when that field has a value.
                    # This prevents empty duration metadata from leaving doubled bullets
                    # (and keeps the same compact format for all four dynamic hero rows).
                    container_id = int(source_label.split("Container(", 1)[1].split(")", 1)[0])
                    metadata = (
                        f"$INFO[Container({container_id}).ListItem.Year]"
                        f"$INFO[Container({container_id}).ListItem.Duration,  •  ]"
                        f"$INFO[Container({container_id}).ListItem.Genre,  •  ]"
                        f"$INFO[Container({container_id}).ListItem.Rating,  •  ]"
                    )
                    set_child_text(labels[1], "label", metadata)
                    set_child_text(labels[1], "top", 128)
                    set_child_text(labels[1], "height", 28)
                    set_child_text(labels[1], "font", "font10")
                    set_child_text(labels[1], "textcolor", "silver")
                for child in group.findall("control"):
                    if child.get("type") == "textbox":
                        set_child_text(child, "top", 164)
                        set_child_text(child, "height", 56)
                        set_child_text(child, "width", 900)
                        set_child_text(child, "font", "font13")
                        set_child_text(child, "textcolor", "white")
            if group.get("type") == "group" and group.findtext("control/label", "").startswith("$INFO[Container("):
                set_child_text(group, "width", 1200)
        # Hero actions follow whichever Home rail supplies the current hero item.
        # The play command uses the selected ListItem.File; Info first returns focus
        # to that rail so Kodi opens the correct item's information dialog.
        for control in list(controls):
            if control.get("id") in {"9101", "9102", "9103", "9104"}:
                controls.remove(control)
        action_specs = ((9001, 9111, 1001), (9002, 9113, 1001),
                        (9003, 9115, 1002), (9004, 9117, 1003))
        # Keep each action pair inside the matching hero group. Separate sibling
        # groups were intermittently hidden while the vertical Home rail scrolled;
        # nesting them with the title/synopsis makes their visibility and focus
        # lifecycle identical for all four rows.
        home_default_hero_group = None
        for container_id, play_id, nav_target in action_specs:
            info_id = play_id + 1
            hero_groups = [
                group for group in controls.findall("control")
                if group.get("type") == "group"
                and group.findtext("control/label", "").startswith(
                    f"$INFO[Container({container_id}).ListItem.Label]")
            ]
            if not hero_groups:
                raise SystemExit(f"Home.xml is missing the hero group for row {container_id}")
            hero_group = next(
                (group for group in hero_groups
                 if container_id == 9001 and "Control.HasFocus(1001)" in group.findtext("visible", "")),
                hero_groups[0]
            )
            if container_id == 9001:
                # Row 1 originally had separate navigation-focused and poster-focused
                # hero groups. The buttons lived only in the former, so Up from the
                # first shelf focused invisible controls. Consolidate both states into
                # one group and remove the duplicate title/synopsis group.
                home_default_hero_group = hero_group
                for duplicate in hero_groups:
                    if duplicate is not hero_group:
                        controls.remove(duplicate)
            set_child_text(hero_group, "height", 320)
            # Add a restrained editorial eyebrow above the dynamic title. It
            # gives every selected shelf item a clear hierarchy without
            # hard-coding a movie/show name or implying platform exclusivity.
            row_index = container_id - 9000
            # The eyebrow describes the active widget source instead of saying
            # FEATURED for every rail. Defaults resolve to CONTINUE WATCHING
            # or TRENDING NOW; user-added/replaced paths receive a neutral label.
            eyebrow_base_id = 9300 + (row_index - 1) * 3
            for old_control in list(hero_group.findall("control")):
                if old_control.get("id") in {
                    *(str(eyebrow_base_id + offset) for offset in range(3)),
                    str(9190 + (container_id - 9001)), str(play_id), str(info_id)
                }:
                    hero_group.remove(old_control)
            source_path = f"Skin.String(Cineva.Widget{row_index}.Path)"
            eyebrow_specs = (
                ("CONTINUE WATCHING", f"String.Contains({source_path},in_progress)"),
                ("TRENDING NOW", f"String.Contains({source_path},trending)"),
                ("YOUR COLLECTION",
                 f"!String.Contains({source_path},in_progress) + !String.Contains({source_path},trending)")
            )
            for offset, (label, visible) in enumerate(eyebrow_specs):
                eyebrow = ET.SubElement(
                    hero_group, "control",
                    {"type": "label", "id": str(eyebrow_base_id + offset)}
                )
                for tag, value in (
                    ("left", 0), ("top", 0), ("width", 420), ("height", 24),
                    ("label", label), ("visible", visible), ("font", "font9"),
                    ("textcolor", "FFE50914"), ("align", "left"), ("aligny", "center")
                ):
                    set_child_text(eyebrow, tag, value)
            # Prefer provider-supplied clear logos in the title slot. Keep the
            # readable text title as a per-item fallback when clearlogo art is absent.
            title_label = next(
                (node for node in hero_group.findall("control")
                 if node.get("type") == "label"
                 and f"$INFO[Container({container_id}).ListItem.Label]" in node.findtext("label", "")),
                None,
            )
            if title_label is None:
                raise SystemExit(f"Home hero {container_id} is missing its dynamic title label")
            clearlogo_info = f"Container({container_id}).ListItem.Art(clearlogo)"
            set_child_text(title_label, "visible", f"String.IsEmpty({clearlogo_info})")
            clearlogo = ET.SubElement(
                hero_group, "control",
                {"type": "image", "id": str(9190 + (container_id - 9001))}
            )
            for tag, value in (
                ("left", 0), ("top", 36), ("width", 900), ("height", 70),
                ("texture", f"$INFO[{clearlogo_info}]"),
                ("visible", f"!String.IsEmpty({clearlogo_info})"),
            ):
                set_child_text(clearlogo, tag, value)
            ET.SubElement(
                clearlogo, "aspectratio", {"align": "left", "aligny": "center"}
            ).text = "keep"
            for button_id, label, left, width in (
                (play_id, f"$VAR[CinevaHeroAction{row_index}]", 0, 176),
                (info_id, "MORE INFO", 196, 210)
            ):
                button = ET.SubElement(hero_group, "control",
                                       {"type": "button", "id": str(button_id)})
                for tag, value in (
                    ("left", left), ("top", 238), ("width", width), ("height", 50),
                    ("label", label), ("font", "font10"),
                    ("onup", f"SetFocus({nav_target})"),
                    ("ondown", f"SetFocus({container_id})"),
                    ("onleft", f"SetFocus({play_id})"),
                    ("onright", f"SetFocus({info_id})"),
                    ("texturefocus", "focus-bar.png"),
                    ("texturenofocus", "white.png" if button_id == play_id else "black.png"),
                    ("textcolor", "black" if button_id == play_id else "white"),
                    ("focusedcolor", "white"), ("align", "center"), ("aligny", "center")
                ):
                    set_child_text(button, tag, value)
                set_child_text(button, "textcolor", "black" if button_id == play_id else "gainsboro")
                if button_id == play_id:
                    set_child_text(button, "onclick",
                                   f"PlayMedia($INFO[Container({container_id}).ListItem.File])")
                else:
                    set_child_text(button, "onclick", f"SetFocus({container_id})")
                    ET.SubElement(button, "onclick").text = "Action(Info)"
        # Keep hero metadata visible while either action button in its row is focused.
        for hero_group in controls.findall("control"):
            if hero_group.get("type") != "group":
                continue
            source_label = hero_group.findtext("control/label", "")
            if not source_label.startswith("$INFO[Container("):
                continue
            current_visible = hero_group.findtext("visible", "")
            if "Control.HasFocus(1001)" in current_visible:
                continue
            container_id = int(source_label.split("Container(", 1)[1].split(")", 1)[0])
            play_id = 9111 + (container_id - 9001) * 2
            set_child_text(hero_group, "visible",
                           f"Control.HasFocus({container_id}) | Control.HasFocus({play_id}) | Control.HasFocus({play_id + 1})")
        if home_default_hero_group is None:
            raise SystemExit("Home row 1 lost its consolidated hero/action group")
        # Keep the first hero active on initial Home/navigation focus and while
        # row 1 or its two actions are focused. Switch cleanly to rows 2–4 without
        # leaving two hero groups visible or hiding row 1's PLAY/MORE INFO controls.
        row1_exclusions = (9002, 9113, 9114, 9003, 9115, 9116, 9004, 9117, 9118)
        set_child_text(home_default_hero_group, "visible",
                       " + ".join(f"!Control.HasFocus({control_id})" for control_id in row1_exclusions))
        # Keep the cinematic hero pinned while the four Home rails scroll as one catalogue.
        # Each row is a single grouplist child so its non-focusable heading cannot
        # intercept Up from the nested fixedlist before the shelf's explicit route.
        rail_list = ET.Element("control", {"type": "grouplist", "id": "9050"})
        for tag, value in (("left", 105), ("top", 454), ("width", 1710), ("height", 670)):
            set_child_text(rail_list, tag, value)
        set_child_text(rail_list, "orientation", "vertical")
        set_child_text(rail_list, "itemgap", 12)
        # Keep the rail viewport responsive on low-power TV hardware. Kodi's
        # native grouplist already performs the required movement; avoid an
        # additional conditional slide animation on the entire 4-row viewport.
        set_child_text(rail_list, "scrolltime", 160)
        set_child_text(rail_list, "usecontrolcoords", "false")
        first_row_index = None
        for index in range(1, 5):
            heading_label = f"$INFO[Skin.String(Cineva.Widget{index}.Name)]"
            heading = next((c for c in controls.findall("control")
                            if c.get("type") == "label" and c.findtext("label") == heading_label), None)
            shelf = controls.find(f"./control[@type='fixedlist'][@id='{9000 + index}']")
            if heading is None or shelf is None:
                raise SystemExit(f"Home.xml is missing widget row {index}")
            if first_row_index is None:
                first_row_index = list(controls).index(heading)
            controls.remove(heading)
            controls.remove(shelf)
            row_group = ET.Element("control", {"type": "group", "id": str(9060 + index)})
            for tag, value in (("left", 0), ("top", 0), ("width", 1710), ("height", 508)):
                set_child_text(row_group, tag, value)
            play_id = 9111 + (index - 1) * 2
            next_target = 9000 + index + 1 if index < 4 else 1001
            set_child_text(row_group, "onup", f"SetFocus({play_id})")
            set_child_text(row_group, "ondown", f"SetFocus({next_target})")
            # The grouplist places each row group in sequence; children use local coordinates.
            set_child_text(heading, "left", 0)
            set_child_text(heading, "top", 0)
            set_child_text(heading, "width", 1100)
            set_child_text(heading, "height", 38)
            set_child_text(heading, "font", "font18")
            set_child_text(shelf, "left", 0)
            set_child_text(shelf, "top", 52)
            set_child_text(shelf, "width", 1710)
            set_child_text(shelf, "height", 448)
            set_child_text(shelf, "itemgap", 14)
            set_child_text(shelf, "onup", f"SetFocus({play_id})")
            set_child_text(shelf, "ondown", f"SetFocus({next_target})")
            for layout in shelf.findall("./itemlayout") + shelf.findall("./focusedlayout"):
                layout.set("width", "285")
                layout.set("height", "448")
            focused_layout = shelf.find("./focusedlayout")
            focused_include = focused_layout.find("include") if focused_layout is not None else None
            if focused_include is not None:
                focused_include.text = f"CinevaFocusedPosterItem{9000 + index}"
            # Keep already-passed shelves in the grouplist's geometry, but stop
            # painting their posters/titles behind the pinned hero when a later
            # rail becomes active. This preserves the preview on initial Home.
            later_focus_ids = []
            for later_index in range(index + 1, 5):
                later_container = 9000 + later_index
                later_play = 9111 + (later_index - 1) * 2
                later_focus_ids.extend((later_container, later_play, later_play + 1))
            base_row_visibility = f"!String.IsEmpty(Skin.String(Cineva.Widget{index}.Path))"
            # Reset source visibility first so repeated archive builds do not
            # append duplicate Kodi boolean conditions to the same control.
            set_child_text(heading, "visible", base_row_visibility)
            set_child_text(shelf, "visible", base_row_visibility)
            if later_focus_ids:
                hide_previous_row = " + ".join(
                    f"!Control.HasFocus({control_id})" for control_id in later_focus_ids
                )
                set_child_text(heading, "visible", f"{base_row_visibility} + {hide_previous_row}")
                set_child_text(shelf, "visible", f"{base_row_visibility} + {hide_previous_row}")
            # A restrained red underline makes the active Home rail legible
            # even when the selected poster is several cards into the row.
            row_accent = ET.Element("control", {"type": "image"})
            for tag, value in (("left", 0), ("top", 40), ("width", 58), ("height", 3)):
                set_child_text(row_accent, tag, value)
            set_child_text(row_accent, "texture", "focus-bar.png")
            set_child_text(row_accent, "visible", f"Control.HasFocus({9000 + index})")
            row_group.append(heading)
            row_group.append(row_accent)
            row_group.append(shelf)
            rail_list.append(row_group)
        if first_row_index is None:
            raise SystemExit("Home.xml has no widget rows to place in the scrolling rail list")
        previous_scroll_mask = controls.find("./control[@id='9107']")
        if previous_scroll_mask is not None:
            controls.remove(previous_scroll_mask)
        controls.insert(first_row_index, rail_list)
        # When a lower rail is focused, blend the scrolled-away shelf contents
        # into the pinned hero's own bottom fade instead of painting a hard black stripe.
        scroll_mask = ET.Element("control", {"type": "image", "id": "9107"})
        for tag, value in (("left", 0), ("top", 320), ("width", 1920), ("height", 430)):
            set_child_text(scroll_mask, tag, value)
        ET.SubElement(scroll_mask, "texture").text = "rail-scroll-mask.png"
        set_child_text(scroll_mask, "aspectratio", "scale")
        lower_focus_ids = (9002, 9113, 9114, 9003, 9115, 9116, 9004, 9117, 9118)
        set_child_text(scroll_mask, "visible", " | ".join(
            f"Control.HasFocus({control_id})" for control_id in lower_focus_ids
        ))
        # Draw the fade over the hero background but underneath the scrolling
        # shelves. This keeps the pinned backdrop blended while poster artwork,
        # progress bars and the active-rail underline retain their full contrast.
        controls.insert(list(controls).index(rail_list), scroll_mask)
        # Hero titles and PLAY / MORE INFO controls remain above both the fade
        # and the shelves, preserving the selected row's cinematic composition.
        home_hero_groups = [
            node for node in controls.findall("control")
            if node.get("type") == "group"
            and node.findtext("control/label", "").startswith("$INFO[Container(")
        ]
        for hero_group in home_hero_groups:
            controls.remove(hero_group)
        for hero_group in home_hero_groups:
            controls.append(hero_group)
        nav_group = next((node for node in controls.findall("control") if node.get("type") == "group" and node.find("./control[@id='1001']") is not None), None)
        if nav_group is not None:
            # Widget sources belong in Skin Settings, not in a separate Home destination.
            # Remove the stale hub button and reclaim its slot for the single Settings entry.
            widget_hub = next(
                (button for button in nav_group.findall("./control[@type='button']")
                 if button.findtext("label", "").strip().upper() == "MY WIDGETS"
                 or "ActivateWindow(11119)" in button.findtext("onclick", "")),
                None,
            )
            if widget_hub is not None:
                nav_group.remove(widget_hub)
            # Find Settings by meaning rather than its old ID: after the first
            # build it already owns 1005, so rerunning the builder must preserve it.
            settings_button = next(
                (button for button in nav_group.findall("./control[@type='button']")
                 if button.findtext("label", "").strip().upper() == "SETTINGS"),
                None,
            )
            if settings_button is not None:
                settings_button.set("id", "1005")
                set_child_text(settings_button, "left", 670)
                set_child_text(settings_button, "width", 150)
            # Put the menu on the same horizontal baseline as the CINÉVA wordmark
            # instead of stacking it underneath. The right-aligned date remains
            # anchored at the far edge of the same 1080p-safe header row.
            for tag, value in (("left", 280), ("top", 32), ("width", 1080), ("height", 48)):
                set_child_text(nav_group, tag, value)
            for button in nav_group.findall("./control[@type='button']"):
                # Text-first navigation: remove the heavy black button slabs.
                action_targets = {"1001": "9111", "1002": "9115", "1003": "9117"}
                if button.get("id") in action_targets:
                    set_child_text(button, "ondown", f"SetFocus({action_targets[button.get('id')]})")
                for tag, value in (("texturefocus", "focus-bar.png"), ("texturenofocus", "-"), ("textcolor", "silver"), ("focusedcolor", "white"), ("align", "center"), ("aligny", "center")):
                    set_child_text(button, tag, value)
                set_child_text(button, "font", "font12")
                set_child_text(button, "height", 48)
            # Keep a persistent red section marker under HOME even after focus
            # moves into the catalogue, so users never lose their location.
            old_marker = nav_group.find("./control[@id='9201']")
            if old_marker is not None:
                nav_group.remove(old_marker)
            active_marker = ET.Element("control", {"type": "image", "id": "9201"})
            for tag, value in (("left", 34), ("top", 42), ("width", 62), ("height", 4)):
                set_child_text(active_marker, tag, value)
            set_child_text(active_marker, "texture", "focus-bar.png")
            set_child_text(active_marker, "visible", "Window.IsActive(home)")
            nav_group.append(active_marker)
        # The top navigation already has a My Widgets destination. The extra
        # floating button obscured the fourth shelf and is intentionally removed.
        for control in list(controls):
            if control.get("id") == "9010" or control.findtext("label") == "MORE WIDGETS  ›":
                controls.remove(control)
    elif path == "skin.cineva/xml/Includes.xml":
        # Use RESUME for continue-watching sources and PLAY for other shelves.
        # Keep the label in a skin variable so each row's action remains one
        # focusable button with the same ID and D-pad route.
        for row_index in range(1, 5):
            variable_name = f"CinevaHeroAction{row_index}"
            previous_variable = root.find(f"./variable[@name='{variable_name}']")
            if previous_variable is not None:
                root.remove(previous_variable)
            variable = ET.Element("variable", {"name": variable_name})
            resume_value = ET.SubElement(
                variable, "value",
                {"condition": f"String.Contains(Skin.String(Cineva.Widget{row_index}.Path),in_progress)"}
            )
            resume_value.text = "RESUME"
            play_value = ET.SubElement(variable, "value")
            play_value.text = "PLAY"
            root.insert(row_index - 1, variable)
        # Brand typography and date treatment are shared across all windows.
        topbar = root.find("./include[@name='CinevaTopBar']")
        if topbar is not None:
            for label in topbar.findall(".//control[@type='label']"):
                text_value = label.findtext("label", "")
                if text_value == "CINÉVA":
                    set_child_text(label, "font", "font24")
                    set_child_text(label, "height", 62)
                elif "$INFO[System.Date]" in text_value:
                    set_child_text(label, "font", "font12")
                    set_child_text(label, "textcolor", "silver")
        normal = root.find("./include[@name='CinevaPosterItem']")
        focused = root.find("./include[@name='CinevaFocusedPosterItem']")
        if normal is None or focused is None:
            raise SystemExit("Includes.xml is missing CINÉVA poster layouts")
        normal_image = normal.find("./control[@type='image']")
        normal_label = normal.find("./control[@type='textbox']")
        if normal_label is None:
            normal_label = normal.find("./control[@type='label']")
        focused_image = focused.find("./control[@type='image']")
        focused_label = focused.find("./control[@type='textbox']")
        if focused_label is None:
            focused_label = focused.find("./control[@type='label']")
        progress = focused.find("./control[@type='progress']")
        if any(node is None for node in (normal_image, normal_label, focused_image, progress)):
            raise SystemExit("Includes.xml has an incomplete poster layout")
        if focused_label is None:
            focused_label = ET.fromstring(ET.tostring(normal_label, encoding="unicode"))
        # Kodi label controls ellipsize long card titles despite wrapmultiline.
        # Textboxes wrap naturally inside the same fixed 48px caption area.
        normal_label.set("type", "textbox")
        focused_label.set("type", "textbox")
        for tag, value in (("left", 12), ("top", 0), ("width", 261), ("height", 348)):
            set_child_text(normal_image, tag, value)
        # Use the semantic poster key for every shelf state. Providers often map
        # thumb to landscape fanart, which makes inactive cards turn into short,
        # cropped strips while the selected row still appears portrait.
        set_child_text(normal_image, "texture", "$INFO[ListItem.Art(poster)]")
        normal_texture = normal_image.find("texture")
        if normal_texture is None:
            raise SystemExit("Includes.xml normal poster image has no texture")
        normal_texture.set("fallback", "poster-placeholder.png")
        for tag, value in (("left", 0), ("top", 350), ("width", 285), ("height", 64), ("align", "center"), ("aligny", "center"), ("font", "font10"), ("textcolor", "lightgrey")):
            set_child_text(normal_label, tag, value)
        stale_visibility = normal_label.find("visible")
        if stale_visibility is not None:
            normal_label.remove(stale_visibility)
        stale_wrap = normal_label.find("wrap")
        if stale_wrap is not None:
            normal_label.remove(stale_wrap)
        stale_multiline = normal_label.find("wrapmultiline")
        if stale_multiline is not None:
            normal_label.remove(stale_multiline)
        set_child_text(normal_label, "textcolor", "gainsboro")
        set_child_text(normal_label, "visible", "!ListItem.IsSelected")
        # Netflix-style resume progress belongs to every in-progress card, not
        # only the currently focused poster. Use a charcoal track beneath the
        # familiar red played segment so it does not read as a white underline.
        set_child_text(progress, "texturebg", "resume-track.png")
        set_child_text(progress, "midtexture", "focus-bar.png")
        normal_progress = normal.find("./control[@type='progress']")
        if normal_progress is None:
            normal_progress = ET.fromstring(ET.tostring(progress, encoding="unicode"))
            normal.append(normal_progress)
        for tag, value in (("left", 18), ("top", 337), ("width", 249), ("height", 5)):
            set_child_text(normal_progress, tag, value)
        set_child_text(normal_progress, "info", "ListItem.PercentPlayed")
        set_child_text(normal_progress, "visible", "ListItem.IsResumable")
        set_child_text(normal_progress, "texturebg", "resume-track.png")
        set_child_text(normal_progress, "midtexture", "focus-bar.png")
        set_child_text(normal_progress, "overlaytexture", "-")
        # Keep the selected artwork prominent without letting its zoom cover
        # the title below it. The 104% control geometry plus a 104% focus
        # animation gives a balanced ~108% total scale instead of double-enlarging
        # an already oversized 108% control.
        for tag, value in (("left", 9), ("top", -3), ("width", 267), ("height", 355)):
            set_child_text(focused_image, tag, value)
        set_child_text(focused_image, "texture", "$INFO[ListItem.Art(poster)]")
        focused_texture = focused_image.find("texture")
        if focused_texture is None:
            raise SystemExit("Includes.xml focused poster image has no texture")
        focused_texture.set("fallback", "poster-placeholder.png")
        # Focused poster geometry already provides a subtle 4% emphasis.
        # Remove the extra animated zoom so Fire TV does not resample a large
        # poster texture on every focus transition.
        for focus_animation in list(focused_image.findall("./animation")):
            focused_image.remove(focus_animation)
        for tag, value in (("left", 18), ("width", 249), ("top", 345), ("height", 5)):
            set_child_text(progress, tag, value)
        if focused_label is not None and focused_label in list(focused):
            focused.remove(focused_label)
        for container_id in (9001, 9002, 9003, 9004):
            include_name = f"CinevaFocusedPosterItem{container_id}"
            previous = root.find(f"./include[@name='{include_name}']")
            if previous is not None:
                root.remove(previous)
            clone = ET.fromstring(ET.tostring(focused, encoding="unicode"))
            clone.set("name", include_name)
            # A fixed list remembers a selected item even while another rail has
            # focus. Give that inactive selection its normal poster/title, and
            # show the zoom/border/bright title only in the actively focused rail.
            fallback_image = ET.fromstring(ET.tostring(normal_image, encoding="unicode"))
            active_image = ET.fromstring(ET.tostring(focused_image, encoding="unicode"))
            fallback_label = ET.fromstring(ET.tostring(normal_label, encoding="unicode"))
            active_label = ET.fromstring(ET.tostring(focused_label, encoding="unicode"))
            fallback_progress = ET.fromstring(ET.tostring(normal_progress, encoding="unicode"))
            clone_progress = ET.fromstring(ET.tostring(progress, encoding="unicode"))
            set_child_text(fallback_image, "visible", f"!Control.HasFocus({container_id})")
            set_child_text(active_image, "visible", f"Control.HasFocus({container_id})")
            set_child_text(fallback_label, "visible", f"!Control.HasFocus({container_id})")
            set_child_text(fallback_progress, "visible", f"!Control.HasFocus({container_id}) + ListItem.IsResumable")
            # Reserve a 64px caption area for two full lines at TV distance; row and item geometry below keep it clear of the next shelf.
            for tag, value in (("left", 0), ("top", 362), ("width", 285), ("height", 64), ("align", "center"), ("aligny", "center"), ("font", "font10"), ("textcolor", "white")):
                set_child_text(active_label, tag, value)
            stale_wrap = active_label.find("wrap")
            if stale_wrap is not None:
                active_label.remove(stale_wrap)
            stale_multiline = active_label.find("wrapmultiline")
            if stale_multiline is not None:
                active_label.remove(stale_multiline)
            set_child_text(active_label, "visible", f"Control.HasFocus({container_id})")
            set_child_text(clone_progress, "visible", f"Control.HasFocus({container_id}) + ListItem.IsResumable")
            focus_accent = ET.Element("control", {"type": "image"})
            for tag, value in (("left", 101), ("top", 433), ("width", 84), ("height", 4)):
                set_child_text(focus_accent, tag, value)
            set_child_text(focus_accent, "texture", "focus-bar.png")
            set_child_text(focus_accent, "visible", f"Control.HasFocus({container_id})")
            for child in list(clone.findall("control")):
                clone.remove(child)
            for child in (fallback_image, active_image, fallback_label, active_label, fallback_progress, clone_progress, focus_accent):
                clone.append(child)
            root.append(clone)
    elif path == "skin.cineva/xml/SkinSettings.xml":
        # Replace the legacy broad widget-manager links with twelve direct,
        # numbered slot actions. This makes each screen's four sources editable
        # from the skin's own Settings window without a separate My Widgets hub.
        controls = root.find("controls")
        if controls is None:
            raise SystemExit("SkinSettings.xml is missing its controls container")
        for stale in list(controls.findall("control")):
            if stale.get("id") in {"6", "7", "8", "9", "10"}:
                controls.remove(stale)
        headings = {
            "home": ("HOME WIDGETS", 96, "Cineva.Widget"),
            "movies": ("MOVIES WIDGETS", 704, "Cineva.MovieWidget"),
            "tvshows": ("TV SHOWS WIDGETS", 1312, "Cineva.ShowWidget"),
        }
        for screen, (heading, left, string_prefix) in headings.items():
            section = ET.Element("control", {"type": "label"})
            for tag, value in (("left", left), ("top", 238), ("width", 520),
                               ("height", 42), ("font", "font18"),
                               ("textcolor", "white"), ("label", heading)):
                set_child_text(section, tag, value)
            controls.append(section)
            for slot in range(1, 5):
                button = ET.Element("control", {"type": "button", "id": str(20 + (list(headings).index(screen) * 4) + slot)})
                for tag, value in (("left", left), ("top", 300 + (slot - 1) * 82),
                                   ("width", 520), ("height", 64), ("font", "font14"),
                                   ("label", f"WIDGET {slot}  ·  $INFO[Skin.String({string_prefix}{slot}.Name)]"),
                                   ("texturefocus", "focus-bar.png"),
                                   ("texturenofocus", "black.png"),
                                   ("textcolor", "white"), ("focusedcolor", "white"),
                                   ("onclick", f"RunScript(script.cineva.widgets,action=configure&screen={screen}&slot={slot})")):
                    set_child_text(button, tag, value)
                controls.append(button)
        # A concise hint explains that each action opens the add-on/folder picker.
        hint = ET.Element("control", {"type": "label"})
        for tag, value in (("left", 96), ("top", 690), ("width", 1500),
                           ("height", 44), ("font", "font12"),
                           ("textcolor", "grey"), ("label", "Choose a slot to select, change or clear its video add-on source.")):
            set_child_text(hint, tag, value)
        controls.append(hint)
    elif path == "skin.cineva/xml/Font.xml":
        fontset = root.find("./fontset[@id='Default']")
        if fontset is None:
            raise SystemExit("Font.xml is missing its Default fontset")
        compact = next((node for node in fontset.findall("font") if node.findtext("name") == "font9"), None)
        if compact is None:
            compact = ET.SubElement(fontset, "font")
        set_child_text(compact, "name", "font9")
        set_child_text(compact, "filename", "Lato-Regular.ttf")
        set_child_text(compact, "size", 17)
        # Replace the generic Roboto stack with a consistent Lato family:
        # Black for cinematic headlines, Semibold for navigation/shelves,
        # and Regular for long-form synopsis and supporting copy.
        scale = {
            "font9": ("Lato-Regular.ttf", 17),
            "font10": ("Poppins-SemiBold.ttf", 19),
            "font12": ("Poppins-Medium.ttf", 18),
            "font13": ("Lato-Regular.ttf", 24),
            "font14": ("Lato-Regular.ttf", 27),
            "font16": ("Poppins-SemiBold.ttf", 29),
            "font18": ("Poppins-SemiBold.ttf", 34),
            "font20": ("Poppins-SemiBold.ttf", 38),
            "font22": ("Poppins-ExtraBold.ttf", 40),
            "font24": ("Poppins-ExtraBold.ttf", 46),
            "font30": ("Poppins-ExtraBold.ttf", 58),
            "font36": ("Poppins-ExtraBold.ttf", 68),
        }
        for name, (filename, size) in scale.items():
            node = next((item for item in fontset.findall("font")
                         if item.findtext("name") == name), None)
            if node is None:
                node = ET.SubElement(fontset, "font")
            set_child_text(node, "name", name)
            set_child_text(node, "filename", filename)
            set_child_text(node, "size", size)
    elif path == "skin.cineva/xml/DialogConfirm.xml":
        default = root.find("defaultcontrol")
        if default is None:
            default = ET.Element("defaultcontrol")
            root.insert(0, default)
        # Runtime JSON-RPC confirms control 11 is Yes and control 10 is No.
        default.set("always", "true")
        default.text = "11"
        # The skin has no bundled default button textures. Supply explicit
        # textures and colors so Yes/No are actually visible in the modal.
        for button in root.findall(".//control[@type='button']"):
            values = {
                "texturefocus": "focus-bar.png",
                "texturenofocus": "black.png",
                "textcolor": "white",
                "focusedcolor": "white",
                "align": "center",
                "aligny": "center",
            }
            for tag, value in values.items():
                node = button.find(tag)
                if node is None:
                    node = ET.SubElement(button, tag)
                node.text = value
    elif path == "skin.cineva/xml/Startup.xml":
        # The old startup panel had no content but was the default focus target.
        root.clear()
        root.set("id", "12999")
        # Startup remains the topmost window after a skin switch unless it
        # explicitly hands off to Home. This leaves the Home UI underneath but
        # keeps currentwindow=Startup and prevents Home navigation focus.
        ET.SubElement(root, "onload").text = "ActivateWindow(Home)"
        controls = ET.SubElement(root, "controls")
        ET.SubElement(controls, "include").text = "CinevaBackground"
        ET.SubElement(controls, "include").text = "CinevaTopBar"
    elif path == "skin.cineva/xml/MyVideoNav.xml":
        # Unified cinematic catalogue: larger portrait cards, generous gutters,
        # restrained metadata and a full-width grid that uses the screen.
        panel = root.find("./controls/control[@type='panel']")
        if panel is not None:
            set_child_text(panel, "left", 54)
            set_child_text(panel, "top", 252)
            set_child_text(panel, "width", 1812)
            set_child_text(panel, "height", 790)
            for layout in panel.findall("./itemlayout") + panel.findall("./focusedlayout"):
                layout.set("width", "330")
                layout.set("height", "390")
                for child in layout.findall("control"):
                    if child.get("type") == "image":
                        set_child_text(child, "left", 38)
                        set_child_text(child, "top", 0)
                        set_child_text(child, "width", 244)
                        set_child_text(child, "height", 354)
                    elif child.get("type") == "label":
                        set_child_text(child, "left", 12)
                        set_child_text(child, "top", 356)
                        set_child_text(child, "width", 306)
                        set_child_text(child, "height", 30)
                        set_child_text(child, "align", "center")
        title = root.find("./controls/control[@type='label']")
        if title is not None:
            set_child_text(title, "left", 72)
            set_child_text(title, "top", 138)
            set_child_text(title, "font", "font30")
    elif path == "skin.cineva/xml/Home.xml":
        # Kodi treats '-' as a literal texture filename and logs a missing
        # texture for every transparent navigation button. Omit the no-focus
        # texture entirely; Kodi renders the button text without a background.
        remove_missing_no_focus_textures(root)
    elif path == "skin.cineva/xml/DialogVideoInfo.xml":
        # Full-bleed detail composition with readable copy and a clear primary action.
        for node in root.findall("./controls/control"):
            kind = node.get("type")
            if kind == "image":
                if node.findtext("texture", "").startswith("$INFO[ListItem.Art(poster)]"):
                    for tag, value in (("left", 1240), ("top", 100), ("width", 470), ("height", 710)):
                        set_child_text(node, tag, value)
            elif kind == "label":
                label = node.findtext("label", "")
                if "$INFO[ListItem.Label]" in label:
                    for tag, value in (("left", 100), ("top", 150), ("width", 1040), ("height", 112)):
                        set_child_text(node, tag, value)
                    set_child_text(node, "font", "font40")
                elif "$INFO[ListItem.Year]" in label:
                    for tag, value in (("left", 104), ("top", 270), ("width", 1040), ("height", 44)):
                        set_child_text(node, tag, value)
            elif kind == "textbox":
                for tag, value in (("left", 104), ("top", 350), ("width", 1000), ("height", 300)):
                    set_child_text(node, tag, value)
            elif kind == "button":
                for tag, value in (("left", 104), ("top", 760), ("width", 300), ("height", 70)):
                    set_child_text(node, tag, value)
                set_child_text(node, "font", "font16")
                set_child_text(node, "texturefocus", "focus-bar.png")
                set_child_text(node, "texturenofocus", "black.png")
                set_child_text(node, "textcolor", "white")
    elif path == "skin.cineva/xml/VideoOSD.xml":
        # Premium, low-profile playback overlay with a long seek bar and legible controls.
        for node in root.findall("./controls/control"):
            if node.get("type") == "image":
                set_child_text(node, "top", 720)
                set_child_text(node, "height", 360)
            elif node.get("type") == "label":
                set_child_text(node, "left", 80)
                if "$INFO[VideoPlayer.Title]" in node.findtext("label", ""):
                    set_child_text(node, "top", 770)
                    set_child_text(node, "font", "font20")
                else:
                    set_child_text(node, "top", 826)
            elif node.get("type") == "progress":
                set_child_text(node, "left", 80)
                set_child_text(node, "top", 880)
                set_child_text(node, "width", 1760)
            elif node.get("type") == "group":
                set_child_text(node, "left", 80)
                set_child_text(node, "top", 920)
                for button in node.findall("./control[@type='button']"):
                    set_child_text(button, "height", 64)
                    set_child_text(button, "texturefocus", "focus-bar.png")
                    set_child_text(button, "texturenofocus", "black.png")
                    set_child_text(button, "textcolor", "white")
    elif path in {"skin.cineva/xml/custom11117.xml", "skin.cineva/xml/custom11118.xml"}:
        # Give catalogue pages a true selected-title hero instead of a static
        # category heading over four compressed poster strips.
        is_tv = path.endswith("custom11118.xml")
        controls = root.find("controls")
        if controls is not None:
            page_title = "TV SHOWS" if is_tv else "MOVIES"
            title = ET.Element("control", {"type": "label", "id": "9210"})
            for tag, value in {
                "left": 72, "top": 205, "width": 1120, "height": 64,
                "font": "font26", "textcolor": "white",
                "label": "$INFO[Container(9201).ListItem.Label]",
                "visible": "!String.IsEmpty(Container(9201).ListItem.Label) + !Control.HasFocus(9202) + !Control.HasFocus(9203) + !Control.HasFocus(9204)",
                "scroll": "no",
            }.items():
                ET.SubElement(title, tag).text = str(value)
            fallback = ET.Element("control", {"type": "label", "id": "9211"})
            for tag, value in {
                "left": 72, "top": 205, "width": 1120, "height": 64,
                "font": "font26", "textcolor": "white",
                "label": page_title,
                "visible": "String.IsEmpty(Container(9201).ListItem.Label)",
            }.items():
                ET.SubElement(fallback, tag).text = str(value)
            meta = ET.Element("control", {"type": "label", "id": "9212"})
            for tag, value in {
                "left": 76, "top": 270, "width": 1100, "height": 30,
                "font": "font10", "textcolor": "silver",
                "label": "$INFO[Container(9201).ListItem.Year]$INFO[Container(9201).ListItem.Genre,  ￼  ]$INFO[Container(9201).ListItem.Rating,  ￼  ]",
                "visible": "!String.IsEmpty(Container(9201).ListItem.Label)",
            }.items():
                ET.SubElement(meta, tag).text = str(value).replace("￼", "•")
            logo = ET.Element("control", {"type": "image", "id": "9213"})
            for tag, value in {
                "left": 72, "top": 205, "width": 850, "height": 64,
                "texture": "$INFO[Container(9201).ListItem.Art(clearlogo)]",
                "aspectratio": "keep",
                "visible": "!String.IsEmpty(Container(9201).ListItem.Art(clearlogo))",
            }.items():
                ET.SubElement(logo, tag).text = str(value)
            # Render hero information above the background and below focusable
            # controls; all focus movement remains native Kodi D-pad navigation.
            controls.extend([title, fallback, meta, logo])
    elif path == "skin.cineva/xml/custom11112.xml":
        # Search hub: keep the search action prominent and align results to the catalogue grid.
        for node in root.findall(".//control[@type='button']"):
            set_child_text(node, "texturefocus", "focus-bar.png")
            set_child_text(node, "texturenofocus", "black.png")
            set_child_text(node, "textcolor", "white")
            set_child_text(node, "focusedcolor", "white")
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def main():
    if not ARCHIVE.is_file() or ARCHIVE.stat().st_size == 0:
        raise SystemExit("Missing skin.cineva-0.5.3.zip")
    fd, tmp_name = tempfile.mkstemp(prefix="cineva-skin-", suffix=".zip", dir=str(ARCHIVE.parent))
    os.close(fd)
    tmp = Path(tmp_name)
    changed = []
    try:
        with ZipFile(ARCHIVE, "r") as source, ZipFile(tmp, "w", ZIP_DEFLATED, compresslevel=9) as target:
            names = set(source.namelist())
            required = {
                "skin.cineva/addon.xml",
                "skin.cineva/xml/Home.xml",
                "skin.cineva/xml/DialogConfirm.xml",
                "skin.cineva/xml/Includes.xml",
                "skin.cineva/xml/SkinSettings.xml",
                "skin.cineva/xml/Font.xml",
                "skin.cineva/xml/MyVideoNav.xml",
                "skin.cineva/xml/DialogVideoInfo.xml",
                "skin.cineva/xml/VideoOSD.xml",
                "skin.cineva/xml/custom11112.xml",
                "skin.cineva/xml/custom11117.xml",
                "skin.cineva/xml/custom11118.xml",
                "skin.cineva/xml/Startup.xml",
            }
            missing = sorted(required - names)
            if missing:
                raise SystemExit("Skin archive is missing: " + ", ".join(missing))
            # Bundle the licensed Lato typeface into the installable skin. Fetch
            # pinned static files from the Google Fonts repository during build.
            font_base = "https://raw.githubusercontent.com/google/fonts/main/ofl/lato/"
            font_assets = {
                "skin.cineva/fonts/Lato-Regular.ttf": "Lato-Regular.ttf",
                "skin.cineva/fonts/Lato-SemiBold.ttf": "Lato-SemiBold.ttf",
                "skin.cineva/fonts/Lato-Black.ttf": "Lato-Black.ttf",
                "skin.cineva/fonts/OFL.txt": "OFL.txt",
            }
            # Poppins supplies the stronger display voice; Lato remains the
            # quieter, highly legible reading face for synopsis and long copy.
            poppins_base = "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/"
            poppins_assets = {
                "skin.cineva/fonts/Poppins-Medium.ttf": "Poppins-Medium.ttf",
                "skin.cineva/fonts/Poppins-SemiBold.ttf": "Poppins-SemiBold.ttf",
                "skin.cineva/fonts/Poppins-ExtraBold.ttf": "Poppins-ExtraBold.ttf",
                "skin.cineva/fonts/Poppins-OFL.txt": "OFL.txt",
            }
            generated_assets = {
                **{path: fetch_asset(font_base + filename)
                   for path, filename in font_assets.items()},
                **{path: fetch_asset(poppins_base + filename)
                   for path, filename in poppins_assets.items()},
                "skin.cineva/media/hero-left-shade.png": hero_left_shade_png(),
                "skin.cineva/media/hero-topbar-shade.png": hero_topbar_shade_png(),
                "skin.cineva/media/hero-bottom-fade.png": hero_bottom_fade_png(),
                "skin.cineva/media/hero-placeholder.png": hero_placeholder_png(),
                "skin.cineva/media/hero-poster-vignette.png": hero_poster_vignette_png(),
                "skin.cineva/media/rail-scroll-mask.png": rail_scroll_mask_png(),
                "skin.cineva/media/resume-track.png": resume_track_png(),
                "skin.cineva/media/poster-focus.png": poster_focus_png(),
                "skin.cineva/media/poster-placeholder.png": poster_placeholder_png(),
            }
            written_assets = set()
            for info in source.infolist():
                if info.filename == "skin.cineva/xml/CinevaWidgetHub.xml":
                    changed.append(info.filename + " (removed obsolete My Widgets hub)")
                    continue
                data = source.read(info.filename)
                if info.filename in generated_assets:
                    generated = generated_assets[info.filename]
                    if data != generated:
                        changed.append(info.filename)
                    data = generated
                    written_assets.add(info.filename)
                if info.filename in required:
                    updated = update_xml(data, info.filename)
                    if updated != data:
                        changed.append(info.filename)
                    data = updated
                target.writestr(info, data)
            for asset_name, asset_data in generated_assets.items():
                if asset_name not in written_assets:
                    target.writestr(asset_name, asset_data, compress_type=ZIP_DEFLATED)
                    changed.append(asset_name)
        if changed:
            os.replace(tmp, ARCHIVE)
            print("Updated release ZIP entries:", ", ".join(changed))
        else:
            print("Release ZIP already contains all runtime fixes; no rewrite needed.")
    finally:
        if tmp.exists():
            tmp.unlink()


if __name__ == "__main__":
    main()
