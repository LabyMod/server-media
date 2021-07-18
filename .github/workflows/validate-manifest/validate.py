import json
import os
import requests
from sys import exit as sys_exit

REQUIRED_KEYS = ['server_name', 'nice_name', 'direct_ip']
USERNAME_SOCIAL_KEYS = ['twitter', 'tiktok', 'facebook', 'instagram', 'teamspeak']
URL_SOCIAL_KEYS = ['web', 'web_shop', 'web_support', 'youtube', 'discord']
BRAND_KEYS = ['primary', 'background', 'text']


def main():
    comment = ''
    for manifest_file in get_changed_manifest_files():
        with open(manifest_file) as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                comment += '- [ ] One of the **required values** is missing\n'
                continue

        # Check for required keys
        if not all(key in data for key in REQUIRED_KEYS):
            comment += '- [ ] One of the **required values** is missing\n'
            continue

        server_directory = manifest_file.replace('minecraft_servers/', '').replace('/manifest.json', '')
        if server_directory != data['server_name']:
            comment += '**Servername has to be directory name!**'

        # Check for https
        if 'social' in data:
            social = data['social']
            for key in URL_SOCIAL_KEYS:
                if key in social and not social[key].startswith('https://'):
                    comment += f'- [ ] Please use **https://** instead of http:// (`social.{key}`)\n'

            for key in USERNAME_SOCIAL_KEYS:
                if key in social and (social[key].startswith('http') or 'www' in social[key]):
                    comment += f'- [ ] Please use a **username**, not a link (`social.{key}`)\n'

            # Check facebook, because it works :)
            if 'facebook' in social:
                facebook_username = social['facebook']
                request = requests.get(f'https://facebook.com/{facebook_username}')
                if request.status_code == 404:
                    comment += f'- [ ] Invalid facebook username not available: {facebook_username} ' \
                               f'(`social.facebook`)\n'

        # check for numeric server id (discord)
        if 'discord' in data:
            try:
                int(data['discord']['server_id'])
            except ValueError:
                comment += '- [ ] Please use a **numeric** value for your server id (`discord.server_id`)\n'

        # check hex codes
        if 'brand' in data:
            for key in BRAND_KEYS:
                if key in data['brand'] and '#' not in data['brand'][key]:
                    comment += f'- [ ] Please enter a valid hex-code (`brand.{key})`\n'

        if 'user_stats' in data:
            stats_url = data['user_stats']
            if not stats_url.startswith('https://'):
                comment += f'- [ ] Please use **https://** (`user_stats`)\n'

            if '://laby.net/' in stats_url:
                comment += f'- [ ] Please use **your own page**, not LABY.net (`user_stats`)\n'

    post_comment(comment)


def get_changed_manifest_files():
    print('Getting changed files from json')

    with open('./files.json') as files:
        data = json.load(files)
        changed_files = [changed_file for changed_file in data if changed_file.endswith('manifest.json')]

    print(changed_files)

    return changed_files


def post_comment(comment: str):
    if comment == '':
        print('Seems valid so far! We do not need a comment.')
        return

    request = requests.post(
        f"https://api.github.com/repos/LabyMod/server-media/pulls/{os.getenv('PR_ID')}/reviews",
        json={'body': comment, 'event': 'REQUEST_CHANGES'},
        headers={'Accept': 'application/vnd.github.v3+json', 'Authorization': f"Token {os.getenv('GH_TOKEN')}"}
    )

    print(f'Comment GH request: {request.status_code}')

    # Make job fail
    sys_exit('Invalid data in manifest.json')


if __name__ == '__main__':
    main()
