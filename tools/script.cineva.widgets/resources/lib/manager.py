# -*- coding: utf-8 -*-
"""CINÉVA's per-screen widget source picker and slot persistence.

The skin owns presentation. This helper only browses Kodi video add-ons and
stores the selected plugin:// folder for each screen slot.
"""
import json
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
SCREENS = ('home', 'movies', 'tvshows')
SLOT_COUNT = 4
DEFAULT_HOME = [
    {'id': 'pov:continue-movies', 'name': 'Continue Watching Movies', 'path': 'plugin://plugin.video.pov/?mode=build_movie_list&action=in_progress_movies&name=Continue%20Watching%20Movies', 'addon': 'plugin.video.pov', 'content': 'videos'},
    {'id': 'pov:continue-tv', 'name': 'In Progress Shows', 'path': 'plugin://plugin.video.pov/?mode=build_tvshow_list&action=in_progress_tvshows&name=In%20Progress%20Shows', 'addon': 'plugin.video.pov', 'content': 'videos'},
    {'id': 'pov:trending-movies', 'name': 'Trending Movies', 'path': 'plugin://plugin.video.pov/?mode=build_movie_list&action=tmdb_movies_trending&name=Trending%20Movies', 'addon': 'plugin.video.pov', 'content': 'videos'},
    {'id': 'pov:trending-tv', 'name': 'Trending TV Shows', 'path': 'plugin://plugin.video.pov/?mode=build_tvshow_list&action=tmdb_tv_trending&name=Trending%20TV%20Shows', 'addon': 'plugin.video.pov', 'content': 'videos'}
]

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
    def _registry_path():
        return xbmcvfs.translatePath('special://profile/addon_data/script.cineva.widgets/widget_registry.json')

    def load(self):
        path = self._registry_path()
        exists = xbmcvfs.exists(path)
        data = {}
        if exists:
            try:
                handle = xbmcvfs.File(path, 'r')
                try:
                    data = json.loads(handle.read() or '{}')
                finally:
                    handle.close()
            except (TypeError, ValueError, IOError):
                xbmc.log('CINEVA_WIDGETS: registry unreadable; keeping screens empty', xbmc.LOGWARNING)
        if not isinstance(data, dict):
            data = {}
        registry = {screen: self._clean_list(data.get(screen, [])) for screen in SCREENS}
        # Defaults are a first-install convenience only. An intentionally
        # cleared Home must remain blank on every later launch.
        if not exists:
            registry['home'] = [dict(item) for item in DEFAULT_HOME]
            self.save(registry)
        return registry

    @staticmethod
    def _clean_list(items):
        if not isinstance(items, list):
            return []
        cleaned = []
        for item in items[:SLOT_COUNT]:
            if not isinstance(item, dict):
                cleaned.append({})
                continue
            name, path = str(item.get('name', '')).strip(), str(item.get('path', '')).strip()
            if not name and not path:
                cleaned.append({})
                continue
            if name and path.startswith('plugin://'):
                cleaned.append({'id': str(item.get('id') or path), 'name': name,
                                'path': path, 'addon': str(item.get('addon', '')),
                                'content': str(item.get('content', 'videos'))})
        return cleaned

    def save(self, registry):
        folder = 'special://profile/addon_data/script.cineva.widgets'
        xbmcvfs.mkdirs(folder)
        handle = xbmcvfs.File(self._registry_path(), 'w')
        try:
            handle.write(json.dumps(registry, ensure_ascii=False, separators=(',', ':')))
        finally:
            handle.close()
        mappings = {'home': 'Cineva.Widget', 'movies': 'Cineva.MovieWidget', 'tvshows': 'Cineva.ShowWidget'}
        for screen, prefix in mappings.items():
            items = registry.get(screen, [])
            for index in range(1, SLOT_COUNT + 1):
                item = items[index - 1] if len(items) >= index else {}
                for suffix, value in {
                    'Name': item.get('name', ''), 'Path': item.get('path', ''),
                    'Target': 'videos' if item else '', 'Type': 'video' if item else ''
                }.items():
                    encoded = json.dumps(str(value), ensure_ascii=False)
                    xbmc.executebuiltin('Skin.SetString({}{}.{},{})'.format(prefix, index, suffix, encoded))
        xbmc.executebuiltin('Skin.SetBool(Cineva.Initialized)')
        for control_id in (9001, 9002, 9003, 9004):
            xbmc.executebuiltin('Container.Refresh({})'.format(control_id))

    def installed_video_addons(self):
        result = KodiRPC.call('Addons.GetAddons', {
            'type': 'xbmc.python.pluginsource', 'content': 'video',
            'properties': ['name', 'enabled']}) or {}
        addons = result.get('addons', []) if isinstance(result, dict) else []
        return [a for a in addons if a.get('enabled', True) and a.get('addonid')]

    def _browse_directory(self, path, addon_id):
        result = KodiRPC.call('Files.GetDirectory', {
            'directory': path, 'media': 'video',
            'properties': ['title', 'file', 'thumbnail', 'art', 'playcount', 'resume']})
        if not isinstance(result, dict):
            self.dialog.ok('CINÉVA', 'Kodi could not read this add-on folder. Check that it is enabled and working.')
            return None
        choices, mapping = ['✓  Use this folder as widget'], [('select', path, '')]
        for item in result.get('files', []):
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

    def choose_source(self):
        addons = self.installed_video_addons()
        if not addons:
            self.dialog.ok('CINÉVA', 'No enabled video add-ons were found.')
            return None
        labels = ['{}  ({})'.format(a.get('name', a['addonid']), a['addonid']) for a in addons]
        index = self.dialog.select('Choose video add-on', labels)
        if index < 0:
            return None
        addon = addons[index]
        chosen = self._browse_directory('plugin://{}/'.format(addon['addonid']), addon['addonid'])
        if not chosen:
            return None
        name = self.dialog.input('Widget name', defaultt=chosen.get('title') or addon.get('name', 'Widget'))
        if not name or not name.strip():
            return None
        return {'id': '{}:{}'.format(addon['addonid'], chosen['path']),
                'name': name.strip(), 'path': chosen['path'],
                'addon': addon['addonid'], 'content': 'videos'}

    def configure_slot(self, registry, screen, slot):
        if screen not in SCREENS or slot < 1 or slot > SLOT_COUNT:
            return
        items = registry[screen]
        while len(items) < slot:
            items.append({})
        current = items[slot - 1]
        actions = ['Choose / change source', 'Clear this widget', 'Cancel']
        if current:
            actions.insert(0, 'Current: ' + current.get('name', 'Widget'))
        picked = self.dialog.select('{} · Widget {}'.format(screen.title(), slot), actions)
        if picked < 0 or actions[picked] == 'Cancel':
            return
        if actions[picked] == 'Clear this widget':
            items[slot - 1] = {}
        else:
            selected = self.choose_source()
            if selected:
                items[slot - 1] = selected
        # Remove only trailing empty slots; internal empty slots preserve numbering.
        while items and not items[-1]:
            items.pop()
        self.save(registry)

    def manage_screen(self, registry, screen):
        while True:
            items = registry[screen]
            labels = []
            for slot in range(1, SLOT_COUNT + 1):
                item = items[slot - 1] if len(items) >= slot else {}
                labels.append('Widget {}  —  {}'.format(slot, item.get('name', 'Not set')))
            labels.append('←  Back')
            picked = self.dialog.select('CINÉVA · {} settings'.format(screen.upper()), labels)
            if picked < 0 or picked == SLOT_COUNT:
                return
            self.configure_slot(registry, screen, picked + 1)

    def run(self, action='manage', screen='home', slot=1):
        registry = self.load()
        if screen not in SCREENS:
            screen = 'home'
        if action == 'init':
            self.save(registry)
            return
        if action == 'configure':
            self.configure_slot(registry, screen, int(slot))
            return
        if action == 'clear':
            index = int(slot) - 1
            if 0 <= index < SLOT_COUNT:
                while len(registry[screen]) <= index:
                    registry[screen].append({})
                registry[screen][index] = {}
                while registry[screen] and not registry[screen][-1]:
                    registry[screen].pop()
                self.save(registry)
            return
        if action == 'list':
            xbmc.log('CINEVA_WIDGET_REGISTRY=' + json.dumps(registry, ensure_ascii=False), xbmc.LOGINFO)
            return
        self.manage_screen(registry, screen)
