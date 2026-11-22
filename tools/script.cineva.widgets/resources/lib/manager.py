# -*- coding: utf-8 -*-
"""Generic per-screen widget registry and installed video add-on browser."""
import json
import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
SCREENS = ('home', 'movies', 'tvshows', 'search', 'mylist')

class KodiRPC:
    @staticmethod
    def call(method, params=None):
        payload = {'jsonrpc': '2.0', 'id': 1, 'method': method}
        if params is not None:
            payload['params'] = params
        try:
            result = json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
        except (TypeError, ValueError):
            return None
        return None if 'error' in result else result.get('result')

class WidgetManager:
    def __init__(self):
        self.dialog = xbmcgui.Dialog()

    @staticmethod
    def _clean_list(items):
        if not isinstance(items, list):
            return []
        cleaned = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name, path = str(item.get('name', '')).strip(), str(item.get('path', '')).strip()
            if name and path.startswith('plugin://'):
                cleaned.append({'id': str(item.get('id') or path), 'name': name,
                                'path': path, 'addon': str(item.get('addon', '')),
                                'content': str(item.get('content', 'videos'))})
        return cleaned

    def load(self):
        try:
            data = json.loads(ADDON.getSettingString('widget_registry') or '{}')
        except (TypeError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        return {screen: self._clean_list(data.get(screen, [])) for screen in SCREENS}

    @staticmethod
    def save(registry):
        ADDON.setSettingString('widget_registry', json.dumps(registry, ensure_ascii=False, separators=(',', ':')))

    def installed_video_addons(self):
        result = KodiRPC.call('Addons.GetAddons', {
            'type': 'xbmc.python.pluginsource', 'content': 'video',
            'properties': ['name', 'enabled']}) or {}
        addons = result.get('addons', []) if isinstance(result, dict) else []
        return [a for a in addons if a.get('enabled', True)]

    def browse_plugin(self, addon):
        return self._browse_directory('plugin://{}/'.format(addon['addonid']), addon['addonid'])

    def _browse_directory(self, path, addon_id):
        result = KodiRPC.call('Files.GetDirectory', {
            'directory': path, 'media': 'video',
            'properties': ['title', 'file', 'thumbnail', 'art', 'playcount', 'resume']}) or {}
        files = result.get('files', []) if isinstance(result, dict) else []
        choices, mapping = ['✓  Use this folder as widget'], [('select', path, '')]
        for item in files:
            target = item.get('file', '')
            if not target:
                continue
            folder = item.get('filetype') == 'directory' or target.endswith('/')
            title = item.get('label') or item.get('title') or target.rstrip('/').split('/')[-1]
            choices.append(('📁  ' if folder else '▶  ') + title)
            mapping.append(('folder' if folder else 'select', target, title))
        choices.append('←  Back')
        mapping.append(('back', '', ''))
        picked = self.dialog.select('Browse ' + addon_id, choices, useDetails=False)
        if picked < 0:
            return None
        action, target, title = mapping[picked]
        if action == 'select':
            return {'path': target, 'title': title}
        if action == 'folder':
            return self._browse_directory(target, addon_id)
        return None

    def add_widget(self, registry, screen):
        addons = self.installed_video_addons()
        if not addons:
            self.dialog.ok('CINÉVA', 'No enabled video add-ons were found.')
            return
        labels = ['{}  ({})'.format(a.get('name', a['addonid']), a['addonid']) for a in addons]
        index = self.dialog.select('Choose video add-on', labels)
        if index < 0:
            return
        addon = addons[index]
        chosen = self.browse_plugin(addon)
        if not chosen:
            return
        name = self.dialog.input('Widget name', defaultt=chosen.get('title') or addon.get('name', 'Widget'))
        if not name:
            return
        registry[screen].append({'id': '{}:{}'.format(addon['addonid'], len(registry[screen]) + 1),
                                 'name': name.strip(), 'path': chosen['path'],
                                 'addon': addon['addonid'], 'content': 'videos'})
        self.save(registry)

    def manage_screen(self, registry, screen):
        while True:
            widgets = registry[screen]
            labels = ['＋  Add widget'] + ['{}  —  {}'.format(i + 1, w['name']) for i, w in enumerate(widgets)] + ['←  Back']
            picked = self.dialog.select('CINÉVA · {} widgets'.format(screen.upper()), labels)
            if picked < 0 or picked == len(labels) - 1:
                return
            if picked == 0:
                self.add_widget(registry, screen)
            else:
                self.edit_widget(registry, screen, picked - 1)

    def edit_widget(self, registry, screen, index):
        widget = registry[screen][index]
        while True:
            actions = ['Rename', 'Change source folder', 'Move up', 'Move down', 'Remove widget', 'Back']
            picked = self.dialog.select(widget['name'], actions)
            if picked < 0 or picked == 5:
                return
            if picked == 0:
                name = self.dialog.input('Widget name', defaultt=widget['name'])
                if name:
                    widget['name'] = name.strip()
            elif picked == 1:
                addons = self.installed_video_addons()
                labels = ['{}  ({})'.format(a.get('name', a['addonid']), a['addonid']) for a in addons]
                pos = self.dialog.select('Choose video add-on', labels)
                if pos >= 0:
                    addon = addons[pos]
                    chosen = self.browse_plugin(addon)
                    if chosen:
                        widget.update({'path': chosen['path'], 'addon': addon['addonid']})
            elif picked in (2, 3):
                new_index = index + (-1 if picked == 2 else 1)
                if 0 <= new_index < len(registry[screen]):
                    registry[screen][index], registry[screen][new_index] = registry[screen][new_index], registry[screen][index]
                    index = new_index
            elif picked == 4:
                if self.dialog.yesno('Remove widget', 'Remove "{}"?'.format(widget['name'])):
                    registry[screen].pop(index)
                    self.save(registry)
                    return
            self.save(registry)
            widget = registry[screen][index]

    def run(self, action='manage', screen='home'):
        registry = self.load()
        if action == 'list':
            xbmc.log('CINEVA_WIDGET_REGISTRY=' + json.dumps(registry, ensure_ascii=False), xbmc.LOGINFO)
            return
        if screen not in SCREENS:
            screen = 'home'
        self.manage_screen(registry, screen)
