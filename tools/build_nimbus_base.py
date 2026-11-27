#!/usr/bin/env python3
"""Build a reproducible CINÉVA foundation from the pinned Nimbus source.

Nimbus is the upstream UI foundation. Its GPL code and CC BY-SA artwork notices
are retained. The Nimbus Helper is reduced to local menu/widget/search functions;
its MDBList/TMDb rating service and API modules are deliberately not packaged.
"""
from __future__ import annotations

import ast
import io
import json
import re
import shutil
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
NIMBUS_REPO = "ivarbrandt/skin.nimbus"
NIMBUS_SHA = "8b5071b8cd0db3a8e813eb00e9a821d3efad2454"
HELPER_REPO = "ivarbrandt/script.nimbus.helper"
HELPER_SHA = "e42d2ffffbccaa58386ef2e4a054049e5fcb7664"
SKIN_VERSION = "0.6.9"
BRIDGE_VERSION = "0.1.0"
OUT_DIR = ROOT / "dist" / "nimbus-foundation"
NOTICE = """CINÉVA Nimbus foundation

CINÉVA's visual and layout foundation is derived from Nimbus by Ivar Brandt.
Nimbus code: GNU General Public License, version 2.0.
Nimbus artwork: Creative Commons Attribution-ShareAlike 4.0.
Upstream skin: https://github.com/ivarbrandt/skin.nimbus
Upstream helper: https://github.com/ivarbrandt/script.nimbus.helper

The CINÉVA Nimbus Bridge retains local widget/menu path generation and search
history functions. A minimal local-only Kodi service entry is kept so Kodi can
resolve the bridge dependency; it performs no network work. The upstream
MDBList/TMDb rating service and API modules are not included. CINÉVA renders
Kodi ListItems and does not make those API calls.
"""

TEXT_SUFFIXES = {".xml", ".py", ".txt", ".md", ".po", ".json"}
API_FUNCTIONS = {
    "check_api_key",
    "validate_api_key",
    "set_api_key",
    "check_api_key_on_load",
}
SAFE_CUSTOM_ACTIONS = {
    "show_changelog",
    "set_widget_count",
    "set_image",
    "play_trailer",
    "fix_black_screen",
    "set_blurradius",
    "set_blursaturation",
    "set_autoendplaybackdelay",
    "capture_user_key",
    "modify_keymap",
}

# Nimbus Includes.xml loads these files before the first-run welcome dialog can
# invoke remake_all_cpaths(). Ship empty defaults so the first skin parse is
# clean; the local bridge replaces them with configured paths later.
DEFAULT_SKIN_INCLUDE_NAMES = {
    "script-nimbus-widget_movies": "MovieWidgets",
    "script-nimbus-widget_tvshows": "TVShowWidgets",
    "script-nimbus-widget_custom1": "Custom1Widgets",
    "script-nimbus-widget_custom2": "Custom2Widgets",
    "script-nimbus-widget_custom3": "Custom3Widgets",
    "script-nimbus-main_menu_movies": "MoviesMainMenu",
    "script-nimbus-main_menu_tvshows": "TVShowsMainMenu",
    "script-nimbus-main_menu_custom1": "Custom1MainMenu",
    "script-nimbus-main_menu_custom2": "Custom2MainMenu",
    "script-nimbus-main_menu_custom3": "Custom3MainMenu",
}


def fetch_archive(repository: str, commit: str) -> bytes:
    """Download a pinned GitHub source archive with a clear, bounded request."""
    url = f"https://codeload.github.com/{repository}/zip/{commit}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "CINEVA-Nimbus-Builder/1.0"}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read()
    if not data.startswith(b"PK"):
        raise RuntimeError(f"GitHub did not return a ZIP archive for {repository}@{commit}")
    return data


def extract_archive(data: bytes, destination: Path) -> None:
    """Extract one GitHub ZIP root safely, without trusting archive paths."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    with ZipFile(io.BytesIO(data)) as archive:
        names = [name for name in archive.namelist() if name and not name.endswith("/")]
        roots = {PurePosixPath(name).parts[0] for name in names}
        if len(roots) != 1:
            raise RuntimeError(f"Expected one source root in archive, found {sorted(roots)}")
        root = next(iter(roots))
        for info in archive.infolist():
            parts = PurePosixPath(info.filename).parts
            if not parts or parts[0] != root or len(parts) == 1 or info.is_dir():
                continue
            relative = PurePosixPath(*parts[1:])
            if any(part in {"", ".", ".."} for part in relative.parts):
                raise RuntimeError(f"Unsafe archive path: {info.filename}")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))


def patch_text_tree(root: Path, replacements: tuple[tuple[str, str], ...]) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        original = text
        for old, new in replacements:
            text = text.replace(old, new)
        if text != original:
            path.write_text(text, encoding="utf-8", newline="")


def set_child_text(parent: ET.Element, tag: str, value: str) -> None:
    node = parent.find(tag)
    if node is None:
        node = ET.SubElement(parent, tag)
    node.text = value


def patch_skin_manifest(skin_root: Path) -> None:
    manifest_path = skin_root / "addon.xml"
    root = ET.parse(manifest_path).getroot()
    root.set("id", "skin.cineva")
    root.set("name", "CINÉVA")
    root.set("version", SKIN_VERSION)
    root.set("provider-name", "CINÉVA Project; based on Nimbus by Ivar Brandt")

    requires = root.find("requires")
    if requires is None:
        requires = ET.SubElement(root, "requires")
    imports = list(requires.findall("import"))
    found_gui = False
    found_bridge = False
    for item in imports:
        addon_id = item.get("addon", "")
        if addon_id == "xbmc.gui":
            item.set("version", "5.18.0")
            found_gui = True
        elif addon_id == "script.cineva.nimbus":
            item.set("version", BRIDGE_VERSION)
            found_bridge = True
        elif addon_id != "xbmc.python":
            requires.remove(item)
    if not found_gui:
        ET.SubElement(requires, "import", {"addon": "xbmc.gui", "version": "5.18.0"})
    if not found_bridge:
        ET.SubElement(
            requires, "import",
            {"addon": "script.cineva.nimbus", "version": BRIDGE_VERSION},
        )

    metadata = root.find("./extension[@point='xbmc.addon.metadata']")
    if metadata is not None:
        set_child_text(metadata, "license", "GPL-2.0-only; artwork CC BY-SA 4.0")
        set_child_text(metadata, "summary", "CINÉVA cinematic Kodi skin, based on Nimbus")
        set_child_text(
            metadata,
            "description",
            "A remote-first cinematic Kodi skin based on Nimbus by Ivar Brandt.",
        )
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(manifest_path, encoding="UTF-8", xml_declaration=True)



def add_list_id_to_include_calls(
    path: Path,
    include_name: str,
    list_id: str,
    expected: int,
    rename_params: tuple[tuple[str, str], ...] = (),
) -> None:
    """Bind focus-sensitive Nimbus layout includes to their owning container."""
    text = path.read_text(encoding="utf-8")
    changed = 0

    plain_pattern = re.compile(
        r"<include>\s*" + re.escape(include_name) + r"\s*</include>"
    )

    def replace_plain(match: re.Match[str]) -> str:
        nonlocal changed
        start = match.start()
        line_start = text.rfind("\n", 0, start) + 1
        indent = text[line_start:start]
        changed += 1
        if indent.strip():
            return (
                f'<include content="{include_name}">'
                f'<param name="list_id" value="{list_id}" /></include>'
            )
        param_indent = indent + "\t"
        return (
            f'<include content="{include_name}">\n'
            f'{param_indent}<param name="list_id" value="{list_id}" />\n'
            f'{indent}</include>'
        )

    text = plain_pattern.sub(replace_plain, text)
    content_pattern = re.compile(
        r'<include(?P<attrs>[^>]*\bcontent="'
        + re.escape(include_name)
        + r'"[^>]*)>'
        r'(?P<body>(?:\s*<param\b[^>]*/>\s*)*)</include>',
        re.S,
    )

    def replace_content(match: re.Match[str]) -> str:
        nonlocal changed
        body = match.group("body")
        if re.search(r'<param\s+name="list_id"', body):
            return match.group(0)
        for old_name, new_name in rename_params:
            body = body.replace(f'name="{old_name}"', f'name="{new_name}"')
        position = body.find("<param")
        if position < 0:
            start = match.start()
            line_start = text.rfind("\n", 0, start) + 1
            indent = text[line_start:start]
            param_indent = indent + "\t"
            body = (
                f"\n{param_indent}<param name=\"list_id\" value=\"{list_id}\" />"
                f"\n{indent}"
            )
        else:
            param_line_start = body.rfind("\n", 0, position) + 1
            param_indent = body[param_line_start:position]
            body = (
                body[:position]
                + f'<param name="list_id" value="{list_id}" />\n{param_indent}'
                + body[position:]
            )
        changed += 1
        return f'<include{match.group("attrs")}>{body}</include>'

    text = content_pattern.sub(replace_content, text)
    if changed != expected:
        raise RuntimeError(
            f"{path.name}: expected {expected} {include_name} focus bindings, changed {changed}"
        )
    path.write_text(text, encoding="utf-8", newline="")
    ET.parse(path)


def patch_nimbus_focus_include_ids(skin_root: Path) -> None:
    """Fix upstream Flix layouts that omit the list ID used by focus expressions."""
    xml_root = skin_root / "xml"
    patches = (
        ("Includes.xml", "FlixSquareLayout", "$PARAM[group_id]50", 2,
         (("fallback_image", "fallback_icon"),)),
        ("View_54_Flix.xml", "FlixMovieLayout", "54", 2, ()),
        ("View_500_Wall.xml", "FlixMovieLayout", "500", 2, ()),
        ("View_55_FlixScape.xml", "FlixScapeMovieLayout", "55", 2, ()),
        ("View_501_WallScape.xml", "FlixScapeMovieLayout", "501", 2, ()),
        ("View_51_PosterFlow.xml", "PosterFlowLayout", "51", 2, ()),
        ("View_50_List.xml", "ListLandscapeSlideAnimations", "$PARAM[list_id]", 1, ()),
    )
    for filename, include_name, list_id, expected, renames in patches:
        path = xml_root / filename
        if not path.is_file():
            raise RuntimeError(f"Nimbus source is missing focus-layout file: {filename}")
        add_list_id_to_include_calls(path, include_name, list_id, expected, renames)



def patch_nimbus_include_list_id_defaults(skin_root: Path) -> None:
    """Add valid Kodi include params and wrap their bodies in <definition>."""
    xml_root = skin_root / "xml"
    tag_pattern = re.compile(r"</?include\b[^>]*>")

    for path in xml_root.glob("*.xml"):
        text = path.read_text(encoding="utf-8")
        scan_text = re.sub(
            r"<!--.*?-->",
            lambda match: " " * len(match.group(0)),
            text,
            flags=re.S,
        )

        blocks: list[tuple[int, int]] = []
        depth = 0
        current_start = None
        for tag in tag_pattern.finditer(scan_text):
            token = tag.group(0)
            if token.startswith("</"):
                if depth:
                    depth -= 1
                    if depth == 0 and current_start is not None:
                        blocks.append((current_start, tag.end()))
                        current_start = None
            elif not token.rstrip().endswith("/>"):
                if depth == 0:
                    current_start = tag.start()
                depth += 1

        replacements: list[tuple[int, int, str]] = []
        for block_start, block_end in blocks:
            block = text[block_start:block_end]
            if "$PARAM[list_id]" not in block:
                continue
            try:
                parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
                include = ET.fromstring(block, parser=parser)
            except ET.ParseError as exc:
                raise RuntimeError(
                    f"{path.name}: invalid include definition: {exc}"
                ) from exc

            if include.tag != "include" or not include.get("name"):
                continue

            children = list(include)
            params = [child for child in children if child.tag == "param"]
            list_params = [param for param in params if param.get("name") == "list_id"]
            if len(list_params) > 1:
                raise RuntimeError(
                    f"{path.name}: duplicate list_id params in {include.get('name')}"
                )

            if list_params:
                list_param = list_params[0]
                legacy_value = list_param.attrib.pop("value", None)
                if not list_param.get("default"):
                    list_param.set("default", legacy_value or "999999")
            else:
                list_param = ET.Element(
                    "param",
                    {"name": "list_id", "default": "999999"},
                )
                params.append(list_param)

            definition = next(
                (child for child in children if child.tag == "definition"),
                None,
            )
            body_children = [
                child for child in children
                if child.tag not in ("param", "definition")
            ]
            if definition is None:
                definition = ET.Element("definition")
            for child in body_children:
                include.remove(child)
                definition.append(child)

            for child in list(include):
                include.remove(child)
            for param in params:
                include.append(param)
            include.append(definition)

            ET.indent(include, space="\t")
            replacements.append(
                (block_start, block_end, ET.tostring(include, encoding="unicode"))
            )

        for block_start, block_end, new_block in reversed(replacements):
            text = text[:block_start] + new_block + text[block_end:]
        if replacements:
            path.write_text(text, encoding="utf-8", newline="")
            ET.parse(path)


def apply_cineva_visuals(skin_root: Path) -> None:
    """Apply CINÉVA's Netflix-inspired presentation without replacing Nimbus UI logic."""
    colors_path = skin_root / "colors" / "defaults.xml"
    if not colors_path.is_file():
        raise RuntimeError("Nimbus source is missing colors/defaults.xml")
    palette = {
        "primary_background": "FF080808",
        "dialog_tint": "FF050505",
        "dialog_bg": "E6080808",
        "dialog_bg2": "F2080808",
        "dialog_bg3": "F7080808",
        "button_focus": "FFE50914",
        "button_focus2": "FF080808",
        "focused_text": "FF080808",
        "unfocused_text": "FFF5F5F1",
        "artwork_dim": "FFFFFFFF",
        "accent_color": "FFE50914",
        "selected": "FFE50914",
        "keyboard_selected": "FFE50914",
        "primary_content_panel_bg": "FF111111",
        "background": "FF000000",
        "bg_overlay": "99000000",
        "red": "FFE50914",
    }
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    color_tree = ET.parse(colors_path, parser=parser)
    color_root = color_tree.getroot()
    for name, value in palette.items():
        matches = [node for node in color_root.findall("color") if node.get("name") == name]
        if len(matches) != 1:
            raise RuntimeError(
                f"colors/defaults.xml: expected one active {name} color, found {len(matches)}"
            )
        matches[0].text = value
    ET.indent(color_root, space="  ")
    color_tree.write(colors_path, encoding="UTF-8", xml_declaration=True)
    ET.parse(colors_path)

    home_path = skin_root / "xml" / "Home.xml"
    if not home_path.is_file():
        raise RuntimeError("Nimbus source is missing xml/Home.xml")
    home = home_path.read_text(encoding="utf-8")
    default_focus = "<defaultcontrol>9000</defaultcontrol>"
    content_focus = "<defaultcontrol>20000</defaultcontrol>"
    if home.count(default_focus) == 1 and home.count(content_focus) == 0:
        # Start on the first content widget, using Nimbus's own hidden focus bridge.
        # The left navigation remains fully available from the existing D-pad route.
        home = home.replace(default_focus, content_focus, 1)
    elif home.count(content_focus) != 1 or home.count(default_focus) != 0:
        raise RuntimeError("Nimbus Home must have exactly one supported default focus control")
    if 'id="19990"' in home:
        raise RuntimeError("CINÉVA wordmark control ID 19990 already exists upstream")
    brand = """
        <control type="group" id="19990">
            <left>68</left>
            <top>42</top>
            <width>430</width>
            <height>78</height>
            <visible>!Player.HasMedia</visible>
            <animation effect="fade" start="0" end="100" time="350">WindowOpen</animation>
            <control type="label">
                <left>0</left>
                <top>0</top>
                <width>430</width>
                <height>58</height>
                <font>font36_title</font>
                <textcolor>accent_color</textcolor>
                <shadowcolor>text_shadow</shadowcolor>
                <align>left</align>
                <aligny>center</aligny>
                <label>[B]CINÉVA[/B]</label>
            </control>
            <control type="image">
                <left>2</left>
                <top>63</top>
                <width>76</width>
                <height>4</height>
                <texture colordiffuse="accent_color">colors/white.png</texture>
            </control>
        </control>
"""
    marker = "</controls>"
    if home.count(marker) != 1:
        raise RuntimeError("Home.xml must contain exactly one controls closing tag")
    home = home.replace(marker, brand + "    " + marker, 1)
    ET.fromstring(home)
    home_path.write_text(home, encoding="utf-8", newline="")




def apply_cineva_home_layout(skin_root: Path) -> None:
    """Convert Nimbus Home to Netflix-style horizontal navigation and a larger hero."""
    xml_root = skin_root / "xml"
    home_path = xml_root / "Home.xml"
    home = home_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if 'id="9000"' not in home or 'id="2000"' not in home:
        return

    menu_group = """<control type="group">
					<left>-540</left>
					<animation type="Conditional" condition="!ControlGroup(2000).HasFocus + !Control.IsVisible(20000) + !Control.IsVisible(20001)" reversible="true">
						<effect type="slide" start="0" end="540" time="500" tween="cubic" easing="inout" />
					</animation>
					<include>OpenClose_Left</include>
					<include content="MenuContentPanel">
						<param name="width" value="549"/>
					</include>"""
    if menu_group not in home:
        raise RuntimeError("Home.xml: Nimbus main-menu panel structure changed")
    home = home.replace(menu_group, """<control type="group">
					<left>0</left>""", 1)

    patches = (
        ("<defaultcontrol>20000</defaultcontrol>", "<defaultcontrol>9000</defaultcontrol>"),
        ("<left>25</left>\n\t\t\t\t\t\t<top>215</top>\n            <width>825</width>\n\t\t\t\t\t\t<height>605</height>",
         "<left>270</left>\n\t\t\t\t\t\t<top>26</top>\n\t\t\t\t\t\t<width>1260</width>\n\t\t\t\t\t\t<height>82</height>\n\t\t\t\t\t\t<orientation>horizontal</orientation>"),
        ("<movement>7</movement>", "<movement>1</movement>"),
        ("<onright>SetFocus($INFO[Container(9000).ListItem.Property(menu_id)])</onright>",
         "<ondown>SetFocus($INFO[Container(9000).ListItem.Property(menu_id)])</ondown>"),
        ("<onback>700</onback>\n\t\t\t\t\t\t<onup>700</onup>\n\t\t\t\t\t\t<ondown>9000</ondown>",
         "<onback>9000</onback>\n\t\t\t\t\t\t<onup>700</onup>\n\t\t\t\t\t\t<onright>9000</onright>"),
        ("""<include content="List">
              <param name="id" value="9000" />
            </include>""",
         """<include content="CinevaMainMenuList">
							<param name="id" value="9000" />
						</include>"""),
    )
    for old, new in patches:
        if old not in home:
            raise RuntimeError(f"Home.xml: expected Nimbus menu fragment not found: {old[:80]!r}")
        home = home.replace(old, new, 1)

    if home.count("<top>510</top>") != 1:
        raise RuntimeError("Home.xml: expected one Nimbus widget-shelf anchor at y=510")
    home = home.replace("<top>510</top>", "<top>575</top>", 1)

    quick = """<control type="group">
						<left>65</left>
						<top>70</top>
						<width>343</width>"""
    if quick not in home:
        raise RuntimeError("Home.xml: Nimbus quick-action group geometry not found")
    home = home.replace(quick, """<control type="group">
						<left>1515</left>
						<top>18</top>
						<width>360</width>""", 1)

    flix_path = xml_root / "Includes_FlixPanel.xml"
    flix = flix_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    hero = '<left>50</left>\n\t\t\t\t<width>815</width>\n\t\t\t\t<top>45</top>'
    if hero not in flix:
        raise RuntimeError("Includes_FlixPanel.xml: Nimbus hero geometry not found")
    flix = flix.replace(hero, '<left>72</left>\n\t\t\t\t<width>900</width>\n\t\t\t\t<top>150</top>', 1)
    flix_path.write_text(flix, encoding="utf-8", newline="")
    ET.parse(flix_path)

    clock = '<control type="group">\n\t\t\t\t\t<top>90</top>\n\t\t\t\t\t<left>90</left>'
    if clock in home:
        home = home.replace(clock, '<control type="group">\n\t\t\t\t\t<visible>false</visible>\n\t\t\t\t\t<top>90</top>\n\t\t\t\t\t<left>90</left>', 1)
    rss = home.rfind('<control type="rss">')
    if rss >= 0:
        home = home[:rss] + home[rss:].replace('<control type="rss">', '<control type="rss">\n\t\t\t\t\t\t\t\t<visible>false</visible>', 1)

    ET.fromstring(home)
    home_path.write_text(home, encoding="utf-8", newline="")

    home_includes_path = xml_root / "Includes_Home.xml"
    home_includes = home_includes_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    common_group = """<include name="WidgetGroupListCommon">
		<orientation>vertical</orientation>
		<height>33000</height>
		<itemgap>-100</itemgap>
		<onup>20000</onup>
		<ondown>20001</ondown>
		<usecontrolcoords>true</usecontrolcoords>
	</include>"""
    if common_group not in home_includes:
        raise RuntimeError("Includes_Home.xml: Nimbus widget navigation include changed")
    home_includes = home_includes.replace(
        common_group,
        common_group.replace(
            "<usecontrolcoords>true</usecontrolcoords>",
            "<onback>SetFocus(9000)</onback>\n\t\t<usecontrolcoords>true</usecontrolcoords>",
        ),
        1,
    )
    ET.fromstring(home_includes)
    home_includes_path.write_text(home_includes, encoding="utf-8", newline="")

    (xml_root / "Includes_Cineva.xml").write_text("""<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="CinevaMainMenuList">
    <param name="id" default="9000" />
    <definition>
      <focusedlayout width="210" height="72">
        <control type="group">
          <control type="label">
            <left>12</left><top>0</top><width>186</width><height>62</height>
            <font>font23_title</font><textcolor>FFFFFFFF</textcolor>
            <align>center</align><aligny>center</aligny>
            <label>$VAR[MenuCaseVar]</label><shadowcolor>text_shadow</shadowcolor>
          </control>
          <control type="image">
            <left>86</left><bottom>2</bottom><width>38</width><height>4</height>
            <texture colordiffuse="accent_color">colors/white.png</texture>
          </control>
        </control>
      </focusedlayout>
      <itemlayout width="210" height="72">
        <control type="label">
          <left>12</left><top>0</top><width>186</width><height>62</height>
          <font>font23</font><textcolor>FFE0E0E0</textcolor>
          <align>center</align><aligny>center</aligny>
          <label>$VAR[MenuCaseVar]</label><shadowcolor>text_shadow</shadowcolor>
        </control>
      </itemlayout>
    </definition>
  </include>
</includes>
""", encoding="utf-8", newline="")
    ET.parse(xml_root / "Includes_Cineva.xml")


def write_default_skin_includes(skin_root: Path) -> None:
    """Ship empty Nimbus menu/widget includes before Kodi parses Includes.xml."""
    xml_root = skin_root / "xml"
    template = """<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="{include_name}">
  </include>
</includes>
"""
    for filename, include_name in DEFAULT_SKIN_INCLUDE_NAMES.items():
        path = xml_root / f"{filename}.xml"
        if not path.exists():
            path.write_text(
                template.format(include_name=include_name),
                encoding="utf-8",
                newline="",
            )


def remove_api_controls(skin_root: Path) -> None:
    path = skin_root / "xml" / "SkinSettings.xml"
    if not path.exists():
        return
    tree = ET.parse(path)
    root = tree.getroot()
    parent_map = {child: parent for parent in root.iter() for child in parent}
    blocked = (
        "mode=set_api_key",
        "mode=delete_all_ratings",
        "mode=check_api_key_on_load",
    )
    for node in list(root.iter()):
        if node.tag != "control":
            continue
        serialized = ET.tostring(node, encoding="unicode")
        if any(token in serialized for token in blocked):
            parent = parent_map.get(node)
            if parent is not None:
                parent.remove(node)
    tree.write(path, encoding="UTF-8", xml_declaration=True)


def remove_unsupported_startup_checks(skin_root: Path) -> None:
    path = skin_root / "xml" / "Includes_Home.xml"
    if not path.exists():
        return
    tree = ET.parse(path)
    root = tree.getroot()
    for parent in root.iter():
        for child in list(parent):
            if child.tag in {"onload", "onfocus"}:
                text = (child.text or "")
                if any(mode in text for mode in (
                    "mode=check_for_update",
                    "mode=check_for_profile_change",
                    "mode=check_api_key_on_load",
                )):
                    parent.remove(child)
    tree.write(path, encoding="UTF-8", xml_declaration=True)


def remove_functions(source: str, names: set[str]) -> str:
    """Remove selected top-level Python functions without altering other code."""
    tree = ast.parse(source)
    ranges = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            ranges.append((node.lineno, node.end_lineno))
    lines = source.splitlines(keepends=True)
    for start, end in sorted(ranges, reverse=True):
        del lines[start - 1:end]
    return "".join(lines)


def patch_helper_manifest(helper_root: Path) -> None:
    manifest_path = helper_root / "addon.xml"
    root = ET.parse(manifest_path).getroot()
    root.set("id", "script.cineva.nimbus")
    root.set("name", "CINÉVA Nimbus Bridge")
    root.set("version", BRIDGE_VERSION)
    root.set("provider-name", "CINÉVA Project; based on Nimbus Helper by Ivar Brandt")
    requires = root.find("requires")
    if requires is not None:
        for item in list(requires):
            if item.get("addon") != "xbmc.python":
                requires.remove(item)
    service_extension = root.find("./extension[@point='xbmc.service']")
    if service_extension is None:
        service_extension = ET.SubElement(root, "extension", {"point": "xbmc.service"})
    service_extension.set("library", "resources/lib/service.py")
    service_extension.set("start", "startup")
    metadata = root.find("./extension[@point='xbmc.addon.metadata']")
    if metadata is not None:
        set_child_text(metadata, "license", "GPL-2.0-only")
        set_child_text(metadata, "description", "Local widget, menu and search bridge for CINÉVA.")
        assets = metadata.find("assets")
        if assets is not None:
            metadata.remove(assets)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(manifest_path, encoding="UTF-8", xml_declaration=True)


def write_bridge(helper_source: Path, bridge_root: Path) -> None:
    selected = (
        "resources/lib/default.py",
        "resources/lib/modules/__init__.py",
        "resources/lib/modules/cpath_maker.py",
        "resources/lib/modules/search_utils.py",
        "resources/lib/modules/xmls.py",
        "resources/lib/modules/custom_actions.py",
    )
    bridge_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(helper_source / "addon.xml", bridge_root / "addon.xml")
    for relative in selected:
        source = helper_source / relative
        if not source.is_file():
            raise RuntimeError(f"Nimbus Helper source is missing required file: {relative}")
        target = bridge_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    patch_helper_manifest(bridge_root)
    patch_text_tree(
        bridge_root,
        (
            ("script.nimbus.helper", "script.cineva.nimbus"),
            ("skin.nimbus", "skin.cineva"),
            ("special://profile/addon_data/script.nimbus.helper/",
             "special://profile/addon_data/script.cineva.nimbus/"),
        ),
    )

    actions_path = bridge_root / "resources/lib/modules/custom_actions.py"
    actions_text = actions_path.read_text(encoding="utf-8")
    actions_text = remove_functions(actions_text, API_FUNCTIONS)
    actions_text = "\n".join(
        line for line in actions_text.splitlines()
        if line.strip() != "import requests"
    ) + "\n"
    actions_path.write_text(actions_text, encoding="utf-8")

    router = '''# -*- coding: utf-8 -*-
"""CINÉVA's API-free compatibility router for Nimbus menu/widget XML."""
import sys
from urllib.parse import parse_qsl


def routing():
    params = dict(parse_qsl(sys.argv[1], keep_blank_values=True))
    mode = params.get("mode", "")

    if mode == "manage_widgets":
        from modules.cpath_maker import CPaths
        return CPaths(params.get("cpath_setting", "")).manage_widgets()
    if mode == "manage_main_menu_path":
        from modules.cpath_maker import CPaths
        return CPaths(params.get("cpath_setting", "")).manage_main_menu_path()
    if mode == "remake_all_cpaths":
        from modules.cpath_maker import remake_all_cpaths
        return remake_all_cpaths()
    if mode in {"refresh_search_history", "search_input", "remove_all_spaths",
                "re_search", "open_search_window", "toggle_search_provider"}:
        from modules.search_utils import SPaths
        action = {
            "refresh_search_history": "refresh_search_history",
            "search_input": "search_input",
            "remove_all_spaths": "remove_all_spaths",
            "re_search": "re_search",
            "open_search_window": "open_search_window",
            "toggle_search_provider": "toggle_search_provider",
        }[mode]
        return getattr(SPaths(), action)()
    if mode in {"set_widget_count", "set_image", "play_trailer",
                "fix_black_screen", "set_blurradius", "set_blursaturation",
                "set_autoendplaybackdelay", "capture_user_key", "modify_keymap",
                "show_changelog"}:
        from modules import custom_actions
        return getattr(custom_actions, mode)()
    if mode in {"clear_image_cache", "calculate_cache_size"}:
        from modules import cache
        return getattr(cache, mode)()
    if mode in {"check_for_update", "check_for_profile_change",
                "set_api_key", "delete_all_ratings", "check_api_key_on_load"}:
        return None
    raise ValueError("Unsupported CINÉVA Nimbus Bridge mode: " + mode)
'''
    router_path = bridge_root / "resources/lib/modules/router.py"
    router_path.write_text(router, encoding="utf-8")

    cache_module = '''# -*- coding: utf-8 -*-
"""Small local cache utilities; intentionally performs no network requests."""
import os
import shutil
import xbmc
import xbmcaddon
import xbmcvfs


def _cache_path():
    addon_id = xbmcaddon.Addon().getAddonInfo("id")
    return xbmcvfs.translatePath(
        "special://profile/addon_data/%s/image_cache" % addon_id
    )


def clear_image_cache():
    path = _cache_path()
    if xbmcvfs.exists(path):
        shutil.rmtree(path, ignore_errors=True)
    xbmcvfs.mkdir(path)
    xbmc.executebuiltin("Notification(CINÉVA, Image cache cleared, 2500)")


def calculate_cache_size():
    path = _cache_path()
    total = 0
    if os.path.isdir(path):
        for base, _dirs, files in os.walk(path):
            for filename in files:
                try:
                    total += os.path.getsize(os.path.join(base, filename))
                except OSError:
                    pass
    megabytes = total / (1024 * 1024)
    xbmc.executebuiltin("Skin.SetString(CinevaCacheSize, %.1f MB)" % megabytes)
    return total
'''
    (bridge_root / "resources/lib/modules/cache.py").write_text(cache_module, encoding="utf-8")

    service_module = '''# -*- coding: utf-8 -*-
"""Minimal API-free service entry for Kodi's Nimbus bridge dependency."""
import xbmc


class NimbusBridgeService(xbmc.Monitor):
    def run(self):
        xbmc.log("CINEVA_NIMBUS_BRIDGE_SERVICE_STARTED", xbmc.LOGINFO)
        while not self.abortRequested():
            self.waitForAbort(1)


if __name__ == "__main__":
    NimbusBridgeService().run()
'''
    (bridge_root / "resources/lib/service.py").write_text(service_module, encoding="utf-8")
    (bridge_root / "NOTICE.txt").write_text(NOTICE, encoding="utf-8")


def write_deterministic_zip(source_root: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in source_root.rglob("*") if p.is_file()):
            relative = path.relative_to(source_root.parent).as_posix()
            info = ZipInfo(relative, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def build(output_dir: Path = OUT_DIR, fetcher=fetch_archive) -> dict[str, Path]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    with tempfile.TemporaryDirectory(prefix="cineva-nimbus-") as temp:
        temp_root = Path(temp)
        nimbus_source = temp_root / "nimbus-source"
        helper_source = temp_root / "helper-source"
        skin_root = output_dir / "skin.cineva"
        bridge_root = output_dir / "script.cineva.nimbus"

        extract_archive(fetcher(NIMBUS_REPO, NIMBUS_SHA), nimbus_source)
        extract_archive(fetcher(HELPER_REPO, HELPER_SHA), helper_source)
        shutil.copytree(nimbus_source, skin_root)

        patch_text_tree(
            skin_root,
            (
                ("script.nimbus.helper", "script.cineva.nimbus"),
                ("skin.nimbus", "skin.cineva"),
            ),
        )
        patch_nimbus_focus_include_ids(skin_root)
        patch_nimbus_include_list_id_defaults(skin_root)
        patch_skin_manifest(skin_root)
        remove_api_controls(skin_root)
        remove_unsupported_startup_checks(skin_root)
        apply_cineva_visuals(skin_root)
        apply_cineva_home_layout(skin_root)
        write_default_skin_includes(skin_root)
        (skin_root / "NOTICE.txt").write_text(NOTICE, encoding="utf-8")
        manifest = {
            "skin": "skin.cineva",
            "version": SKIN_VERSION,
            "base_repository": NIMBUS_REPO,
            "base_commit": NIMBUS_SHA,
            "helper_repository": HELPER_REPO,
            "helper_commit": HELPER_SHA,
            "helper_policy": "local widget/menu/search only; no MDBList/TMDb API service",
            "license": "GPL-2.0-only; artwork CC BY-SA 4.0",
        }
        (skin_root / "CINEVA_BASELINE.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_bridge(helper_source, bridge_root)
        upstream_license = skin_root / "LICENSE.txt"
        if upstream_license.is_file():
            shutil.copy2(upstream_license, bridge_root / "LICENSE-NIMBUS.txt")

        skin_zip = output_dir / f"skin.cineva-{SKIN_VERSION}-nimbus.zip"
        bridge_zip = output_dir / f"script.cineva.nimbus-{BRIDGE_VERSION}.zip"
        write_deterministic_zip(skin_root, skin_zip)
        write_deterministic_zip(bridge_root, bridge_zip)

    return {"skin": skin_zip, "bridge": bridge_zip}


if __name__ == "__main__":
    built = build()
    for name, path in built.items():
        print(f"{name}: {path} ({path.stat().st_size} bytes)")
