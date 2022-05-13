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
An Open Source Image distortion discord bot based on the old version of [@DistortBot](https://twitter.com/DistortBot) on twitter build by [@SergioSV96](https://github.com/SergioSV96)

# Add to your server
[click here](https://discord.com/oauth2/authorize?client_id=971742838024978463&permissions=140660558912&scope=bot) to add DeformBot to your discord server

# Usage
DeformBot's command prefix is `§`.\
You can display the help message with `§help`.\
Reacting to an image with the `🤖`-emoji will trigger DeformBot to process it.\
Additionally `§deform` alias `§d` causes the bot to use the attached image of the message containing the command (or the image replied to with a command).

# Command arguments
Arguments for the `§d` command can be used as followed:\
`§deform [option0][value] [option1][value] ...`
| option | description                 | value type | value range  |
|:------:|-----------------------------|:----------:|--------------|
| l      | seam carving factor         | int        | [0; 100]     |
| s      | swirl                       | int        | [-360; +360] |
| n      | noise                       | int        | [0; 100]     |
| b      | blur                        | int        | [0; 100]     |
| c      | contrast                    | int        | [-100; 100]  |
| o      | implode                     | int        | [0; 100]     |
| p      | perspective distortion (IWD)| int        | [0; 100]     |
| i      | invert colors               | bool       |              |
| g      | grayscale colors            | bool       |              |
| u      | disable compression         | bool       |              |

All arguments can be arbitrarily combined or left out.
Only integer values are accepted, I advise to play around with those values to find something that looks good.\
\
Examples:\
_§deform_\
_§deform s35 n95 l45 c+40 b1_\
_§deform l50 s25 c+30 n70 g_\
_§deform l0 u_ (this outputs the original image)

# Twitter
[@Deformbot](https://twitter.com) on Twitter will distort an image, if you tag him in the comments.

# Privacy policy
[Here](https://github.com/bj4rnee/DeformBot/blob/main/misc/PRIVACY.md) you can check out DeformBot's privacy policy.

# Credits
[@rupansh](https://github.com/rupansh) for the idea
