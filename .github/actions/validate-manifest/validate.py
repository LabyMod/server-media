import json
import os
import re
import sys
import time
from base64 import b64decode
from io import BytesIO

import requests
import tldextract
from PIL import Image

REPOSITORY = 'LabyMod/server-media'
DOCS_URL = 'https://github.com/LabyMod/server-media/blob/master/docs/Manifest.md'
BOT_LOGIN = 'github-actions[bot]'
MARKER = '<!-- server-media-validate -->'
TIMEOUT = 10

REQUIRED_KEYS = ['server_name', 'nice_name', 'direct_ip']
PARTY_KEYS = ['invite', 'accept', 'leave', 'kick', 'disband', 'transfer', 'warp', 'jump']
PARTY_REQUIRED_KEYS = ['invite', 'accept']
PARTY_PLAYER_KEYS = ['invite', 'kick', 'transfer']
USERNAME_SOCIAL_KEYS = ['twitter', 'tiktok', 'facebook', 'instagram', 'teamspeak']
URL_SOCIAL_KEYS = ['web', 'web_shop', 'web_support', 'youtube', 'discord']
BRAND_KEYS = ['primary', 'background', 'text']
GAMEMODE_KEYS = ['name', 'color', 'url', 'command', 'versions']
ALLOWED_KEYS = {
    None: REQUIRED_KEYS + ['server_wildcards', 'supported_languages', 'social', 'gamemodes', 'chat', 'discord',
                           'brand', 'location', 'yt_trailer', 'user_stats', 'command_delay', 'party'],
    'social': URL_SOCIAL_KEYS + USERNAME_SOCIAL_KEYS,
    'discord': ['server_id', 'rename_to_minecraft_name'],
    'brand': BRAND_KEYS,
    'location': ['city', 'country', 'country_code'],
    'chat': ['message_formats'],
}
MAINTENANCE_KEYWORDS = ['maintenance', 'wartung', 'mantenimiento', 'manutenção', 'manutencao']

HEX_COLOR = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')
VERSION = r'(?:\*|\d+(?:\.\d+)*|\d{2}w\d{2}[a-z])'
VERSION_RANGE = re.compile(rf'^{VERSION}(?:<{VERSION})?$')
LANGUAGE = re.compile(r'^[a-z]{2}(?:-[A-Za-z]{2,3})?$')
SERVER_NAME = re.compile(r'^[a-z0-9]+$')
GAMEMODE_KEY = re.compile(r'^[a-z0-9_-]+$')
YOUTUBE_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')

SESSION = requests.Session()
SESSION.headers['User-Agent'] = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                 '(KHTML, like Gecko) Chrome/130.0 Safari/537.36')
# Without it, YouTube answers every channel with its cookie consent page and HTTP 200
SESSION.cookies.set('SOCS', 'CAI', domain='.youtube.com')
DOMAINS = tldextract.TLDExtract(cache_dir=None, suffix_list_urls=())


class Report:
    """Collects the results of one manifest."""

    def __init__(self, path):
        self.path = path
        self.errors = []
        self.notes = []
        self.facts = []

    def error(self, message):
        self.errors.append(message)

    def note(self, message):
        self.notes.append(message)

    def fact(self, label, value):
        self.facts.append((label, value))


def main():
    changes = get_changed_files()
    manifests = [path for path, status in changes.items()
                 if path.startswith('minecraft_servers/') and path.endswith('manifest.json') and status != 'D']

    if not manifests:
        print('There are no changed manifest files in this pull request.')

    reports = []
    for path in sorted(manifests):
        print(f'Validate {path}')
        report = Report(path)
        validate_manifest(path, changes[path] == 'A', report)
        reports.append(report)

    errors = render(reports, 'errors')
    notes = render(reports, 'notes')
    print(errors or 'No errors found.')
    print(notes)
    write_summary(reports)

    github = GitHub.from_env()
    if github:
        github.sync_review(errors)
        github.sync_comment(notes)
    else:
        print('No pull request context, nothing is posted.')

    if errors:
        sys.exit('Invalid data in manifest.json. See the review in the pull request for more information.')


def get_changed_files():
    """Returns {path: status} of the pull request, as listed by the workflow in changed_files.txt."""
    if len(sys.argv) > 1:
        return {path: 'A' for path in sys.argv[1:]}

    changes = {}
    with open('changed_files.txt', encoding='utf-8') as file:
        for line in file:
            status, _, path = line.rstrip('\n').partition('\t')
            if path:
                changes[path] = status[:1]
    return changes


def validate_manifest(path, is_new, report):
    parts = path.split('/')
    if len(parts) != 3:
        report.error('- `manifest.json` has to be inside the server directory, '
                     'e.g. `minecraft_servers/{server_name}/manifest.json`')
        return

    try:
        with open(path, encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f'Unable to open {path} - Continue...')
        return
    except (json.JSONDecodeError, UnicodeDecodeError):
        report.error(f'- JSON is invalid! Workflow is not able to check {path}')
        return

    if not isinstance(data, dict) or not all(key in data for key in REQUIRED_KEYS):
        report.error('- One of the **required values** is missing')
        return

    if not check_types(data, report):
        return
    check_keys(data, report)

    server_directory = parts[1]
    if data['direct_ip'] in ['', '-']:
        report.error('- Direct IP is required')
    if data['nice_name'] in ['', '-']:
        report.error('- Nice name is required and cannot be empty!')
    if server_directory != data['server_name']:
        report.error('**Servername has to be directory name!** (all lowercase)')
    elif is_new and not SERVER_NAME.match(data['server_name']):
        report.error('- `server_name` may only contain lowercase letters and digits (`server_name`)')
    if data['direct_ip'] != data['direct_ip'].lower():
        report.error(f'- Please use lowercase for the direct IP: `{data["direct_ip"].lower()}` (`direct_ip`)')

    wildcards = data.get('server_wildcards', [])
    for wildcard in wildcards:
        if not wildcard.startswith('%.'):
            report.error('- Invalid wildcard entry. Each entry must start with **%.**. Further information here: '
                         'https://en.wikipedia.org/wiki/Wildcard_DNS_record (`server_wildcards`)')

    status = check_server(data['direct_ip'], report)
    if wildcards and all(wildcard.startswith('%.') for wildcard in wildcards):
        check_wildcards(data['direct_ip'], wildcards, status, report)

    if 'social' in data:
        check_social(data, report)

    if 'discord' in data:
        if data['discord'].get('rename_to_minecraft_name') is True:
            report.note('- `discord.rename_to_minecraft_name` is reserved for LabyMod Partners. Change it to `false`. '
                        'If you are a partner, please ignore this message.')

    if 'location' in data:
        if data['location'].get('city') in ['', '-']:
            report.error('- Please remove the empty key **city** or fill in information.')

        if 'country_code' in data['location']:
            country_code = data['location']['country_code']
            if len(country_code) != 2:
                report.error('- Use valid format (ISO 3166-1 alpha-2) for country code. (`location.country_code`)')
            if not country_code.isupper():
                report.error('- Use upper-case for country code. (`location.country_code`)')

    if 'brand' in data:
        for key, value in data['brand'].items():
            if not HEX_COLOR.match(value):
                report.error(f'- Please enter a valid hex-code like `#1A2B3C` (`brand.{key}`)')

    if 'yt_trailer' in data:
        check_trailer(data['yt_trailer'], report)

    if 'user_stats' in data:
        stats_url = data['user_stats']
        if not stats_url.startswith('https://'):
            report.error('- Invalid url. URL has to start with **https://** (`user_stats`)')
        if '{userName}' not in stats_url and '{uuid}' not in stats_url:
            report.error('- Please use {userName} or {uuid} in your stats url (`user_stats`)')
        if '://laby.net/' in stats_url:
            report.error('- Please use **your own page**, not LABY.net (`user_stats`)')

    if 'chat' in data and 'message_formats' in data['chat']:
        check_chat(data['chat']['message_formats'], report)

    if 'command_delay' in data and data['command_delay'] < 0:
        report.error('- `command_delay` has to be a positive number in milliseconds (`command_delay`)')

    if 'gamemodes' in data:
        check_gamemodes(data['gamemodes'], os.path.dirname(path), is_new, report)

    if 'party' in data:
        for message in validate_party(data['party']):
            report.error(message)

    icon_path = os.path.join(os.path.dirname(path), 'icon.png')
    report.fact('Favicon', describe_favicon(status, icon_path))


def check_keys(data, report):
    """Unknown keys are ignored by LABY.net and LabyMod, so a typo would silently drop the value."""
    for section, allowed in ALLOWED_KEYS.items():
        values = data if section is None else data.get(section, {})
        for key in values:
            if key not in allowed:
                name = key if section is None else f'{section}.{key}'
                report.error(f'- Unknown key **{key}**, allowed are: {", ".join(allowed)} (`{name}`)')


def check_types(data, report):
    """Returns False if a value has a type the other checks cannot handle."""
    errors = len(report.errors)

    for key in ['server_name', 'nice_name', 'direct_ip', 'yt_trailer', 'user_stats']:
        if key in data and not isinstance(data[key], str):
            report.error(f'- `{key}` has to be a text value (`{key}`)')

    for key in ['server_wildcards', 'supported_languages']:
        if key in data and (not isinstance(data[key], list) or not all(isinstance(v, str) for v in data[key])):
            report.error(f'- `{key}` has to be a list of texts, e.g. `["de", "en"]` (`{key}`)')

    for section in ['social', 'discord', 'brand', 'location', 'chat', 'gamemodes']:
        if section in data and not isinstance(data[section], dict):
            report.error(f'- `{section}` has to be an object, see the [documentation]({DOCS_URL})')

    for section in ['social', 'brand', 'location']:
        for key, value in data.get(section, {}).items() if isinstance(data.get(section), dict) else []:
            if not isinstance(value, str):
                report.error(f'- `{section}.{key}` has to be a text value (`{section}.{key}`)')

    discord = data.get('discord')
    if isinstance(discord, dict):
        server_id = discord.get('server_id')
        if 'server_id' in discord and not (isinstance(server_id, int) and not isinstance(server_id, bool)
                                           or isinstance(server_id, str) and server_id.isdigit()):
            report.error('- Please use a **numeric** value for your server id (`discord.server_id`)')
        if 'rename_to_minecraft_name' in discord and not isinstance(discord['rename_to_minecraft_name'], bool):
            report.error('- `discord.rename_to_minecraft_name` has to be `true` or `false`')

    delay = data.get('command_delay')
    if 'command_delay' in data and (not isinstance(delay, int) or isinstance(delay, bool)):
        report.error('- `command_delay` has to be a number in milliseconds, e.g. `3000` (`command_delay`)')

    gamemodes = data.get('gamemodes')
    if isinstance(gamemodes, dict):
        for key, gamemode in gamemodes.items():
            if not isinstance(gamemode, dict):
                report.error(f'- The gamemode **{key}** has to be an object (`gamemodes.{key}`)')
                continue
            for field, value in gamemode.items():
                if field in GAMEMODE_KEYS and not isinstance(value, str):
                    report.error(f'- `gamemodes.{key}.{field}` has to be a text value')

    if len(report.errors) > errors:
        return False

    for language in data.get('supported_languages', []):
        if not LANGUAGE.match(language):
            report.error(f'- `{language}` is not a valid language code, use ISO 639-1 like `de` (`supported_languages`)')
    return True


def check_social(data, report):
    social = data['social']
    for key in URL_SOCIAL_KEYS:
        if key not in social:
            continue
        url = social[key]
        if not url.startswith('https://'):
            report.error(f'- Invalid url. URL has to start with **https://** (`social.{key}`)')
            continue
        if url.endswith('/'):
            report.error(f'- Please remove **/** at the end of url (`social.{key}`)')
        if key == 'discord':
            continue

        status = http_status(url)
        report.fact(f'social.{key}', f'{url} ({status or "unreachable"})')
        if status is None:
            report.note(f'- The website {url} **could not be reached**. Please recheck whether is available.')
        elif status in (404, 410):
            report.error(f'- The link {url} returns **HTTP {status}**, please check it (`social.{key}`)')
        elif status >= 500:
            report.note(f'- The website {url} currently returns **HTTP {status}**. Please recheck whether is available.')

    if 'discord' in social:
        link = social['discord']
        if not link.startswith(('https://discord.gg', 'https://discord.com')):
            report.note('- Custom Discord invites are reserved for **LabyMod Partners**.\n'
                        'If you are a partner, please ignore this message.')
            print(f'Did not check invite for validity: {link}')
        else:
            check_discord_invite(link, data.get('discord', {}).get('server_id'), report)

    for key in USERNAME_SOCIAL_KEYS:
        if key in social and (social[key].startswith('http') or 'www' in social[key]):
            report.error(f'- Please use a **username**, not a link (`social.{key}`)')
        if key in social and social[key] in ('', '-'):
            report.error(f'- Please remove the empty key **{key}** or fill in information.')

    # Check facebook, because it works :)
    if 'facebook' in social and http_status(f'https://facebook.com/{social["facebook"]}') == 404:
        report.error(f'- Invalid facebook account: https://facebook.com/{social["facebook"]} (`social.facebook`)')


def check_discord_invite(link, server_id, report):
    invite = link.rstrip('/').split('/')[-1]
    print(f'Check discord invite for {invite}')
    try:
        response = request_invite(invite)
        # Discord rate limits per IP, a single short wait is enough for one pull request
        if response.status_code == 429:
            retry_after = float(response.headers.get('Retry-After', TIMEOUT))
            if retry_after <= TIMEOUT:
                time.sleep(retry_after)
                response = request_invite(invite)
    except (requests.RequestException, ValueError):
        report.fact('Discord', f'{link} could not be checked')
        return

    if response.status_code == 404:
        report.error(f'- The Discord invite {link} is **invalid**.')
        return
    if response.status_code != 200:
        report.fact('Discord', f'{link} could not be checked (HTTP {response.status_code})')
        return

    data = response.json()
    guild = data.get('guild') or {}
    report.fact('Discord', f'{guild.get("name", "Unknown Guild")}, {data.get("approximate_member_count", "?")} members, '
                           f'{data.get("approximate_presence_count", "?")} online')
    if data.get('expires_at'):
        report.error(f'- The Discord invite {link} **expires** on {data["expires_at"][:10]}. '
                     'Please use an invite that never expires (`social.discord`)')
    if server_id is not None and guild.get('id') and str(server_id) != guild['id']:
        report.error(f'- `discord.server_id` is `{server_id}`, but the invite {link} belongs to the server '
                     f'`{guild["id"]}` (`discord.server_id`)')


def request_invite(invite):
    return SESSION.get(f'https://discord.com/api/v10/invites/{invite}', params={'with_counts': 'true'},
                       timeout=TIMEOUT)


def check_trailer(trailer, report):
    if not YOUTUBE_ID.match(trailer):
        report.error('- Please use the YouTube **video ID**, not a link, e.g. `8asFIRe2HSw` (`yt_trailer`)')
        return
    status = http_status(f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={trailer}&format=json')
    if status in (400, 404):
        report.error(f'- The YouTube video `{trailer}` does not exist (`yt_trailer`)')
    elif status in (401, 403):
        report.note(f'- The YouTube video `{trailer}` is private or cannot be embedded (`yt_trailer`)')


def check_chat(message_format, report):
    if isinstance(message_format, list):
        if len(message_format) != 1:
            report.error('**message_format** has the wrong format. Please recheck the '
                         f'[example manifest]({DOCS_URL}#chat-object).')
            return
        message_format = message_format[0]

    template_regex = '^§[a-f0-9](?<level>\\d+)( \\||§8 \\|) §[a-f0-9](?<sender>[a-zA-Z0-9_]{2,16})§r§7: §f(?<message>.*)$'
    if template_regex == message_format:
        report.note('- It seems you\'re using the **template regex** for chat message! '
                    'Please make sure it is the right regex for **your server**!')
    if message_format in ('', '-'):
        report.error('- Please remove the empty key **message_formats** or fill in information.')


def check_gamemodes(gamemodes, directory, is_new, report):
    for key, gamemode in gamemodes.items():
        # Existing keys may already be referenced elsewhere, so only new servers have to follow the format
        if is_new and not GAMEMODE_KEY.match(key):
            report.error(f'- The gamemode key **{key}** may only contain lowercase letters, digits, `-` and `_`')
        for field in gamemode:
            if field not in GAMEMODE_KEYS:
                report.error(f'- Unknown key **{field}** in gamemode **{key}**, allowed are: '
                             f'{", ".join(GAMEMODE_KEYS)} (`gamemodes.{key}.{field}`)')

        if gamemode.get('name') in (None, '', '-') or not HEX_COLOR.match(gamemode.get('color', '')):
            report.error(f'- Please add a name or a color to the gamemode {key}')
        for field in ['url', 'versions', 'command']:
            if field in gamemode and gamemode[field] in ('', '-'):
                report.error(f'- Please remove the empty {field} key in gamemode **{key}** or fill in information.')

        versions = gamemode.get('versions')
        if versions not in (None, '', '-'):
            problem = check_versions(versions)
            if problem:
                report.error(f'- {problem}, use e.g. `1.8<*` or `1.17<1.19.1` (`gamemodes.{key}.versions`)')

    icons = os.path.join(directory, 'gamemodes')
    if os.path.isdir(icons):
        for key in sorted(os.listdir(icons)):
            if not key.startswith('.') and key not in gamemodes:
                report.error(f'- There is an icon for the gamemode **{key}**, but no gamemode with this key. '
                             'Please add the gamemode or remove the icon')


def check_versions(versions):
    """Mirrors the version ranges LabyMod understands: `from<to`, `*` for open ends, several separated by commas."""
    for entry in versions.split(','):
        if not VERSION_RANGE.match(entry):
            return f'`{versions}` is not a valid version range'
        bounds = [tuple(int(part) for part in bound.split('.')) for bound in entry.split('<')
                  if re.fullmatch(r'\d+(?:\.\d+)*', bound)]
        if len(bounds) == 2 and bounds[0] > bounds[1]:
            return f'The version range `{entry}` starts after it ends'
    return None


def validate_party(party):
    if not isinstance(party, dict):
        return ['- `party` has to be an object. Please recheck the '
                f'[party object]({DOCS_URL}#party-object).']

    errors = []
    for key in PARTY_REQUIRED_KEYS:
        if key not in party:
            errors.append(f'- The party command **{key}** is required (`party.{key}`)')

    for key, command in party.items():
        if key not in PARTY_KEYS:
            errors.append(f'- Unknown party command **{key}**, allowed are: {", ".join(PARTY_KEYS)} (`party.{key}`)')
            continue
        if not isinstance(command, str) or command.strip() in ('', '-'):
            errors.append(f'- Please remove the empty party command **{key}** or fill in information (`party.{key}`)')
            continue
        if not command.startswith('/'):
            errors.append(f'- Party commands have to start with **/** (`party.{key}`)')
        if key in PARTY_PLAYER_KEYS and '{userName}' not in command:
            errors.append(f'- Please use {{userName}} for the other player in the party command (`party.{key}`)')

    return errors


def check_server(ip, report):
    offline_text = ('In general, we only accept pull requests from servers, **that are online and publicly '
                    'available**.\nPlease change this, otherwise we cannot review your server correctly and have '
                    'to deny the pull request.')
    print(f'Check server status for {ip}')
    status = fetch_status(ip)
    if status is None:
        report.fact('Server', 'status could not be checked')
        return None

    if not status['online']:
        report.fact('Server', f'offline ({status["source"]})')
        report.note(f'- Your server {ip} **could be offline**.\n{offline_text}\n\n'
                    f'Reference: [API URL ({status["url"]})]({status["url"]})')
        return status

    players = status['players']
    report.fact('Server', f'online, {status["version"] or "unknown version"}, {players[0]}/{players[1]} players')
    report.fact('MOTD', ' / '.join(line.strip() for line in status['motd'] if line.strip()) or '-')

    texts = [str(text or '').lower() for text in status['motd'] + status['sample'] + [status['version']]]
    if any(keyword in text for text in texts for keyword in MAINTENANCE_KEYWORDS):
        report.error(f'- The server {ip} **is in maintenance**.\n{offline_text}')
    else:
        print('No maintenance found in MOTD, version nor player list')
    return status


def fetch_status(host):
    """Returns the normalized status of a Minecraft server, or None if no status API answered."""
    url = f'https://api.mcsrvstat.us/3/{host}'
    data = get_json(url)
    if data is not None and data.get('online'):
        players = data.get('players') or {}
        return {
            'online': True, 'source': 'mcsrvstat.us', 'url': url, 'ip': data.get('ip'),
            'motd': (data.get('motd') or {}).get('clean') or [],
            'version': str(data.get('version') or ''),
            'players': (players.get('online'), players.get('max')),
            'sample': [player.get('name', '') for player in players.get('list') or []],
            'icon': data.get('icon'),
        }

    # Recheck with another service
    fallback_url = f'https://api.mcstatus.io/v2/status/java/{host}?query=false'
    fallback = get_json(fallback_url)
    if fallback is None:
        return None if data is None else {'online': False, 'source': 'mcsrvstat.us', 'url': url, 'ip': data.get('ip')}
    url = fallback_url

    players = fallback.get('players') or {}
    version = fallback.get('version') or {}
    motd = (fallback.get('motd') or {}).get('clean') or ''
    return {
        'online': bool(fallback.get('online')), 'source': 'mcstatus.io', 'url': url,
        'ip': fallback.get('ip_address'),
        'motd': motd.splitlines() if isinstance(motd, str) else motd,
        'version': version.get('name_clean', '') if isinstance(version, dict) else str(version),
        'players': (players.get('online'), players.get('max')),
        'sample': [player.get('name_clean', '') for player in players.get('list') or []],
        'icon': fallback.get('icon'),
    }


def check_wildcards(ip, wildcards, status, report):
    """A wildcard has to belong to the server: same domain as the direct IP, or a domain pointing to the same server."""
    own_domain = DOMAINS(ip).registered_domain
    foreign = []
    for wildcard in wildcards:
        domain = wildcard[2:]
        if DOMAINS(domain).registered_domain == own_domain:
            continue

        print(f'Checking wildcard "{wildcard}"')
        other = fetch_status(domain)
        if status and status.get('ip') and other and other.get('online') and other.get('ip') == status['ip']:
            continue
        foreign.append(wildcard)
        report.note(f'- The wildcard `{wildcard}` does not belong to the domain of `{ip}`, and `{domain}` does not '
                    'point to the same server. Please only add domains of your own server (`server_wildcards`)')
    report.fact('Wildcards', f'{len(wildcards)} checked, {len(foreign)} not pointing to this server')


def describe_favicon(status, icon_path):
    if not status or not status.get('icon'):
        return 'no server favicon'
    if not os.path.isfile(icon_path):
        return 'no icon.png to compare'
    try:
        favicon = Image.open(BytesIO(b64decode(status['icon'].split(',', 1)[1])))
        distance = sum(a != b for a, b in zip(image_hash(favicon), image_hash(Image.open(icon_path))))
    except Exception as e:
        return f'could not be compared ({e})'
    return f'{"matches" if distance <= 12 else "differs from"} icon.png (distance {distance}/64)'


def image_hash(image):
    """Difference hash, robust against scaling and compression."""
    image = image.convert('RGBA')
    background = Image.new('RGBA', image.size, (128, 128, 128, 255))
    pixels = Image.alpha_composite(background, image).convert('L').resize((9, 8), Image.LANCZOS).tobytes()
    return [pixels[row * 9 + column] > pixels[row * 9 + column + 1] for row in range(8) for column in range(8)]


def http_status(url):
    try:
        with SESSION.get(url, timeout=TIMEOUT, stream=True) as response:
            return response.status_code
    except requests.RequestException:
        return None


def get_json(url):
    try:
        response = SESSION.get(url, timeout=TIMEOUT)
        return response.json() if response.ok else None
    except (requests.RequestException, ValueError):
        print(f'Cannot get a value from {url} - Skipping...')
        return None


def render(reports, kind):
    sections = []
    for report in reports:
        messages = getattr(report, kind)
        if not messages:
            continue
        body = '\n'.join(messages)
        sections.append(f'**{report.path}**\n{body}' if len(reports) > 1 else body)
    return '\n\n'.join(sections)


def write_summary(reports):
    path = os.getenv('GITHUB_STEP_SUMMARY')
    if not path:
        return
    lines = ['### Manifests']
    if not reports:
        lines.append('No manifest changed.')
    for report in reports:
        lines.append(f'#### {report.path}')
        lines.extend(f'- **{label}:** {str(value).replace("<", "&lt;")}' for label, value in report.facts)
        lines.extend(f'- :x: {message.lstrip("- ")}' for message in report.errors)
        lines.extend(f'- :information_source: {message.lstrip("- ")}' for message in report.notes)
    with open(path, 'a', encoding='utf-8') as file:
        file.write('\n'.join(lines) + '\n')


class GitHub:
    """Keeps one review for the errors and one comment for the notes, instead of a new one per push."""

    def __init__(self, token, pull_request):
        self.pull_request = pull_request
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/vnd.github+json', 'Authorization': f'Bearer {token}'})

    @staticmethod
    def from_env():
        token, pull_request = os.getenv('GH_TOKEN'), os.getenv('PR_ID')
        return GitHub(token, pull_request) if token and pull_request else None

    def request(self, method, path, **kwargs):
        response = self.session.request(method, f'https://api.github.com/repos/{REPOSITORY}/{path}',
                                        timeout=TIMEOUT, **kwargs)
        print(f'Github request {method} {path} returned {response.status_code}')
        return response

    def list(self, path):
        items, page = [], 1
        while page <= 10:
            response = self.request('GET', path, params={'per_page': 100, 'page': page})
            if not response.ok or not response.json():
                break
            items += response.json()
            page += 1
        return items

    def sync_review(self, errors):
        reviews = [review for review in self.list(f'pulls/{self.pull_request}/reviews')
                   if review['user']['login'] == BOT_LOGIN and review['state'] == 'CHANGES_REQUESTED']
        body = f'{errors}\n\nPlease push a commit with the fixes, this review updates itself.' if errors else None
        if body and reviews and (reviews[-1]['body'] or '').strip() == body.strip():
            print('Errors did not change, keeping the current review.')
            return

        for review in reviews:
            message = 'Outdated, see the latest review.' if body else 'Resolved, the latest check passed.'
            self.request('PUT', f'pulls/{self.pull_request}/reviews/{review["id"]}/dismissals',
                         json={'message': message, 'event': 'DISMISS'})
        if body:
            self.request('POST', f'pulls/{self.pull_request}/reviews', json={'body': body, 'event': 'REQUEST_CHANGES'})

    def sync_comment(self, notes):
        comments = [comment for comment in self.list(f'issues/{self.pull_request}/comments')
                    if comment['user']['login'] == BOT_LOGIN and MARKER in comment['body']]
        if notes:
            body = f'{MARKER}\n*Just as an information*:\n\n{notes}'
        elif comments:
            body = f'{MARKER}\nThe notes of the earlier checks are resolved.'
        else:
            return

        if not comments:
            self.request('POST', f'issues/{self.pull_request}/comments', json={'body': body})
        elif comments[0]['body'] != body:
            self.request('PATCH', f'issues/comments/{comments[0]["id"]}', json={'body': body})


if __name__ == '__main__':
    main()
