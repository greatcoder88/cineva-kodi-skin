# -*- coding: utf-8 -*-
"""Kodi entry point for CINÉVA widget settings actions."""
import sys
from urllib.parse import parse_qs
from resources.lib.manager import WidgetManager, SCREENS

def _args():
    if len(sys.argv) < 2:
        return {}
    return {key: values[-1] for key, values in parse_qs(sys.argv[1].lstrip('?')).items()}

if __name__ == '__main__':
    args = _args()
    screen = args.get('screen', 'home')
    if screen not in SCREENS:
        screen = 'home'
    WidgetManager().run(args.get('action', 'manage'), screen, args.get('slot', '1'))
