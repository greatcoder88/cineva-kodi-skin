# -*- coding: utf-8 -*-
"""CINÉVA Widget Manager: Kodi script UI + video plugin directory provider."""
import sys
from urllib.parse import parse_qs
import xbmcplugin
import xbmcgui
from resources.lib.manager import WidgetManager, SCREENS

def _args(is_plugin=False):
    index = 2 if is_plugin else 1
    if len(sys.argv) <= index:
        return {}
    return {key: values[-1] for key, values in parse_qs(sys.argv[index].lstrip('?')).items()}

def _directory(screen):
    handle = int(sys.argv[1])
    registry = WidgetManager().load()
    rows = []
    for widget in registry.get(screen, []):
        li = xbmcgui.ListItem(label=widget['name'], label2=widget.get('addon', ''))
        li.setInfo('video', {'title': widget['name'], 'mediatype': 'video'})
        li.setProperty('Cineva.WidgetId', widget['id'])
        li.setProperty('Cineva.WidgetSource', widget['path'])
        li.addContextMenuItems([('Manage ' + screen.title() + ' widgets',
            'RunScript(script.cineva.widgets,action=manage&screen=' + screen + ')')])
        rows.append((widget['path'], li, True))
    if not rows:
        li = xbmcgui.ListItem(label='No widgets configured — open Edit Widgets')
        li.addContextMenuItems([('Manage widgets',
            'RunScript(script.cineva.widgets,action=manage&screen=' + screen + ')')])
        rows.append(('', li, False))
    xbmcplugin.addDirectoryItems(handle, rows, len(rows))
    xbmcplugin.setContent(handle, 'videos')
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)

if __name__ == '__main__':
    if sys.argv and sys.argv[0].startswith('plugin://'):
        args = _args(is_plugin=True)
        screen = args.get('screen', 'home')
        _directory(screen if screen in SCREENS else 'home')
    else:
        args = _args()
        WidgetManager().run(args.get('action', 'manage'), args.get('screen', 'home'))
