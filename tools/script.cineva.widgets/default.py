# -*- coding: utf-8 -*-
import sys
from urllib.parse import parse_qs
from resources.lib.manager import WidgetManager

def _args():
    if len(sys.argv) < 2:
        return {}
    return {key: values[-1] for key, values in parse_qs(sys.argv[1].lstrip('?')).items()}

if __name__ == '__main__':
    args = _args()
    WidgetManager().run(args.get('action', 'manage'), args.get('screen', 'home'))
