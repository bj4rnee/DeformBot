# this is the bot.py
import os
import random
import time
from urllib import request
import psutil
import requests
import uuid
import shutil
import asyncio
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from dotenv import load_dotenv
from io import BytesIO
from glob import glob
from PIL import Image

VERSION = "1.1"
# Turn off in production!
DEBUG = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
COMMAND_PREFIX = '§'

process = psutil.Process(os.getpid())
start_time = datetime.now()

bot = commands.Bot(command_prefix=COMMAND_PREFIX, help_command=None,
                   description="an Open Source image distortion discord bot")
client = discord.Client()

embed_nofile_error = discord.Embed(description="No attachments", color=0xFF5555)
embed_nofile_error.set_author(name="[Error]", url="https://bjarne.dev/",
                       icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/9e/Barrier_%28held%29_JE2_BE2.png/revision/latest?cb=20200224220440")

embed_wrongfile_error = discord.Embed(description="Can't process this filetype. Only `.jpg`, `.jpeg` and `.png` are supported at the moment", color=0xFF5555)
embed_wrongfile_error.set_author(name="[Error]", url="https://bjarne.dev/", icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/9e/Barrier_%28held%29_JE2_BE2.png/revision/latest?cb=20200224220440")


def fetch_image(message):
    return

def distort_image(fname):
    """function to distort an image using the magick library"""
    image = Image.open(os.path.join("raw", fname))
    imgdimens = image.width, image.height
    distortcmd = f"magick " + \
        os.path.join(
            "raw", f"{fname}") + f" -liquid-rescale 60x60%! -resize {imgdimens[0]}x{imgdimens[1]}\! " + os.path.join("results", f"{fname}")

    os.system(distortcmd)

    buf = BytesIO()
    buf.name = 'image.jpeg'

    image = Image.open(f"results/{fname}")
    filetype = "JPEG" if fname.endswith(".jpg") else "PNG"
    image.save(buf, filetype)
    image.close()
    buf.seek(0)
    return discord.File(os.path.join("results", f"{fname}"))


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
            str(round(process.memory_info().rss / 1024 ** 2, 2)) + 'MB\n'
        response = "```[Debug]\n" + timestr + memstr + "Vers..:\t" + VERSION + "```"
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
        description="[Website](https://bjarne.dev)\n[Github](https://github.com/bj4rnee/DeformBot)\n[Twitter](https://twitter.com)\n\n**Commands:**\n`help`:  Shows this help message\n`deform`:  Distort an attached image\nYou can also react to an image with `🤖` to quickly deform it.", color=rand_color)
    help_embed.set_author(name="Hi, I'm an Open Source image distortion discord bot!", url="https://bjarne.dev/",
                          icon_url="https://cdn.discordapp.com/avatars/971742838024978463/0aa0248616aa2b215640db6b62ad5961.webp?size=80")
    await ctx.send(embed=help_embed)


@bot.command(name='deform', help='deform an image', aliases=['d', 'distort'])
async def deform(ctx):
    #first delete the existing files
    for delf in os.listdir("raw"):
        if delf.endswith(".jpg"):
            os.remove(os.path.join("raw", delf))

    for delf2 in os.listdir("results"):
        if delf2.endswith(".jpg"):
            os.remove(os.path.join("results", delf2))

    msg = ctx.message #msg with command in it
    reply_msg = None #original msg which was replied to with command 

    if msg.reference != None: # TODO find out which cond should be used
        reply_msg = await ctx.channel.fetch_message(msg.reference.message_id)
        msg = reply_msg
    
    try:
        url = msg.attachments[0].url
    except IndexError:
        await ctx.send(embed=embed_nofile_error)
        return
    else:
        if url[0:26] == "https://cdn.discordapp.com":
            if url[-4:].casefold() == ".jpg".casefold() or url[-4:].casefold() == ".png".casefold() or url[-5:].casefold() == ".jpeg".casefold():
                r = requests.get(url, stream=True)
                image_name = str(uuid.uuid4()) + '.jpg'  # generate uuid

                with open(os.path.join("raw", image_name), 'wb') as out_file:
                    if DEBUG:
                        print("saving image: " + image_name)
                    shutil.copyfileobj(r.raw, out_file)

                    # unfortunately await can't be used here
                    distorted_file = distort_image(image_name)

                    if DEBUG:
                        print("distorted image: " + image_name)
                    # send distorted image
                    if DEBUG:
                        await ctx.send("[Debug] Processed image: " + image_name, file=distorted_file)
                        return
                    await ctx.send(file=distorted_file)
                    return
            else:
                await ctx.send(embed=embed_wrongfile_error)
                return

@bot.event
async def on_reaction_add(reaction, user): # if reaction is on a cached message
    if user != bot.user:
        if str(reaction.emoji) == "🤖":
            #fetch and process the image
            msg = reaction.message
            ch = msg.channel
            try:
                url = msg.attachments[0].url
            except IndexError:
                if DEBUG: # don't send errors on reaction
                    await ch.send(embed=embed_nofile_error)
                return
            else:
                if url[0:26] == "https://cdn.discordapp.com":
                    if url[-4:].casefold() == ".jpg".casefold() or url[-4:].casefold() == ".png".casefold() or url[-5:].casefold() == ".jpeg".casefold():
                        r = requests.get(url, stream=True)
                        image_name = str(uuid.uuid4()) + '.jpg'  # generate uuid

                        with open(os.path.join("raw", image_name), 'wb') as out_file:
                            if DEBUG:
                                print("saving image: " + image_name)
                        shutil.copyfileobj(r.raw, out_file)

                        # unfortunately await can't be used here
                        distorted_file = distort_image(image_name)

                        if DEBUG:
                            print("distorted image: " + image_name)
                        # send distorted image
                        if DEBUG:
                            await ch.send("[Debug] Processed image: " + image_name, file=distorted_file)
                            return
                        await ch.send(file=distorted_file)
                        return
                    else:
                        if DEBUG:
                            await ch.send(embed=embed_wrongfile_error)
                        return
        else:
            return

bot.run(TOKEN)
