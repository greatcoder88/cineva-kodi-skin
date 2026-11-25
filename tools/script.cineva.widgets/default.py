# -*- coding: utf-8 -*-
"""Kodi entry point for CINÉVA widget settings actions."""
import sys
from urllib.parse import parse_qs, unquote
from resources.lib.manager import WidgetManager, SCREENS


def _args(argv=None):
    argv = sys.argv if argv is None else argv
    if len(argv) < 2:
        return {}
    raw = argv[1].lstrip('?')
    # The selected plugin URL is deliberately the final argument. Kodi's
    # $ESCINFO[] does not escape ampersands in FileNameAndPath, so parse_qs()
    # would mistake nested URL parameters (for example &id=1) for outer
    # script parameters and silently truncate the path. Parse only the prefix
    # and preserve everything after &path= as the URL payload.
    prefix, marker, raw_path = raw.partition('&path=')
    args = {key: values[-1] for key, values in parse_qs(prefix if marker else raw).items()}
    if marker:
        # Accept a fully percent-encoded plugin URL as well as Kodi's normal
        # raw plugin:// URL. Do not unquote an already-raw URL: its own %XX
        # escapes may be meaningful to the video add-on.
        if raw_path.lower().startswith('plugin%3a%2f%2f'):
            raw_path = unquote(raw_path)
        args['path'] = raw_path
    return args


if __name__ == '__main__':
    args = _args()
    screen = args.get('screen', 'home')
    if screen not in SCREENS:
        screen = 'home'
    WidgetManager().run(
        args.get('action', 'manage'), screen, args.get('slot', '1'),
        args.get('container', '9001'), args.get('path', '')
    )
