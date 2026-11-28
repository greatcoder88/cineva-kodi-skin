"""Sample already-cached poster colors, off Kodi's UI thread."""

from collections import OrderedDict
import colorsys
from pathlib import Path
from urllib.parse import unquote

from PIL import Image
import xbmc
import xbmcgui
import xbmcvfs


class ArtAccent:
    def __init__(self):
        self.home = xbmcgui.Window(10000)
        self.cache = OrderedDict()
        self.previous = ""
        self.published = ""

    def tick(self):
        poster = xbmc.getInfoLabel("ListItem.Art(poster)")
        if not poster or poster == self.published:
            return
        # Let the focus stay on one poster through two monitor ticks.
        if poster != self.previous:
            self.previous = poster
            return
        if poster not in self.cache:
            color = sample_poster(poster)
            if color:
                self.cache[poster] = color
                if len(self.cache) > 64:
                    self.cache.popitem(last=False)
        if xbmc.getInfoLabel("ListItem.Art(poster)") != poster:
            return
        self.home.clearProperty("Frame.ArtAccentPoster")
        self.home.setProperty("Frame.ArtAccent", self.cache.get(poster, ""))
        self.home.setProperty("Frame.ArtAccentPoster", poster)
        self.published = poster


def sample_poster(poster):
    name = unquote(poster.removeprefix("image://")).removesuffix("/") if poster.startswith("image://") else poster
    for source in (poster, name):
        stem = xbmc.getCacheThumbName(source).split(".", 1)[0]
        for extension in (".jpg", ".png"):
            path = f"special://profile/Thumbnails/{stem[0]}/{stem}{extension}"
            try:
                with Image.open(Path(xbmcvfs.translatePath(path))) as image:
                    image.draft("RGB", (32, 32))
                    image.thumbnail((24, 24))
                    palette = image.convert("RGB").quantize(colors=8)
                    colors = palette.getpalette()
                    samples = []
                    for count, index in palette.getcolors():
                        hue, saturation, lightness = colorsys.rgb_to_hsv(
                            *(component / 255 for component in colors[index * 3:index * 3 + 3])
                        )
                        if saturation > .19 and lightness > .13:
                            samples.append((count * saturation, hue, saturation))
                    if samples:
                        _, hue, saturation = max(samples)
                        rgb = colorsys.hsv_to_rgb(hue, min(.69, saturation), 1)
                        return "FF" + "".join(f"{round(component * 255):02X}" for component in rgb)
            except (OSError, ValueError):
                continue
    return ""
