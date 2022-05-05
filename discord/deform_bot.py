# this is the bot.py
import os
import random
from urllib import request
import psutil
import requests
import uuid
import shutil
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from dotenv import load_dotenv
from io import BytesIO
from glob import glob
from PIL import Image

VERSION = "1.0"
DEBUG = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
COMMAND_PREFIX = '§'

process = psutil.Process(os.getpid())
start_time = datetime.now()

bot = commands.Bot(command_prefix=COMMAND_PREFIX, help_command=None,
                   description="an Open Source image distortion discord bot")
client = discord.Client()

embed_error = discord.Embed(description="No attachments", color=0xFF5555)
embed_error.set_author(name="[Error]", url="https://bjarne.dev/",
                       icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/9e/Barrier_%28held%29_JE2_BE2.png/revision/latest?cb=20200224220440")


def distort_image(fname):
    """function to distort an image using the magick library"""
    image = Image.open(fname)
    imgdimens = image.width, image.height
    distortcmd = f"magick {fname} -liquid-rescale 60x60%! -resize {imgdimens[0]}x{imgdimens[1]}\! results/{fname}"

    os.system(distortcmd)

    buf = BytesIO()
    buf.name = 'image.jpeg'

    image = Image.open(f"results/{fname}")
    filetype = "JPEG" if fname.endswith(".jpg") else "PNG"
    image.save(buf, filetype)

    buf.seek(0)
    return buf


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    # bot.remove_command('help')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content == '§status':
        current_time = datetime.now()
        timestr = 'Uptime:\t{}\n'.format(current_time.replace(
            microsecond=0) - start_time.replace(microsecond=0))
        memstr = 'Memory:\t' + \
            str(round(process.memory_info().rss / 1024 ** 2, 2)) + 'MB'
        response = "```[Debug]\n" + timestr + memstr + "```"
        await message.channel.send(response)

    await bot.process_commands(message)

    # if message.content == '§help':
    #     embed = discord.Embed(title="[Debug embed]")
    #     response = "Hi, I'm an Open Source image distortion discord bot!\n[Website](https://bjarne.dev)\n[Github](https://github.com/bj4rnee/DeformBot)\nCommands:"
    #     await message.channel.send(embed)


@bot.command(name='help', help='Shows usage info', aliases=['h', 'info', 'usage'])
async def help(ctx):
    rand_color = random.randint(0, 0xFFFFFF)
    help_embed = discord.Embed(
        description="[Website](https://bjarne.dev)\n[Github](https://github.com/bj4rnee/DeformBot)\n\n**Commands:**\n`help`:  Shows this help message\n", color=rand_color)
    help_embed.set_author(name="Hi, I'm an Open Source image distortion discord bot!", url="https://bjarne.dev/",
                          icon_url="https://cdn.discordapp.com/avatars/971742838024978463/0aa0248616aa2b215640db6b62ad5961.webp?size=80")
    await ctx.send(embed=help_embed)


@bot.command(name='deform', help='deform an image', aliases=['d', 'distort'])
async def deform(ctx):
    try:
        url = ctx.message.attachments[0].url
    except IndexError:
        await ctx.send(embed=embed_error)
        return
    else:
        if url[0:26] == "https://cdn.discordapp.com":
            r = requests.get(url, stream=True)
            # TODO security check, if file is actually an image!
            image_name = str(uuid.uuid4()) + '.jpg'

            with open(image_name, 'wb') as out_file:
                if DEBUG:
                    print("saving image: "+image_name)
                shutil.copyfileobj(r.raw, out_file)
    await ctx.send("done")

bot.run(TOKEN)
