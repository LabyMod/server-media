# Manifest.json

## Available keys

> **Important**: All provided values are just examples. Do not copy them, instead use your own ones!

| Key         | Description            | Example value    |
|-------------|----------------------------|------------------|
| `server_name`* | Short server name (must match the directory name!) | `"laby"`           |
| `nice_name`*   | Nice server name           | `"LabyMod"`        |
| `direct_ip`*   | Direct Minecraft server ip | `"play.labymod.net"` |
| `server_wildcards`   | Wildcards the user can use | `["%.laby.net", "%.labymod.net"]` |
| `supported_languages`   | Supported languages on your server - Format: ISO 639-1 | `["de", "en"]` |
| `social.web`   | [Website **URL**](Usages.md#social) | `"https://labymod.net"` |
| `social.web_shop`   | [Shop **URL**](Usages.md#links) | `"https://labymod.net/shop"` |
| `social.web_support`   | [Support page **URL**](Usages.md#links), e.g. faq page | `"https://labymod.net/support"` |
| `social.twitter`   | [Twitter **username**](Usages.md#social) | `"LabyMod"` |
| `social.discord`   | [Discord invite **URL**](Usages.md#social) | `"https://discord.gg/labymod"` *or* `"https://discord.gg/Wbg7rArky7"` ([Read more](#discord-url)) |
| `social.teamspeak`   | [TeamSpeak server address](Usages.md#social) | `"ts.labymod.net"` |
| `social.tiktok`   | [TikTok **username**](Usages.md#social) | `"LabyMod"` |
| `social.facebook`   | [Facebook **username**](Usages.md#social) | `"LabyMod"` |
| `social.youtube`   | [YouTube channel **URL**](Usages.md#social) | `"https://www.youtube.com/channel/UCSamgE1KYvC7qZn56T0J2yg"` |
| `social.instagram`   | [Instagram **username**](Usages.md#social) | `"LabyMod"` |
| `gamemodes`   | [Gamemodes](Usages.md#gamemodes) | [gamemode object](#gamemode-object) |
| `brand.primary`   | [Primary brand color](Usages.md#colorize-your-page) | `"#008FE8"` |
| `brand.background`   | [Background-color](Usages.md#colorize-your-page) | `"#0A56A5"` |
| `brand.text`   | [Text color](Usages.md#colorize-your-page) (*must fit with the background color*) | `"#FFFFFF"` |
| `location.city`   | [Server location: City](Usages.md#server-location) | `"Berlin"` |
| `location.country`   | [Server location: Country](Usages.md#server-location) | `"Germany"` |
| `location.country_code`   | [Server location: Country code](Usages.md#server-location) - Format: ISO 3166-1 alpha-2 (upper-case) | `"DE"` |
| `yt_trailer`   | [YouTube trailer **embed ID**](Usages.md#server-trailer) | `"vNF-ztQGnUo"` |
| `user_stats`   | [User stats url](Usages.md#links) | `"https://laby.net/@{userName}"` *or* `"https://laby.net/@{uuid}"` |
|  `discord.server_id`   | [Discord server id](Usages.md#one-click-discord-join-partner-only) | `260471731809026048` |
|  `discord.rename_to_minecraft_name`   | Boolean whether the user should be renamed when joining. | `false` |

* Required values are: `server_name`, `nice_name` & `direct_ip`


### Gamemode object
| Key         | Description            | Example value    |
|-------------|----------------------------|------------------|
| `name`* | Gamemode nice name | `"JumpWorld"`           |
| `color`* | Brand color | `"#ADD8E6"`           |
| `url` | Gamemode description url / website related to the gamemode | `"https://www.timolia.de/games#jumpworld"`           |
| `command` | e.g. quickjoin-command | `"/quickjoin jumpworld"`           |

* Required values are: `name` & `color`


### Discord URL

We only support direct discord invite links, such as https://discord.gg/Wbg7rArky7 or https://discord.gg/labymod. Links
like https://labymod.net/dc are only supported for partner servers.<br>
**Why?** Links directly from Discord can be validated well by us for up-to-dateness.

## Example manifest.json file

```json
{
  "server_name": "laby",
  "nice_name": "LabyMod",
  "direct_ip": "play.laby.net",
  "server_wildcards": [
    "%.laby.net"
  ],
  "supported_languages": [
     "en",
     "de"
  ],
  "social": {
    "web": "https://labymod.net/",
    "web_shop": "https://labymod.net/shop",
    "web_support": "https://labymod.net/support",
    "twitter": "LabyMod",
    "tiktok": "LabyMod",
    "facebook": "LabyMod",
    "instagram": "LabyMod",
    "discord": "https://discord.com/invite/labymod",
    "youtube": "https://www.youtube.com/channel/UCSamgE1KYvC7qZn56T0J2yg",
    "teamspeak": "ts.labymod.net"
  },
  "gamemodes": {
    "jumpworld": {
      "name": "JumpWorld", 
      "color": "#FFA500",
      "url": "https://www.timolia.de/games#jumpworld",
      "command": "/quickjoin jumpworld"
    },
    "dna": {
      "name": "DNA",
      "color": "#ADD8E6",
      "url": "https://www.timolia.de/games#dna",
      "command": "/quickjoin dna"
    }
  },
  "discord": {
    "server_id": 260471731809026048,
    "rename_to_minecraft_name": false
  },
  "brand": {
     "primary": "#008FE8",
     "background": "#0A56A5",
     "text": "#FFFFFF"
  }, 
  "location": {
     "city": "Walldorf",
     "country": "Germany",
     "country_code": "DE"
  },
  "yt_trailer": "8asFIRe2HSw",
  "user_stats": "https://laby.net/@{userName}"
}
```
