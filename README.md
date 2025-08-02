<p align="center">
  <img width="200" src="misc/DeformBot_logo_500_transparent.png">
</p>

<p align="center">
  <a href="https://discord.com/oauth2/authorize?client_id=971742838024978463&permissions=140660558912&scope=bot">
    <img src="https://img.shields.io/badge/Add to your server-7289DA?style=flat&logo=discord&logoColor=white">
  </a>
  <a href="https://twitter.com/DeformBot">
    <img src="https://img.shields.io/badge/@DeformBot-1DA1F2?style=flat&logo=twitter&logoColor=white">
  </a>
  <a href="https://bjarne.dev">
    <img src="https://img.shields.io/badge/bjarne.dev-ttf?style=flat&logo=devdotto&logoColor=white"/>
  </a>
  <br>
</p>

<p align="center">funny picture go brrr</p>

- Made with ❤️ and python

# DeformBot
An Open Source Image distortion discord bot based on the old version of [@DistortBot](https://twitter.com/DistortBot) on twitter build by [@SergioSV96](https://github.com/SergioSV96).

# Add to your server
[Click here](https://discord.com/oauth2/authorize?client_id=971742838024978463&permissions=140660558912&scope=bot) to add DeformBot to your discord server.

# Usage
DeformBot's command prefix is `§`.\
You can display the help message with `§help`.\
Reacting to an image with the `🤖`-emoji will trigger DeformBot to process it.\
Additionally `§deform` alias `§d` causes the bot to use the attached image of the message containing the command (or the image replied to with a command).

[NOTE] `$` now works as a prefix too!

# Command arguments
Arguments for the `§d` command can be used as follows:\
`§deform [option0][value] [option1][value] ...`
| option | description                | value type | value range  |
|:------:|----------------------------|:----------:|--------------|
| l      | seam carving factor        | int        | [0; 100]     |
| s      | swirl                      | int        | [-360; +360] |
| n      | noise                      | int        | [0; 100]     |
| b      | blur                       | int        | [0; 100]     |
| c      | contrast                   | int        | [-100; 100]  |
| o      | implode                    | int        | [-100; 100]  |
| d      | shepard's distortion (IWD) | int        | [0; 100]     |
| w      | wave                       | int        | [0; 100]     |
| r      | rotate (clockwise)         | int        | [-360; +360] |
| f      | flip (horizontal, vertical)| string     | ['h','v']    |
| a      | anaglyph (cyan-red 3D)     | bool       |              |
| i      | invert colors              | bool       |              |
| g      | grayscale colors           | bool       |              |
| u      | disable compression        | bool       |              |

All arguments can be arbitrarily combined or left out.
Only integer values are accepted, I advise to play around with those values to find something that looks good.\
\
<ins>Examples for Discord:</ins>\
`§deform` (default arguments)\
`§deform s35 n95 l45 c+40 b1`\
`§deform l50 s25 c+30 n70 g`\
`§deform l0 u` (this outputs the original image)

# Twitter
[@DeformBot](https://twitter.com/DeformBot) on Twitter will distort an image, if you tag him in the replies.\
To use command arguments simply append them after the mention.\
`@DeformBot [option0][value] [option1][value] ...`\
\
<ins>Examples for Twitter:</ins>\
`@DeformBot` (default arguments)\
`@DeformBot s35 n95 l45 c+40 b1`\
`@DeformBot l50 s25 c+30 n70 g`\
`@DeformBot l0 u` (this outputs the original image)

# Self hosting
If you want to self host deformbot, the most simple way is to use the docker image with docker compose.
for this, you must place a `.env` file conatining the information specified in [.env.example](https://github.com/bj4rnee/DeformBot/blob/main/discord/.env.example) in the
root folder of the repository (where the `.git` folder is).\
After that is done just build the image with `docker compose up --build`.

# Privacy policy
[Here](https://github.com/bj4rnee/DeformBot/blob/main/misc/PRIVACY.md) you can check out DeformBot's privacy policy.

# What's Next
- GIF support [beta]
- trigger typing indicator [beta]
- search for last image on command if nothing else is found [beta]
- fix reply to sensitive image not being sensitive on twitter
- fix twitter functions blocking shard heartbeat
- deform multiple images on twitter [beta]
- .PNG support

# Known Bugs
- invalid argument error embed on discord refers to twitter
- pictures with alpha channel can be buggy sometimes
- blur argument must be placed before noise
- the output of a slash command can be flipped vertically

# Credits
[@rupansh](https://github.com/rupansh) for the idea
