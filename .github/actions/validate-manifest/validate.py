import json
import os
import requests
from sys import exit as sys_exit

REQUIRED_KEYS = ['server_name', 'nice_name', 'direct_ip']
USERNAME_SOCIAL_KEYS = ['twitter', 'tiktok', 'facebook', 'instagram', 'teamspeak']
URL_SOCIAL_KEYS = ['web', 'web_shop', 'web_support', 'youtube', 'discord']
BRAND_KEYS = ['primary', 'background', 'text']


def main():
    error = ''
    comment = ''
    wildcard_stop = False

    create_comment = comment_needed()
    if not create_comment:
        print('No manifest file changed, comment will be skipped.')

    manifest_files = get_changed_manifest_files()

    if len(manifest_files) == 0:
        print('There are no changed manifest files in this pull request.')
        return

    for manifest_file in manifest_files:
        if manifest_file == 'minecraft_servers/manifest.json':
            continue
        try:
            with open(manifest_file) as file:
                print(f'Open manifest file: {manifest_file}')

                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    error += f'- JSON is invalid! Workflow is not able to check {manifest_file}\n'
                    continue
        except FileNotFoundError:
            print(f'Unable to open {manifest_file} - Continue...')
            continue

        # Check for required keys
        if not all(key in data for key in REQUIRED_KEYS):
            error += '- One of the **required values** is missing\n'
            continue

        if data['direct_ip'] in ['', '-']:
            error += f'- Direct IP is required\n'
        if data['nice_name'] in ['', '-']:
            error += f'- Nice name is required and cannot be empty!\n'

        server_directory = manifest_file.replace('minecraft_servers/', '').replace('/manifest.json', '')
        if server_directory != data['server_name']:
            error += '**Servername has to be directory name!** (all lowercase)\n'

        # Validate wildcards
        if 'server_wildcards' in data:
            for wildcard in data['server_wildcards']:
                if not wildcard.startswith('%.'):
                    wildcard_stop = True
                    error += '- Invalid wildcard entry. Each entry must start with **%.**. Further information here: https://en.wikipedia.org/wiki/Wildcard_DNS_record (`server_wildcards`)\n'
                print(f'Found valid wildcard entry: {wildcard}')

        check_server_online_state(
            data['direct_ip'],
            [] if wildcard_stop else (data['server_wildcards'] if 'server_wildcards' in data else [])
        )

        # Check for https
        if 'social' in data:
            social = data['social']
            for key in URL_SOCIAL_KEYS:
                if key not in social:
                    continue
                if not social[key].startswith('https://'):
                    error += f'- Invalid url. URL has to start with **https://** (`social.{key}`)\n'
                if social[key].endswith('/'):
                    error += f'- Please remove **/** at the end of url (`social.{key}`)\n'

                try:
                    response = requests.get(social[key], timeout=5)
                except requests.exceptions.RequestException as e:
                    comment += f'- The website {social[key]} **could not be reached**. Please recheck whether is available.\n'

            if 'discord' in social:
                link = social['discord']
                if not link.startswith(('https://discord.gg', 'https://discord.com')):
                    comment += f'- Custom Discord invites are reserved for **LabyMod Partners**.\nIf you are a partner, please ignore this message.\n'
                    print(f'Did not check invite for validity: {link}')
                else:
                    if not check_discord_invite(link):
                        error += f'- The Discord invite {link} is **invalid** or Discord is down.\n'


            for key in USERNAME_SOCIAL_KEYS:
                if key in social and (social[key].startswith('http') or 'www' in social[key]):
                    error += f'- Please use a **username**, not a link (`social.{key}`)\n'
                if key in social and social[key] in ('', '-'):
                    error += f'- Please remove the empty key **{key}** or fill in information.\n'

            # Check facebook, because it works :)
            if 'facebook' in social:
                facebook_username = social['facebook']
                request = requests.get(f'https://facebook.com/{facebook_username}')
                if request.status_code == 404:
                    error += f'- Invalid facebook account: https://facebook.com/{facebook_username} ' \
                               f'(`social.facebook`)\n'

        # check for numeric server id (discord)
        if 'discord' in data:
            try:
                int(data['discord']['server_id'])
            except ValueError:
                error += f'- Please use a **numeric** value for your server id (`discord.server_id`)\n'
            if 'rename_to_minecraft_name' in data['discord'] and data['discord']['rename_to_minecraft_name'] == True:
                comment += f'- `discord.rename_to_minecraft_name` is reserved for LabyMod Partners. Change it to `false`.' \
                            'If you are a partner, please ignore this message.\n'


        if 'location' in data:
            if 'city' in data['location'] and data['location']['city'] in ['', '-']:
                error += f'- Please remove the empty key **city** or fill in information.\n'

            if 'country_code' in data['location']:
                country_code = data['location']['country_code']
                if len(country_code) > 2 or len(country_code) <= 1:
                    error += '- Use valid format (ISO 3166-1 alpha-2) for country code. (`location.country_code`)\n'

                if not country_code.isupper():
                    error += '- Use upper-case for country code. (`location.country_code`)\n'

        # check hex codes
        if 'brand' in data:
            for key in BRAND_KEYS:
                if key in data['brand'] and '#' not in data['brand'][key]:
                    error += f'- Please enter a valid hex-code (`brand.{key})`\n'

        if 'user_stats' in data:
            stats_url = data['user_stats']
            if not stats_url.startswith('https://'):
                error += f'- Invalid url. URL has to start with **https://** (`user_stats`)\n'
            if '{userName}' not in data['user_stats'] and '{uuid}' not in data['user_stats']:
                error += '- Please use {userName} or {uuid} in your stats url (`user_stats`)\n'

            if '://laby.net/' in stats_url:
                error += f'- Please use **your own page**, not LABY.net (`user_stats`)\n'

        if 'chat' in data and 'message_formats' in data['chat']:
            message_format = data['chat']['message_formats']
            if isinstance(message_format, list):
                if len(message_format) == 1:
                    message_format = message_format[0]
                else:
                    error += f'**message_format** has the wrong format. Please recheck the [example manifest](https://github.com/LabyMod/server-media/blob/master/docs/Manifest.md#chat-object).'

            template_regex = '^§[a-f0-9](?<level>\\d+)( \\||§8 \\|) §[a-f0-9](?<sender>[a-zA-Z0-9_]{2,16})§r§7: §f(?<message>.*)$'
            if template_regex == message_format:
                comment += f'- It seems you\'re using the **template regex** for chat message! Please make sure it is the right regex for **your server**!'
            if message_format in ('', '-'):
                error += f'- Please remove the empty key **message_formats** or fill in information.\n'


        if 'gamemodes' in data:
            gamemodes = data['gamemodes']
            for key, gamemode in gamemodes.items():
                if 'name' not in gamemode or 'color' not in gamemode or gamemode['name'] in ('', '-') or '#' not in gamemode['color']:
                    error += f"- Please add a name or a color to the gamemode {key}\n"
                if 'url' in gamemode and gamemode['url'] in ('', '-'):
                    error += f"- Please remove the empty url key in gamemode **{key}** or fill in information.\n"
                if 'versions' in gamemode and gamemode['versions'] in ('', '-'):
                    error += f"- Please remove the empty version key in gamemode **{key}** or fill in information.\n"
                if 'command' in gamemode and gamemode['command'] in ('', '-'):
                    error += f"- Please remove the empty command key in gamemode **{key}** or fill in information.\n"



    if create_comment:
        if error != '':
            post_comment(error)
        if comment != '':
            temp_comment = comment
            comment = '*Just as an information*:\n\n'
            comment += temp_comment
            post_comment(comment, 'comments')

    if error != '':
        # Make job fail
        sys_exit('Invalid data in manifest.json. See comments above or review in PR for more information.')

    for error in error.split('\n'):
        # Print error comments, so that the user can relate the issues even if there is no comment
        print(error)

    for comment in comment.split('\n'):
        print(comment)


def get_changed_manifest_files():
    print('Getting changed files from json')

    with open('./files.json') as files:
        data = json.load(files)
        changed_files = [changed_file for changed_file in data if changed_file.endswith('manifest.json')
                         and changed_file.startswith('minecraft_servers/')]

    print(changed_files)

    return changed_files


def post_comment(comment: str, request_type: str = 'reviews'):
    if request_type == 'reviews':
        comment += '\nPlease fix the issues by pushing **one** commit to the pull ' \
                   'request to prevent too many automatic reviews.'

    request = requests.post(
        f"https://api.github.com/repos/LabyMod/server-media/"
        f"{'pulls' if request_type == 'reviews' else 'issues'}/{os.getenv('PR_ID')}/{request_type}",
        json={'body': comment, 'event': 'REQUEST_CHANGES'},
        headers={'Accept': 'application/vnd.github.v3+json', 'Authorization': f"Token {os.getenv('GH_TOKEN')}"}
    )

    print(f'Github request returned {request.status_code}, posted into {request_type}.')


def check_server_online_state(ip: str, wildcards: list):
    offline_text = 'In general, we only accept pull requests from servers, **that are online and publicly available**.\nPlease change this, otherwise we cannot review your server correctly and have to deny the pull request.\n\n'
    print(f'Check server status for {ip}')

    url = f'https://api.mcsrvstat.us/2/{ip}'
    request = requests.get(url)

    try:
        response = json.loads(request.text)
    except json.JSONDecodeError:
        print(f'Cannot get value from server API. API returned {request.status_code} - Skipping...')
        return

    server_ip = response['ip']
    print(f"Checked server status successfully: {response['online']}")

    if not response['online']:
        print(f'Rechecking with another service')
        url = f'https://api.mcstatus.io/v2/status/java/{ip}?query=false'
        request = requests.get(url)

        try:
            response = json.loads(request.text)
        except json.JSONDecodeError:
            print(f'Cannot get value from server API. API returned {request.status_code} - Skipping...')
            return

        server_ip = response['ip_address']
        print(f"Checked server status successfully: {response['online']}")

        offline_text += f"Reference: [API URL ({url})]({url})"

        if not response['online']:
            post_comment(f'*Just as an information*:\nYour server {ip} **could be offline**.\n {offline_text}', 'comments')

    wildcard_string = '*Just as an information regarding your wildcards*:\n'
    wildcard_comment = False
    for wildcard in wildcards:
        print(f'Checking wildcard "{wildcard}"')
        wildcard_ip = str.replace(wildcard, '%', 'testingstringwildcard')
        request = requests.get(f'https://api.mcsrvstat.us/2/{wildcard_ip}')

        try:
            response = json.loads(request.text)
        except json.JSONDecodeError:
            print(f'Cannot get {wildcard} from server API. API returned {request.status_code} - Skipping...')
            continue

        if not response['online']:
            print(f'Wildcard "{wildcard}" is offline')
            wildcard_string += f'- Wildcard {wildcard} seems to be invalid. Server is offline with testing wildcard.\n'
            wildcard_comment = True
        else:
            print(f'Wildcard "{wildcard}" is online')
            if response['ip'] != server_ip:
                wildcard_string += f'- Wildcard do not resolve the same ip address: *{wildcard}* => *{response["ip"]}*\n'
                wildcard_comment = True

    wildcard_string += f'\nPlease make sure it is an [actual wildcard](https://en.wikipedia.org/wiki/Wildcard_DNS_record).\n'
    if wildcard_comment:
        post_comment(wildcard_string, 'comments')
    if 'motd' in response or 'version' in response:
        maintenance_tagged = False
        if 'motd' in response:
            for line in response['motd']['clean']:
                line_content = line.lower()
                if any(keyword in line_content for keyword in ['maintenance', 'wartung', 'wartungen', 'mantenimiento', 'wartungsarbeiten']):
                    maintenance_tagged = True
        if 'version' in response:
            version_name = response['version']

            if isinstance(version_name, str):
                version_name = version_name.lower()
            if isinstance(version_name, dict) and 'name_clean' in version_name:
                version_name = version_name['name_clean'].lower()

            if any(keyword in version_name for keyword in ['maintenance', 'wartung', 'wartungen', 'mantenimiento', 'wartungsarbeiten']):
                maintenance_tagged = True

        if maintenance_tagged:
            post_comment(f'The server {ip} **is in maintenance**.\n {offline_text}')
        else:
            print(f'No maintenance found in MOTD nor version')


def comment_needed():
    pr_action = os.getenv('PR_ACTION')
    if pr_action in ['opened', 'reopened', 'synchronize']:
        print('PR opened - Write comment.')
        return True

    request = requests.get(
        os.getenv('COMMIT_URL')[:-6] + '/' + os.getenv('COMMIT_SHA'),
        headers={'Accept': 'application/vnd.github.v3+json', 'Authorization': f"Token {os.getenv('GH_TOKEN')}"}
    )

    try:
        response = json.loads(request.text)
        if 'files' not in response:
            print('No changed files in commit.')
            return False

        return any(file['filename'].endswith('manifest.json') for file in response['files'])
    except json.JSONDecodeError:
        print(f'Cannot fetch commit.')

    return False

def check_discord_invite(url: str):
    invite = url.split('/')[-1]
    print(f'Check discord invite for {invite}')

    try:
        request = requests.get(f'https://discord.com/api/v9/invites/{invite}')
        if request.status_code == 200:
            print(f'Invite for {invite} was successful.')

            response_data = request.json()
            guild_data = response_data.get('guild', {})
            if isinstance(guild_data, dict):
                guild_name = guild_data.get('name', 'Unknown Guild')
            else:
                guild_name = 'Unknown Guild'
            print(f'Guild name: {guild_name}')

            return True
        else:
            print(f'Invite for {invite} was invalid.')
            return False
    except requests.exceptions.ConnectionError:
        print(f'Discord seems to be down while checking. Please check manually\n')
        return False

if __name__ == '__main__':
    main()