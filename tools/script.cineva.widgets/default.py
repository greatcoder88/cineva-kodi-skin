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
    # A selected plugin URL is the final argument and can itself contain '&'
    # query parameters. parse_qs would split those into unrelated arguments;
    # preserve the untouched tail after our explicit path delimiter.
    marker = '&path='
    if marker in raw:
        args['path'] = raw.split(marker, 1)[1]
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
