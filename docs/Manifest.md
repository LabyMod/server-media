# Manifest.json

## Available keys
| Key         | Description            | Example value    |
|-------------|----------------------------|------------------|
| `server_name *` | Short server name          | "laby"           |
| `nice_name *`   | Nice server name           | "LabyMod"        |
| `direct_ip *`   | Direct Minecraft server ip | play.labymod.net |
| `server_wildcards`   | Wildcards the user can use | ["%.laby.net", "%.labymod.net"] |
| `social.web`   | Website **URL** | "https://labymod.net" |
| `social.web_shop`   | Shop **URL** | "https://labymod.net/shop" |
| `social.web_support`   | Support page **URL**, e.g. faq page | "https://labymod.net/support" |
| `social.twitter`   | Twitter **username** | "https://labymod.net/support" |
| `social.discord`   | Discord invite **URL** | "https://discord.gg/labymod" |
| `social.teamspeak`   | TeamSpeak server address | "ts.labymod.net" |
| `social.tiktok`   | TikTok **username** | "LabyMod" |
| `social.facebook`   | Facebook **username** | "LabyMod" |
| `social.youtube`   | YouTube channel **URL** | "https://www.youtube.com/channel/UCSamgE1KYvC7qZn56T0J2yg" |
| `social.instagram`   | Instagram **username** | "LabyMod" |
| `brand.primary`   | Primary brand color | "#008FE8" |
| `brand.background`   | Background-color | "#0A56A5" |
| `brand.primary`   | Text color (*must match the background color*) | "#FFFFFF" |
| `yt_trailer`   | YouTube trailer **embed ID** | "vNF-ztQGnUo" |
| `user_stats`   | User stats url | "https://laby.net/@{username}" *or* "https://laby.net/@{uuid}" |
|  `discord.server_id`   | Discord server id | "260471731809026048" |
|  `discord.rename_to_minecraft_name`   | Boolean whether the user should be renamed when joining. | true |
Required values are: `server_name`, `nice_name` & `direct_ip`

## Example manifest.json file
```json
{
  "server_name": "laby",
  "nice_name": "LabyMod",
  "direct_ip": "play.laby.net",
  "server_wildcards": [
    "%.laby.net"
  ],
  "social": {
    "web": "https://labymod.net/",
    "web_shop": "https://labymod.net/shop",
    "web_support": "https://labymod.net/support",
    "twitter": "LabyMod",
    "discord": "https://discord.com/invite/labymod",
    "teamspeak": "ts.labymod.net",
    "tiktok": "LabyMod",
    "facebook": "LabyMod",
    "youtube": "https://youtube/TODO",
    "instagram": "LabyMod"
  },
  "discord": {
    "server_id": 260471731809026048,
    "rename_to_minecraft_name": true
  },
  "brand": {
     "primary": "#008FE8",
     "background": "#0A56A5",
     "text": "#FFFFFF"
  },
  "yt_trailer": "8asFIRe2HSw",
  "user_stats": "https://laby.net/@{userName}"
}
```