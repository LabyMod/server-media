# Example usages

## Discord - Rich presence

<img src="https://docs.labymod.net/img/discord_rpc_example.png" alt="Discord Rich Presence" width="200">

Icon for [Discord Rich Presence](https://docs.labymod.net/pages/server/labymod/discord_rich_presence/) (as Discord has a
limitation here, we cannot guarantee that as a permanent feature for smaller servers).

## LABY.net

We use all uploaded images for [LABY.net](https://laby.net)! In addition, we use the data from
the [manifest.json](/docs/Manifest.md#example-manifestjson-file) to give interested users more information about the
server.

### Images / Files

<img src="https://user-images.githubusercontent.com/45363287/125614035-5e359ae3-a8ae-49dc-896f-55a0cfbda201.png" width="500"><br>
We use the icon, logo and background image to design the server page.

### Social

<img src="https://user-images.githubusercontent.com/45363287/125614264-0cd99ee6-8014-4307-896d-87601dee8cd9.gif" width="300"><br>
You can show your social accounts on your LABY.net server page.

### Links

<img src="https://user-images.githubusercontent.com/45363287/125614566-210c5088-9279-4ca9-8b13-40a3658c6f6b.png" width="300"><br>
Link your shop, faq and custom player stats page on your server page!
Give users the opportunity to explore your server further!

### Server trailer

<img src="https://user-images.githubusercontent.com/45363287/125614769-f1436ba9-281b-402e-b257-7eb28714869f.png" width="500"><br>
Show users what is happening on a server. - With a YouTube server trailer!

### Colorize your page

<img src="https://user-images.githubusercontent.com/45363287/125615032-08ac824a-cd56-4962-a423-f5d243b8f950.png" width="200"><br>
<img src="https://user-images.githubusercontent.com/45363287/125615115-7d523e2a-c202-4fc0-9b9b-a865db50cde4.png" width="200"><br>
Add your brand colors to your LABY.net server page. We'll use `primary_color` for the background image - `background`
and `text` for elements such as buttons!

### Gamemodes
<img src="https://user-images.githubusercontent.com/45363287/130877774-f3a54c1b-2fc3-417e-81eb-d308c307aac3.png" width="200">
You are able to add your information about gamemodes, that are available on your server!

### One-click discord join (partner-only)

<img src="https://user-images.githubusercontent.com/45363287/125778845-d60d00b7-2e31-4458-8585-0c0b339800be.gif" width="500"><br>
Users who have linked their discord account can join the server with one click.

### Server location

<img src="https://user-images.githubusercontent.com/45363287/130817858-5332b066-edfb-4079-90d6-04be7fa5c776.png" width="200"><br>
We try to detect your servers location by reading an api request. If there is something wrong, you can give us custom
information about the location of your server, that will be added to your LABY.net-page!

### Language specific results

You can add the supported languages on your server to your manifest-file! We can then locate your server and your
community better to improve features!

## LabyMod party

LabyMod players can form a party with their friends in the LabyMod chat. The party is a temporary group chat and works
on every server: when the party leader joins another server, all members are asked whether they want to follow. On a
server listed in this repository they follow on their own after a short countdown, unless they choose to stay.

If your manifest contains a [party object](Manifest.md#party-object), LabyMod also mirrors the party into the party
system of your server:

1. As soon as the leader and a member are both on your server, the leader's client sends `invite` for that member.
2. The member's client answers with `accept`, so the member ends up in the party of the leader on your server.
3. Members who came along with the leader are brought onto the leader's sub server: a few seconds after the last of
   them was invited, the leader's client sends `warp` once. Members who come later, or every member if your server has
   no `warp`, send `jump` once after accepting.
4. From then on your own party system takes over, e.g. members are pulled into a gamemode when the leader joins it.
5. When a member leaves the LabyMod party, `leave` (member) or `kick` (leader) is sent. `disband` is sent when the leader
   ends the party, `transfer` when the leadership moves to another member.

Commands are sent as regular chat commands of the player, only after the `command_delay` of your manifest has passed
since joining, and never more than one per second.

Without a party object the LabyMod party still works, but the members are not grouped on your server. LabyMod then
tells the players that your server is not supported yet and links to this repository.
