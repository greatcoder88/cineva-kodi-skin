# -*- coding: utf-8 -*-
"""Kodi entry point for CINÉVA widget settings actions."""
import sys
from urllib.parse import parse_qs
from resources.lib.manager import WidgetManager, SCREENS


def _args(argv=None):
    argv = sys.argv if argv is None else argv
    if len(argv) < 2:
        return {}
    raw = argv[1].lstrip('?')
    args = {key: values[-1] for key, values in parse_qs(raw).items()}
    # Home passes the selected FileNameAndPath through Kodi's $ESCINFO[]
    # expansion. The URL-escaped separators stay inside this argument; parse_qs
    # decodes the selected plugin URL once without splitting its query parameters.
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
