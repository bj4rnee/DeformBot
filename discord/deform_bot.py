#!/usr/bin/env python3
# Copyright (C) Bjarne - All Rights Reserved
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either Version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# A copy of the GNU General Public License Version 3 is distributed
# along with this program and can be found here
# <https://github.com/bj4rnee/DeformBot/blob/main/LICENSE>.
#
#                          ..:::^^^^^^^^^^^:::..
#                    ..::^^^^^^^^^^^^^^^^^^^^^^^^^::.
#                 .::^^^::::::::::::::::::::::^^^^^^^^^:.
#              .:::::::::::::::::::::::::::::^^^^^^^^^^^^^:
#            .:::::::::::::::::::::::::::^^^^^^^^^^^^^^^^^^^:.
#          .::::::::::^^^^:::::::::::::^~^:^~~!!!!!!!!~~^^^^^^:.
#        .::::::^^~~~~~~^^^~::::::::::!~.:!7777777!!!!7!!~^^^^^^:
#       ::::::^~!!7777777!^^!::::::::!~.^7777777777777!!!!!!^^^:^^.
#     .:::::^~!!77!!77777?7:~~::::::^7:.7?77777777~^^^!7!!!!!~:^::^:
#    .::::^^!!77~:.:!77????:~!::::::~7::???????77~.. .^^~!!!!!~:^::::
#   .::::^^!777!.  .~?????7:!~::::::^?^.7????????~..    :7!!!!!^:::::.
#   :::::^^77777~^~7??????^~!^^^^^^^^77.^?????????!^:..:~77!!!!~.^..::.
#  .:::::^:!7777????????7^~!^^^^^^^^^^?!.~?J????????77777777!!!~.^:..::
#  ::::::^^^!7????????7~~!~^^^^^^^^^^^~?!:^?JJJ????????777777!!::^....:.
# .:::::::^~^^~!77!!~~~!~^^^^^^^^^^^^^^^7?~:~7JJJ???????77777!^.~:.....:
# .:::::::::^~~~~~~~~~^^^^^^^^^^^^^^^^^^^~77~^^!7?????????7!^::~^......:
# .::::::::::::^^^^^^^^^^^^^^^^^^^^^^^^^^^^~!7!~^^^^~~~~^^::^~~::.......
# .::::::::::::::::^^^^^^^^^^^^^^~~~~~^^^^^^^^~~!!!!~~~~~~~~^:::::......
# .:::::::::::::::^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^:::::::::......
#  :::::::::::::::^^^^^^~!7777!~~!77777!~^^^^^^^^^^:::::::::::::::......
#  .::::::::::^::::^:^!??!~~~~7??7!~~!7??7~^^^^^^^:::::::::::::::......
#   :::::::::~77^::^!?7^.......:::::...:^7J?~^^^:~77~::::::::::::.....
#   .::::::::~7~!!!77^....................:!?7!!!?!?7:::::::::::......
#    .::::::::!~.:::........................:^~~^:^?~:::::::::::.....
#     .::::::::!!:. ...........~7^............  .^7!:::::::::::.....
#       ::::::::^!~^:.......:~7?7?7~:.........:^!!~:::::::::::.....
#        .::::::::^^~~!~!!!!7!~^:^~!7!!!!~~!!!!~^::::::::::::....
#          .:::::::::::^^^^::::::::::^^^^^^^^::::::::::::::....
#            .:::::::::::::::::::::::::::::::::::::::::::....
#              ..:::::::::::::::::::::::::::::::::::::::...
#                 ..:::::::::::::::::::::::::::::::::...
#                     ...:::::::::::::::::::::::....
#                          .....:::::::::......
#
#             Written by Bjarne <klar@bjarne.dev>, May 2022

import os
import sys
import random
import time
from urllib import request
import psutil
import requests
import uuid
import shutil
import asyncio
import traceback
import math
import gc
import tweepy
import logging
import json
import itertools
import atexit
from numpy import interp
from datetime import datetime, timedelta
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv, set_key
from io import BytesIO
from glob import glob
from PIL import Image
from pympler.tracker import SummaryTracker
from pympler import summary, muppy

VERSION = "1.5.4_dev"
# Turn off in production!
DEBUG = True

# load the env variables
load_dotenv()

# Turn on if you want to disable the bot on twitter
DISABLE_TWITTER = os.getenv('DISABLE_TWITTER')
DISABLE_TWITTER = DISABLE_TWITTER.lower(
) in ['true', 'True', '1', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh']

TOKEN = os.getenv('DISCORD_TOKEN')
CONSUMER_KEY = os.getenv('TWITTER_OAUTH_CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('TWITTER_OAUTH_CONSUMER_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
BEARER_TOKEN = os.getenv('BEARER_TOKEN_MANAGE')
USER_ID = os.getenv('DB_USER_ID')
since_id = int(os.getenv('last_id'))
num_processed = 0  # number of total processed images since last reboot
latest_followers = []
user_json = {}
tweet_json = []  # keep in mind this is a list and not a dict
blocked_json = []  # blacklist
# list of twitter users which cannot have overflowing tweets processed
blocked_from_of = []

# load info about twitter users interacting with bot
# this is a fix for feedback loops with e.g. other image bots
try:
    with open('user_interact.json') as f:
        user_json = json.load(f)
except Exception as e:
    print("[Error] Couldn't read 'user_interact.json': " + str(e))

# load overflowing tweet json list
try:
    with open('tweet_overflow.json') as f2:
        tweet_json = json.load(f2)
except Exception as e:
    print("[Error] Couldn't read 'tweet_overflow.json': " + str(e))

# load users which are blocked from using deformbot on twitter
try:
    with open('user_blocked.json') as f3:
        blocked_json = json.load(f3)
except Exception as e:
    print("[Error] Couldn't read 'user_blocked.json': " + str(e))

# load users which are blocked from having overflown tweets processed
try:
    with open('user_blocked_of.json') as f4:
        blocked_from_of = json.load(f4)
except Exception as e:
    print("[Error] Couldn't read 'user_blocked_of.json': " + str(e))


# the bot's command prefix for discord
COMMAND_PREFIX = ['§', '$']

MAX_ARGS = 16  # maximum number of arguments the bot accepts
OUTPUT_PATH = os.getenv("OUTPUT_PATH", os.path.join("/home", "db_outputs")) # fallback to /home/db_outputs
MAX_INTERACTIONS = 3
lock = asyncio.Lock()  # Doesn't require event loop
tracker = SummaryTracker()
process = psutil.Process(os.getpid())
start_time = datetime.now()
arg_error_flag = False
intents = discord.Intents.default()
intents.typing = True
intents.dm_typing = True
intents.message_content = True
intents.messages = True
intents.dm_messages = True
intents.reactions = True
intents.dm_reactions = True

# this is a hack to log print to a file but keep stdout
if os.getenv('ENABLE_LOGGING').lower() == 'true':
    log_path = os.path.join(OUTPUT_PATH, "db.log")
    if os.path.exists(OUTPUT_PATH):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                            handlers=[
                                logging.StreamHandler(),
                                logging.FileHandler(log_path, "a"),
                            ],)
    else:
        print("[Error] Couldn't find logfile. Creating a new one in current dir ...")
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                            handlers=[
                                logging.StreamHandler(),
                                logging.FileHandler("db.log", "a"),
                            ],)
    logger = logging.getLogger()
    logger.propagate = False
    print = logger.info

# UNFORTUNATELY THIS WORKS ONLY IN v1.1 API
# Authenticate to Twitter
auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True)  # twitter api object

bot = commands.Bot(command_prefix=COMMAND_PREFIX, help_command=None,
                   description="an Open Source image distortion discord bot", intents=intents)
client = discord.Client(intents=intents)  # deprecated
bot.mutex = True  # mutex lock

embed_nofile_error = discord.Embed(
    description="No attachments", color=0xFF5555)
embed_nofile_error.set_author(name="[Error]", url="https://bjarne.dev/",
                              icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/9e/Barrier_%28held%29_JE2_BE2.png/revision/latest?cb=20200224220440")

embed_wrongfile_error = discord.Embed(
    description="Can't process this filetype. Only `.jpg`, `.jpeg`, `.png` and `.gif` are supported at the moment", color=0xFF5555)
embed_wrongfile_error.set_author(name="[Error]", url="https://bjarne.dev/",
                                 icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/9e/Barrier_%28held%29_JE2_BE2.png/revision/latest?cb=20200224220440")

argument_error = discord.Embed(
    description="Invalid argument: " + ".\nFor argument usage refer to `§help` or `/help`", color=0xFF5555)
argument_error.set_author(name="[Error]", url="https://github.com/bj4rnee/DeformBot#command-arguments",
                          icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/9e/Barrier_%28held%29_JE2_BE2.png/revision/latest?cb=20200224220440")

embed_unsafeurl_error = discord.Embed(
    description="Unsafe url detected. Only images hosted on `cdn.discordapp.com` are supported at the moment", color=0xFF5555)
embed_wrongfile_error.set_author(name="[Error]", url="https://bjarne.dev/",
                                 icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/9e/Barrier_%28held%29_JE2_BE2.png/revision/latest?cb=20200224220440")


# Semaphore methods
async def wait():  # aquire the lock
    while bot.mutex == False:
        await asyncio.sleep(1)
        print('.', end='')
        pass
    bot.mutex = False
    return bot.mutex


async def signal():  # free the lock
    bot.mutex = True
    return bot.mutex


# testing with explicitly releasing resources before program exit
def exit_handler():
    if twitter_bot_loop.is_running():
        twitter_bot_loop.stop()
    if decr_interactions_loop.is_running():
        decr_interactions_loop.stop()


atexit.register(exit_handler)


# args: seam-carving, noise, blur, contrast, swirl, implode, distort (conventional), invert, disable compression, grayscale
#       l=60,         n=0,   b=0,  c=0,      s=0,   o=0      d=0                     i=False,u=False,             g=False
# defaults values if flag is not set or otherwise specified
# note that the default input for 'l' is 43 but it's interpolated to l=60
# TODO better blur!
def distort_image(fname, args, png: bool = False):
    """function to distort an image using the magick library"""
    global arg_error_flag  # True if invalid arg is detected
    global argument_error
    global num_processed
    invalid_args_list = []
    arg_count = 0
    anaglyph = False
    image = Image.open(os.path.join("raw", fname))
    imgdimens = image.width, image.height

    # convert image to 'RGB' (jpeg format). This fixes wrong encoding with discord
    if not png:
        image = image.convert('RGB')
        image.save(os.path.join("raw", fname), format='JPEG')
    image.close()

    # build the command string
    build_str = """ -background "#36393e" """  # this is the discord bg color
    l = 60  # lower this numer => more distortion

    if ("u" not in args):  # disable-compression flag
        # no '-colorspace RGB'
        build_str += " -define jpeg:dct-method=float -strip -interlace Plane -sampling-factor 4:2:0 -quality 80% "
    if any("l" in (v := value) for value in args):  # if l-flag is in args
        try:
            cast_int = int(v[1:4])
        except Exception as e:
            arg_error_flag = True
            cast_int = 43  # this will be interpolated to the deafult of l = 60
        if cast_int >= 1 and cast_int <= 100:
            l = round(interp(cast_int, [1, 100], [99, 8]))
            build_str += f" -liquid-rescale {l}x{l}%! -resize {imgdimens[0]}x{imgdimens[1]}\! "
        else:  # no seam-carivng
            l = 0
    else:  # l-flag is not in args -> fall back to default l
        build_str += f" -liquid-rescale {l}x{l}%! -resize {imgdimens[0]}x{imgdimens[1]}\! "

    for e in args:
        arg_count += 1  # why the fuck doesn't '++' exist in python
        if arg_count > MAX_ARGS:
            arg_error_flag = True
            invalid_args_list.append(e)
            argument_error.description = "Invalid argument(s): " + str(
                invalid_args_list) + ".\nFor argument usage refer to `§help` or `/help`"
            break
        # note: with heavy noise sc has to run before the image is noisified or it will fail!!
        # ! sc is now applied above !
        if e.startswith('l'):  # sc-factor-flag
            #     cast_int = int(e[1:4])
            #     if cast_int >= 1 and cast_int <= 100:
            #         l = round(interp(cast_int, [1, 100], [99, 8]))
            #         build_str += f" -liquid-rescale {l}x{l}%! -resize {imgdimens[0]}x{imgdimens[1]}\! "
            #     else:  # no seam-carivng
            #         l = 0
            continue
        if e.startswith('n'):  # noise-flag
            try:
                cast_int = int(e[1:4])
            except Exception as e:
                arg_error_flag = True
                continue
            if cast_int >= 1 and cast_int <= 100:
                if cast_int <= 25:
                    cast_float = round(
                        interp(cast_int, [1, 25], [0.1, 1.0]), 2)
                    build_str += f" +noise Gaussian -attenuate {cast_float} "
                    continue
                if cast_int <= 50:
                    cast_float = round(
                        interp(cast_int, [26, 50], [0.1, 1.0]), 2)
                    build_str += f" +noise Gaussian +noise Gaussian -attenuate {cast_float} "
                    continue
                if cast_int <= 75:
                    cast_float = round(
                        interp(cast_int, [51, 75], [0.1, 1.0]), 2)
                    build_str += f" +noise Gaussian +noise Gaussian +noise Gaussian -attenuate {cast_float} "
                    continue
                if cast_int <= 100:
                    cast_float = round(
                        interp(cast_int, [76, 100], [0.1, 1.0]), 2)
                    build_str += f" +noise Gaussian +noise Gaussian +noise Gaussian +noise Gaussian -attenuate {cast_float} "
            continue
        if e.startswith('b'):  # blur-flag
            try:
                cast_int = int(e[1:4])
            except Exception as e:
                arg_error_flag = True
                continue
            if cast_int >= 1 and cast_int <= 100:
                build_str += f" -blur 0x{cast_int} "
            continue
        if e.startswith('c'):  # contrast-flag
            try:
                cast_int = int(e[1:5])
            except Exception as e:
                arg_error_flag = True
                continue
            if cast_int >= -100 and cast_int <= 100:
                build_str += f" -brightness-contrast 0x{cast_int} "
            continue
        if e.startswith('s'):  # swirl-flag
            try:
                cast_int = int(e[1:5])
            except Exception as e:
                arg_error_flag = True
                continue
            if cast_int >= -360 and cast_int <= 360:
                build_str += f" -swirl {cast_int} "
            continue
        if e.startswith('o'):  # implode-flag
            try:
                cast_int = int(e[1:5])
            except Exception as e:
                arg_error_flag = True
                continue
            # explode
            if cast_int >= -100 and cast_int < 0:
                cast_float = round(
                    interp(cast_int, [-100, -1], [-1.15, -0.01]), 2)
                build_str += f" -implode {cast_float} "
                continue
            # implode
            else:
                if cast_int > 0 and cast_int <= 100:
                    cast_float = float(cast_int)/100
                    build_str += f" -implode {cast_float} "
            continue
        if e.startswith('w'):  # wave-flag
            try:
                cast_int = int(e[1:4])
            except Exception as e:
                arg_error_flag = True
                continue
            if cast_int >= 1 and cast_int <= 100:
                #cast_float = float(cast_int)/100
                # TODO fix image having spikes
                build_str += f" -wave {round(0.7*cast_int)}x{2*cast_int} "
            continue
        if e.startswith('d'):  # shepards-distortion-flag
            try:
                cast_int = int(e[1:4])
            except Exception as e:
                arg_error_flag = True
                continue
            if cast_int >= 1 and cast_int <= 100:
                # map float to meaningful power range
                cast_float = "{:.1f}".format(
                    interp(cast_int, [1, 100], [0.1, 12.0]))
                points = []
                x_th = round(0.15*imgdimens[0])  # threshholds
                y_th = round(0.15*imgdimens[1])
                # radius of circle taking up 20% of the area. r^2*π=0.2*x*y
                max_radius = (
                    math.sqrt(imgdimens[0]) * math.sqrt(imgdimens[1]))/(math.sqrt(5*math.pi))
                number_of_points = 3
                for i in range(number_of_points):  # generate 3 random points
                    points.append(tuple([random.randint(
                        x_th, imgdimens[0]-x_th), random.randint(y_th, imgdimens[1]-y_th)]))
                    # for every point, generate another random point in a short range
                    alpha = 2 * math.pi * random.random()  # random angle
                    # random radius within max_radius. Note: the distribution is not linear
                    sigma = interp(random.randint(1, 1000),
                                   [1, 1000], [0.25, 1])
                    r = max_radius * math.sqrt(sigma)
                    # calculating coordinates
                    x_coord = round(r * math.cos(alpha) + points[-1][0])
                    y_coord = round(r * math.sin(alpha) + points[-1][1])
                    points.append(tuple([x_coord, y_coord]))
                # params                                                anker points: (1,1)                  (x,1)                               (1,y)                                                (x,y)
                build_str += f" -define shepards:power={cast_float} -distort Shepards '1,1,1,1 {imgdimens[0]-1},1,{imgdimens[0]-1},1 1,{imgdimens[1]-1},1,{imgdimens[1]-1} {imgdimens[0]-1},{imgdimens[1]-1},{imgdimens[0]-1},{imgdimens[1]-1} "
                for j in range(number_of_points):
                    build_str += f"{points[-2][0]},{points.pop(-2)[1]},{points[-1][0]},{points.pop(-1)[1]} "
                build_str += "' "
            continue
        if e.startswith('r'):  # rotate-flag
            try:
                cast_int = int(e[1:5])
            except Exception as e:
                arg_error_flag = True
                continue
            if cast_int >= -360 and cast_int <= 360:
                build_str += f" -rotate {cast_int} "
            continue
        if e.startswith('f'):  # flip-flag
            try:
                cast_str = str(e[1:2])
            except Exception as e:
                build_str += f" -flip "
                continue
            if cast_str in ['', ' ', 'h', 'H']:
                build_str += f" -flip "
                continue
            else:
                build_str += f" -flop "
            continue
        if e.startswith('a'):  # stereo-flag (aka anaglyph)
            # -stereo doesnt really work in a single command, therefore anaglyph is always applied last. this is a bug.
            #build_str += f" -convert {fname} {fname} -composite -stereo +{random.randint(0, 25)}+{random.randint(1, 20)} "
            anaglyph = True
            continue
        if e.startswith('i'):  # invert-flag
            build_str += f" -channel RGB -negate "
            continue
        if e.startswith('u'):
            continue
        if e.startswith('g'):  # greyscale-flag
            build_str += f" -grayscale average "
            continue
        invalid_args_list.append(e)
        argument_error.description = "Invalid argument(s): " + \
            str(invalid_args_list) + \
            ".\nFor argument usage refer to `§help` or `/help`"
        arg_error_flag = True
        if DEBUG:
            print("[ERROR]: invalid argument '" + e + "'")

    # note: added compression in command
    distortcmd = f"magick " + \
        os.path.join(
            "raw", f"{fname}[0]") + build_str + os.path.join("results", f"{fname}")
    #print("[CMD] " + distortcmd)
    os.system(distortcmd)

    # TODO temporary fix for -composite not working with -stereo in magick7
    if anaglyph:
        # prev generated by: random.randint(0, 25) and random.randint(3, 20)
        stereo_offset = random.sample(range(0, 23), 2)
        stereocmd = f"magick composite " + os.path.join("results", f"{fname}") + " " + os.path.join(
            "results", f"{fname}") + f" -stereo +{stereo_offset[0]}+{stereo_offset[1]} " + os.path.join("results", f"{fname}")
        os.system(stereocmd)

    buf = BytesIO()
    buf.name = 'image.jpeg'

    # save file to /results/
    image = Image.open(f"results/{fname}")
    filetype = "JPEG" if fname.endswith(".jpg") else "PNG"
    image.save(buf, filetype)
    image.close()

    num_processed += 1

    # backup file to specified output path
    bkp_path = OUTPUT_PATH
    if os.path.exists(bkp_path):
        if DEBUG:
            print("[DEBUG] free backup space: " +
                  str(psutil.disk_usage(bkp_path).free) + "B")
        if psutil.disk_usage(bkp_path).free >= 536870912:  # around 500MiB
            try:
                bkp_name = fname
                # check if name collides (extremely unlikely but possible)
                while (os.path.exists(os.path.join(bkp_path, bkp_name))):
                    if DEBUG:
                        print("[ERROR] filename collision detected: " + bkp_name)
                    bkp_name = str(uuid.uuid4()) + '.jpg'  # generate new fname
                    if DEBUG:
                        print("[INFO] new non-colliding file name: " + bkp_name)
                try:
                    shutil.copy(f"results/{fname}",
                                os.path.join(bkp_path, bkp_name))
                    if DEBUG:
                        print(f"stored image: {bkp_name}")
                except OSError as oe:
                    print(
                        "[ERROR] probably ran out of inodes. Action must be taken!")
            except:
                traceback.print_exc()
        else:
            print(
                "[IOError] couldn't save the output file to db_outputs. Maybe check disk...?")
    buf.seek(0)
    buf.close
    return discord.File(os.path.join("results", f"{fname}"))


@bot.event
async def on_ready():
    if DEBUG:
        print("──────────────────────────────────────────────────────────────")
        print("starting DeformBot " + VERSION + " ...")
        print(f'{bot.user} has connected to Discord!')
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Game(name="§help | /help"))
    # sync interaction tree (used for applications like slash cmds)
    await bot.tree.sync()

    if not DISABLE_TWITTER:
        # verify api object
        try:
            api.verify_credentials()
            if DEBUG:
                print("[Twitter] Authentication Successful!")
        except Exception as e:
            raise e
        if not twitter_bot_loop.is_running():
            twitter_bot_loop.start()
        if not decr_interactions_loop.is_running():
            decr_interactions_loop.start()
        #print("[IMPORTANT] You shouldn't be seeing this message!")
    else:
        print("[Twitter] @DefomBot disabled.")
    if DEBUG:
        print("──────────────────────────────────────────────────────────────")
    # bot.remove_command('help')


@bot.hybrid_command(name="status", with_app_command=True, description="Shows status")
async def status(ctx):
    current_time = datetime.now()
    timestr = 'Uptime:\t{}\n'.format(current_time.replace(
        microsecond=0) - start_time.replace(microsecond=0))
    hours = math.ceil((current_time.replace(microsecond=0) -
                      start_time.replace(microsecond=0)).total_seconds() / 3600)
    memstr = 'Memory:\t' + \
        str(round(process.memory_info().rss / 1024 ** 2, 2)) + 'MB\n'
    response = "```[Debug]\n" + timestr + \
        memstr + "Vers..:\t" + VERSION + \
        "\nNumPrc:\t" + str(num_processed) + \
        " ({}/h)".format(round(num_processed / hours, 2)) + "```"
    await ctx.send(response)


@bot.command(name='trigger', help='Triggers testing function')
async def trigger(ctx):
    try:
        # test this function call / loc
        div_by_zero = 1/0
        pass
    except Exception as e:
        embed_stacktrace = discord.Embed(
            title=':x: An expetion occurred', color=0xFF5555, description="Traceback")
        #embed_stacktrace.add_field(name='Traceback', value="Traceback")
        dfile = discord.File("../misc/this_is_fine.png",
                             filename="this_is_fine.png")
        embed_stacktrace.set_image(url="attachment://this_is_fine.png")
        embed_stacktrace.description = traceback.format_exc()
        embed_stacktrace.timestamp = datetime.utcnow()
        await ctx.send(embed=embed_stacktrace, file=dfile)
    return


@bot.command(name='memtrace', help='Outputs last memorytrace', aliases=['t', 'trace'])
async def memtrace(ctx):
    # tracker.print_diff() # this termporarly solves schroedingers memory leak??
    all_objects = muppy.get_objects(include_frames=True)
    sum1 = summary.summarize(all_objects)
    summary.print_(sum1)
    embed_crash = discord.Embed(title=':x: Event Error', color=0xFF5555)
    #embed_crash.add_field(name='Event', value=event)
    #embed_crash.description = '```py\n%s\n```' % traceback.format_exc()
    embed_crash.description = "```diff\n- collecting traces...```"
    embed_crash.timestamp = datetime.utcnow()
    await ctx.send(embed=embed_crash)


@bot.command(name='garbage', help='triggers garbage collector', aliases=['g', 'gc'])
async def garbage(ctx):
    collected = gc.collect()  # manually collect garbage
    print("[Debug] garbage collected: " + str(collected) + " objects")
    embed_crash = discord.Embed(
        title=':white_check_mark: Garbage collected.', color=0x55FF55)
    embed_crash.description = f"```diff\n+ {collected} objects purged```"
    embed_crash.timestamp = datetime.utcnow()
    await ctx.send(embed=embed_crash)


@bot.command(name='ai', help='generate image with AI', aliases=['deformai'])
async def ai(ctx):
    return


@bot.hybrid_command(name='help', with_app_command=True, help='Shows usage info', description='Shows usage info', aliases=['h', 'info', 'usage'])
async def help(ctx):
    rand_color = random.randint(0, 0xFFFFFF)
    helpstr_args = "\n\n**Arguments:**\n`l`:  Seam-Carving factor\n`s`:  swirl (degrees)\n`n`:  noise\n`b`:  blur\n`c`:  contrast (allows negative values)\n`o`:  implode\n`d`:  shepard's distortion\n`i`:  invert colors\n`g`:  grayscale image\n`u`:  disable compression\nAll arguments can be arbitrarily combined or left out.\nOnly integer values are accepted, I advise to play around with those values to find something that looks good."
    helpstr_usage = "\n\n**Usage:**\n`§deform [option0][value] [option1][value] ...`\nExamples:\n _§deform s35 n95 l45 c+40 b1_\n_§deform l50 s25 c+30 n70 g_"
    help_embed = discord.Embed(
        description="[Website](https://bjarne.dev)\n[Github](https://github.com/bj4rnee/DeformBot)\n[Twitter](https://twitter.com/DeformBot)\n\n**Commands:**\n`help`:  Shows this help message\n`deform`:  Distort an attached image\nYou can also react to an image with `🤖` to quickly deform it." + helpstr_args + helpstr_usage, color=rand_color)
    help_embed.set_author(name="Hi, I'm an Open Source image distortion discord bot!", url="https://bjarne.dev/",
                          icon_url="https://cdn.discordapp.com/avatars/971742838024978463/4e6548403fb46347b84de17fe31a45b9.webp")
    await ctx.send(embed=help_embed)


# standard non-slash command
@bot.command(name='deform', help='deform an image', aliases=['d', 'D' 'distort'])
async def deform(ctx, *args):
    global arg_error_flag
    async with lock:
        msg = ctx.message  # msg with command in it
        reply_msg = None  # original msg which was replied to with command
        ch = msg.channel
        url = ""
        async with ch.typing():
            # set error flag to false
            arg_error_flag = False
            # first delete the existing files
            for delf in os.listdir("raw"):
                if delf.endswith(".jpg"):
                    os.remove(os.path.join("raw", delf))

            for delf2 in os.listdir("results"):
                if delf2.endswith(".jpg"):
                    os.remove(os.path.join("results", delf2))

            if msg.reference != None:  # if msg is a reply
                reply_msg = await ctx.channel.fetch_message(msg.reference.message_id)
                msg = reply_msg

            try:
                if len(msg.embeds) <= 0:  # no embeds
                    url = msg.attachments[0].url
                else:
                    url = msg.embeds[0].image.url
                    if isinstance(url, str) == False:
                        await ctx.send(embed=embed_nofile_error)
                        return
            except (IndexError, TypeError):
                # older_msgs = await ch.history(limit=10).flatten() # deprecated
                # discord.py v2 method of handling this is list comprehension
                older_msgs = [m async for m in ch.history(limit=10)]
                # check if an older msg contains image
                for omsg in older_msgs:
                    try:
                        if len(omsg.embeds) <= 0:  # no embeds
                            url = omsg.attachments[0].url
                            break
                        else:
                            url = omsg.embeds[0].image.url
                            # this might be a problem: if the first embed db sees has a faulty url, it returns error
                            if isinstance(url, str) == False:
                                # await ctx.send(embed=embed_nofile_error)
                                # return
                                raise TypeError(
                                    "Embed didn't contain valid image link")
                            break
                    except (IndexError, TypeError):
                        if omsg == older_msgs[-1]:
                            await ctx.send(embed=embed_nofile_error)
                            return
                        else:
                            continue
                # we land here on success

            if url[0:26] == "https://cdn.discordapp.com":
                test_url = url.split('?')[0] # fix for discords new url params (again!!)
                if test_url[-4:].casefold() == ".jpg".casefold() or test_url[-4:].casefold() == ".png".casefold() or test_url[-5:].casefold() == ".jpeg".casefold() or test_url[-4:].casefold() == ".gif".casefold():
                    r = requests.get(url, stream=True)
                    image_name = str(uuid.uuid4()) + '.jpg'  # generate uuid

                    with open(os.path.join("raw", image_name), 'wb') as out_file:
                        if DEBUG:
                            print("───────────" + image_name + "───────────")
                            print("saving image: " + image_name)
                        shutil.copyfileobj(r.raw, out_file)
                        # flush the buffer, this fixes ReadException
                        out_file.flush()

                        # distort the file
                        distorted_file = distort_image(image_name, args)

                        if arg_error_flag:
                            await ctx.send(embed=argument_error)

                        if DEBUG:
                            print("distorted image: " + image_name)
                            print(
                                "──────────────────────────────────────────────────────────────")
                        # send distorted image
                        if DEBUG:
                            await ctx.send("image ID: " + image_name.replace(".jpg", "") + "\nargs=" + str(args), file=distorted_file)
                            return
                        await ctx.send(file=distorted_file)
                        return
                else:
                    await ctx.send(embed=embed_wrongfile_error)
                    return
            else:
                # handle non-discord url
                await ctx.send(embed=embed_unsafeurl_error)
                return


# slash command deform
@bot.tree.command(name="deform", description="Deform an image with optional parameters. For usage refer to /help")
# @app_commands.describe(args='for argument usage refer to /help')
@app_commands.describe(file='Attach an image to deform',
                       message_id='ID of a message containing an image',
                       l='Seam carving factor',
                       s='Swirl',
                       b='Blur',
                       n='Noise',
                       c='Contrast',
                       o='Implode',
                       d="Shepard's distortion (IWD)",
                       w='Wave',
                       r='Rotate (clockwise)',
                       f='Flip (horizontal, vertical)',
                       a='Anaglyph (cyan-red 3D)',
                       i='Invert colors',
                       g='Grayscale colors',
                       u='Disable compression',
                       )
@app_commands.choices(f=[discord.app_commands.Choice(name='horizontal', value='fh'), discord.app_commands.Choice(name='vertical', value='fv')])
async def deform_slash(interaction: discord.Interaction, file: discord.Attachment = None, message_id: str = None, l: int = None, s: int = None, b: int = None, n: int = None, c: int = None, o: int = None, d: int = None, w: int = None, r: int = None,
                       f: discord.app_commands.Choice[str] = None, a: bool = False, i: bool = False, g: bool = False, u: bool = False):
    args_dict = locals()  # this has to be the fist call in the function
    args_dict.pop('interaction', None)  # remove interaction object
    args = []
    for a in args_dict:
        if args_dict[a]:
            if isinstance(args_dict[a], discord.app_commands.Choice):
                args.append(str(args_dict[a].value))
            else:
                args.append(str(a) + str(args_dict[a]))

    # remove 'True' string literal from boolean arguments
    args = [x.replace('True', '') for x in args]
    args = tuple(args)

    # Optional[Union[abc.GuildChannel, PartialMessageable, Thread]]
    ch = interaction.channel

    try:
        # interactions aren't handled via a message. Therefore msg is a message ID integer.
        msg = int(message_id)
    except (ValueError, TypeError):
        msg = None
    if (not file) and msg:
        msg = await ch.fetch_message(msg)

    global arg_error_flag
    async with lock:
        reply_msg = None  # there cannot be a reply_msg with slash commads at the moment
        url = ""
        async with ch.typing():
            arg_error_flag = False
            # first delete the existing files
            for delf in os.listdir("raw"):
                if delf.endswith(".jpg"):
                    os.remove(os.path.join("raw", delf))

            for delf2 in os.listdir("results"):
                if delf2.endswith(".jpg"):
                    os.remove(os.path.join("results", delf2))

            try:
                if file:  # file is passed to call
                    url = file.url
                elif msg:  # msgID is passed to call and is valid int -> msg object available
                    # check for embeds first
                    if len(msg.embeds) <= 0:  # no embeds
                        url = msg.attachments[0].url
                    else:
                        url = msg.embeds[0].image.url
                        if isinstance(url, str) == False:
                            await interaction.response.send_message(embed=embed_nofile_error)
                            return
                else:
                    raise IndexError("No file or msgID given")
            except (IndexError, TypeError):
                # older_msgs = await ch.history(limit=10).flatten() # deprecated
                # discord.py v2 method of handling this is list comprehension
                older_msgs = [m async for m in ch.history(limit=10)]
                # check if an older msg contains image
                for omsg in older_msgs:
                    try:
                        if len(omsg.embeds) <= 0:  # no embeds
                            url = omsg.attachments[0].url
                            break
                        else:
                            url = omsg.embeds[0].image.url
                            if isinstance(url, str) == False:
                                # await ctx.send(embed=embed_nofile_error)
                                # return
                                raise TypeError(
                                    "Embed didn't contain valid image link")
                            break
                    except (IndexError, TypeError):
                        if omsg == older_msgs[-1]:
                            await interaction.response.send_message(embed=embed_nofile_error)
                            return
                        else:
                            continue
                # we land here on success

            if url[0:26] == "https://cdn.discordapp.com":
                test_url = url.split('?')[0]
                if test_url[-4:].casefold() == ".jpg".casefold() or test_url[-4:].casefold() == ".png".casefold() or test_url[-5:].casefold() == ".jpeg".casefold() or test_url[-4:].casefold() == ".gif".casefold():
                    r = requests.get(url, stream=True)
                    image_name = str(uuid.uuid4()) + '.jpg'  # generate uuid

                    with open(os.path.join("raw", image_name), 'wb') as out_file:
                        if DEBUG:
                            print("───────────" + image_name + "───────────")
                            print("saving image: " + image_name)
                        shutil.copyfileobj(r.raw, out_file)
                        # flush the buffer, this fixes ReadException
                        out_file.flush()

                        await interaction.response.defer()
                        # distort the file
                        distorted_file = distort_image(image_name, args)

                        if arg_error_flag:
                            pass
                            # we can't handle arg errors on interactions atm
                            # this should not be needed anyways
                            # await interaction.response.send_message(embed=argument_error)

                        if DEBUG:
                            print("distorted image: " + image_name)
                            print(
                                "──────────────────────────────────────────────────────────────")
                        # send distorted image
                        if DEBUG:
                            await interaction.followup.send("image ID: " + image_name.replace(".jpg", ""), file=distorted_file)
                            return
                        await interaction.followup.send(file=distorted_file)
                        return
                else:
                    await interaction.response.send_message(embed=embed_wrongfile_error)
                    return
            else:
                # handle non-discord url
                await interaction.response.send_message(embed=embed_unsafeurl_error)
                return


# deform via context menu
@bot.tree.context_menu(name="Deform")
async def deform_cm(interaction: discord.Interaction, message: discord.Message):
    async with lock:
        msg = message
        ch = msg.channel

        async with ch.typing():  # trigger typing indicator
            # first delete the existing files
            for delf in os.listdir("raw"):
                if delf.endswith(".jpg"):
                    os.remove(os.path.join("raw", delf))

            for delf2 in os.listdir("results"):
                if delf2.endswith(".jpg"):
                    os.remove(os.path.join("results", delf2))

            # fetch and process the image
            try:
                if len(msg.embeds) <= 0:  # no embeds
                    url = msg.attachments[0].url
                else:
                    url = msg.embeds[0].image.url
                    if isinstance(url, str) == False:
                        await interaction.response.send_message(embed=embed_nofile_error)
                        return
            except (IndexError, TypeError):
                if DEBUG:  # don't send errors on reaction
                    await interaction.response.send_message(embed=embed_nofile_error)
                return
            else:
                if url[0:26] == "https://cdn.discordapp.com":
                    test_url = url.split('?')[0]
                    if test_url[-4:].casefold() == ".jpg".casefold() or test_url[-4:].casefold() == ".png".casefold() or test_url[-5:].casefold() == ".jpeg".casefold() or test_url[-4:].casefold() == ".gif".casefold():
                        r = requests.get(url, stream=True)
                        image_name = str(uuid.uuid4()) + \
                            '.jpg'  # generate uuid

                        with open(os.path.join("raw", image_name), 'wb') as out_file:
                            if DEBUG:
                                print("───────────" +
                                      image_name + "───────────")
                                print("saving image: " + image_name)
                            shutil.copyfileobj(r.raw, out_file)
                            out_file.flush()

                            # unfortunately await can't be used here so the response has to be deferred
                            await interaction.response.defer()
                            distorted_file = distort_image(image_name, ())

                            if DEBUG:
                                print("distorted image: " + image_name)
                                print(
                                    "──────────────────────────────────────────────────────────────")
                            # send distorted image
                            if DEBUG:
                                await interaction.followup.send("image ID: " + image_name.replace(".jpg", ""), file=distorted_file)
                                return
                            await interaction.followup.send(file=distorted_file)
                            return
                    else:
                        if DEBUG:
                            await interaction.response.send_message(embed=embed_wrongfile_error)
                        return
                else:
                    await interaction.response.send_message(embed=embed_unsafeurl_error)
                    return


@bot.event
async def on_reaction_add(reaction, user):  # if reaction is on a cached message
    if user != bot.user:
        if str(reaction.emoji) == "🤖":
            async with lock:
                msg = reaction.message
                ch = msg.channel

                async with ch.typing():  # trigger typing indicator
                    # first delete the existing files
                    for delf in os.listdir("raw"):
                        if delf.endswith(".jpg"):
                            os.remove(os.path.join("raw", delf))

                    for delf2 in os.listdir("results"):
                        if delf2.endswith(".jpg"):
                            os.remove(os.path.join("results", delf2))

                    # fetch and process the image
                    try:
                        if len(msg.embeds) <= 0:  # no embeds
                            url = msg.attachments[0].url
                        else:
                            url = msg.embeds[0].image.url
                            if isinstance(url, str) == False:
                                await ch.send(embed=embed_nofile_error)
                                return
                    except (IndexError, TypeError):
                        if DEBUG:  # don't send errors on reaction
                            await ch.send(embed=embed_nofile_error)
                        return
                    else:
                        if url[0:26] == "https://cdn.discordapp.com":
                            test_url = url.split('?')[0]
                            if test_url[-4:].casefold() == ".jpg".casefold() or test_url[-4:].casefold() == ".png".casefold() or test_url[-5:].casefold() == ".jpeg".casefold() or test_url[-4:].casefold() == ".gif".casefold():
                                r = requests.get(url, stream=True)
                                image_name = str(uuid.uuid4()) + \
                                    '.jpg'  # generate uuid

                                with open(os.path.join("raw", image_name), 'wb') as out_file:
                                    if DEBUG:
                                        print("───────────" +
                                              image_name + "───────────")
                                        print("saving image: " + image_name)
                                    shutil.copyfileobj(r.raw, out_file)
                                    out_file.flush()

                                    # unfortunately await can't be used here
                                    distorted_file = distort_image(
                                        image_name, ())

                                    if DEBUG:
                                        print("distorted image: " + image_name)
                                        print(
                                            "──────────────────────────────────────────────────────────────")
                                    # send distorted image
                                    if DEBUG:
                                        await ch.send("image ID: " + image_name.replace(".jpg", ""), file=distorted_file)
                                        return
                                    await ch.send(file=distorted_file)
                                    return
                            else:
                                if DEBUG:
                                    await ch.send(embed=embed_wrongfile_error)
                                return
                        else:
                            await ch.send(embed=embed_unsafeurl_error)
                            return
        else:
            return


async def check_mentions(api, s_id):
    """checks and processes mentions in v1.1 api"""
    global arg_error_flag
    global user_json

    # Retrieving mentions
    new_since_id = s_id
    twitter_media_url = [] # list of tweet media url(s)
    mentions = []

    try:
        for twObj in tweepy.Cursor(api.mentions_timeline, since_id=new_since_id, count=100, tweet_mode='extended').items():
            mentions.append(twObj)

        for twJson in itertools.islice(tweet_json, 10):
            try:
                t = api.get_status(twJson, tweet_mode='extended')
                if t.user.screen_name.casefold() in blocked_from_of:
                    tweet_json.remove(twJson)
                    continue
                else:
                    mentions.append(t)
            except (tweepy.TweepyException, tweepy.HTTPException) as e:
                print("[Error] TweepyException: " +
                      str(e) + ". StatusID: " + str(twJson))
                tweet_json.remove(twJson)

        for tweet in mentions:
            new_since_id = max(tweet.id, new_since_id)
            #os.environ['last_id'] = str(new_since_id)
            # only works when process is terminated
            set_key(".env", 'last_id', str(new_since_id))

            # check if user is blacklisted
            if tweet.user.id in blocked_json:
                continue

            # increment number of interactions from this user
            if tweet.id not in tweet_json:  # only increment when tweet isn't overflowing
                user_json[tweet.user.screen_name] = (min(int(
                    user_json[tweet.user.screen_name])+1, MAX_INTERACTIONS*2)) if (tweet.user.screen_name in user_json) else 1

            if hasattr(tweet, 'text'):
                tweet_txt = tweet.text.lower()
            else:
                tweet_txt = tweet.full_text.lower()
            if hasattr(tweet, 'possibly_sensitive'):
                sensitive = tweet.possibly_sensitive
            else:
                sensitive = False

            # convert tweet text to ascii: !!warning: §,ß(ss) are removed too
            tweet_txt = tweet_txt.encode("ascii", errors="ignore").decode()
            # remove \n from string for better debug output
            tweet_txt = tweet_txt.replace("\n", "")

            # if user sent too many requests in the past minutes, db ignores
            try:
                if int(user_json[tweet.user.screen_name]) >= MAX_INTERACTIONS:
                    # add tweet to overflow dict
                    if tweet.id not in tweet_json:
                        tweet_json.append(tweet.id)
                        if DEBUG:
                            print("[ERROR] overflowing tweet from " + tweet.user.screen_name +
                                  ": '" + tweet_txt + "', status_id: " + str(tweet.id))
                    continue
                else:  # request will be processed -> if tweet.id is in queued requests it can be removed
                    if tweet.id in tweet_json:
                        tweet_json.remove(tweet.id)
                        # now we must incr user_json otherwise overflowing tweets could spam the api
                        user_json[tweet.user.screen_name] = (int(
                            user_json[tweet.user.screen_name])+1) if (tweet.user.screen_name in user_json) else 1
            except KeyError as ke:
                # somehow this can be buggy and users are not written to user_json => investigate futher
                user_json[tweet.user.screen_name] = 1
                print("[ERROR] keyerror occured: " + str(ke))
                continue

            # original status (if 'tweet' is a reply)
            reply_og_id = tweet.in_reply_to_status_id
            if DEBUG:
                print("[DEBUG] tweet from " + tweet.user.screen_name + ": '" + tweet_txt +
                      "', sensitive: " + str(sensitive) + ", reply: " + str(reply_og_id))

            if hasattr(tweet, 'extended_entities'):
                tw_entities = tweet.extended_entities
            else:
                tw_entities = tweet.entities
            if 'media' in tw_entities:  # tweet that mentionions db contains image
                raw_images_links = [d['media_url'] for d in tw_entities.get('media', [])]
                if (len(raw_images_links) > 0):
                    twitter_media_url = raw_images_links
                else:
                    twitter_media_url = ["[ERROR] No URL found",]
            else:  # tweet that the mentioner replies to contains image
                if isinstance(reply_og_id, str) or isinstance(reply_og_id, int):
                    r_tweet = api.get_status(
                        reply_og_id, tweet_mode='extended')
                    if hasattr(r_tweet, 'extended_entities'):
                        r_tw_entities = r_tweet.extended_entities
                    else:
                        r_tw_entities = r_tweet.entities
                    if hasattr(r_tweet, 'possibly_sensitive'):
                        sensitive = (r_tweet.possibly_sensitive or sensitive)
                    if 'media' in r_tw_entities:  # TODO sometimes this isn't true even if media is shown in tweet -> attempted fix but not tested
                        raw_images_links = [d['media_url'] for d in r_tw_entities.get('media', [])]
                        if (len(raw_images_links) > 0):
                            twitter_media_url = raw_images_links
                        else:
                            twitter_media_url = ["[ERROR] No URL found",]
                    else:  # TODO fix bot responding with error to tweets not trying to send a command -> attempted fix but not tested
                        # dont reply with error to our own tweets
                        if not (r_tweet.in_reply_to_user_id_str == "DeformBot"):
                            api.update_status(status="[ERROR] no media found.", in_reply_to_status_id=tweet.id,
                                              auto_populate_reply_metadata=True, possibly_sensitive=sensitive)
                        continue
                else:
                    api.update_status(status="[ERROR] no media found.", in_reply_to_status_id=tweet.id,
                                      auto_populate_reply_metadata=True, possibly_sensitive=sensitive)
                    continue

            async with lock:  # from here proceed with lock!
                # clear arg error flag
                arg_error_flag = False

                # declare image_name to avoid UnboundLocalError
                image_name = "image_id_error"

                result_image_ids = []
                # first delete the existing files
                for delf in os.listdir("raw"):
                    if delf.endswith(".jpg"):
                        os.remove(os.path.join("raw", delf))
                for delf2 in os.listdir("results"):
                    if delf2.endswith(".jpg"):
                        os.remove(os.path.join("results", delf2))

                # fetch and process the image(s)
                for m_url in twitter_media_url:
                    if m_url[0:26] == "http://pbs.twimg.com/media":
                        m_url = m_url.split('?')[0]
                        if m_url[-4:].casefold() == ".jpg".casefold() or m_url[-4:].casefold() == ".png".casefold() or m_url[-5:].casefold() == ".jpeg".casefold() or m_url[-4:].casefold() == ".gif".casefold():
                            r = requests.get(m_url, stream=True)
                            image_name = str(uuid.uuid4()) + \
                                '.jpg'  # generate uuid

                            with open(os.path.join("raw", image_name), 'wb') as out_file:
                                if DEBUG:
                                    print("───────────" +
                                        image_name + "───────────")
                                    print("saving image: " + image_name)
                                shutil.copyfileobj(r.raw, out_file)
                                out_file.flush()
                                # remove mention and links from args. Alternatively '/' can be used instead of '.'
                                args = tuple(
                                    [x for x in tweet_txt.split() if all(y not in x for y in '@.')])
                                # distort the file
                                distort_image(image_name, args)

                                if arg_error_flag:
                                    arg_error_flag = False
                                    # we're not sending massive amounts of error msgs to twitter
                                    print("[Twitter] argument error flag was true")

                                if DEBUG:
                                    print("distorted image: " + image_name)
                                    print(
                                        "──────────────────────────────────────────────────────────────")
                                # send distorted image
                                # TODO 5MB FILESIZE LIMIT!!!!!!!!!!!!!
                                result_img = api.media_upload(os.path.join("results", image_name))
                                result_image_ids.append(result_img.media_id)
                        else:
                            api.update_status(status="[ERROR] Can't process this filetype. Only '.jpg', '.jpeg', '.png' and '.gif' are supported at the moment.",
                                            in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True, possibly_sensitive=sensitive)
                            continue
                    else:
                        # unsafe url
                        api.update_status(status="[ERROR] Unsafe url detected. Only images hosted on Twitter are supported at the moment.",
                                        in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True, possibly_sensitive=sensitive)
                        continue
                if DEBUG:
                    api.update_status(status="image ID: " + image_name.replace(".jpg", "") + "\n#TwitterBot", in_reply_to_status_id=tweet.id,
                                        auto_populate_reply_metadata=True, possibly_sensitive=sensitive, media_ids=result_image_ids)
                    continue
                api.update_status(status="#TwitterBot", in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True,
                                    possibly_sensitive=sensitive, media_ids=result_image_ids)
                continue
                    
    except (tweepy.TweepyException, tweepy.HTTPException) as e:
        print("[Error] TweepyException in check_mentions: " + str(e))

#api.update_status('@' + tweet.user.screen_name + " Here you go:", tweet.id, media_ids=[result_img.media_id])

    return new_since_id


async def check_followers(api, follower_list):
    """checks and processes followers in v1.1 api

    Important
    ------
        this function is heavily rate-limited and can only be called once a minute!
    """
    try:
        followers = api.get_followers(
            user_id=int(USER_ID), count=5, skip_status=True)
        if followers == follower_list:
            return followers  # if latest followers didnt change, we can return
        avatars = []
        async with lock:
            for follower in followers:
                avatar_url = follower.profile_image_url_https.replace(
                    "_normal.jpg", ".jpg")  # "_bigger.jpg")
                r = requests.get(avatar_url, stream=True)
                image_name = str(follower.id) + '.jpg'

                with open(os.path.join("raw", image_name), 'wb') as out_file:
                    shutil.copyfileobj(r.raw, out_file)
                    out_file.flush()
                avatars.append(image_name)

            # construct banner image
            banner = Image.open("../misc/DeformBot_banner.png", 'r')
            bn_w, bn_h = banner.size
            offset = (470, 350)  # (513, 375)

            for avatar in avatars:
                img = Image.open(os.path.join("raw", avatar), 'r')
                # adjust size
                img = img.resize((100, 100), Image.Resampling.LANCZOS)
                banner.paste(img, offset)
                img.close()
                offset = (offset[0]+115, offset[1])

            banner.save(os.path.join("results", "banner.jpg"), "JPEG")
            banner.close()
            api.update_profile_banner(os.path.join("results", "banner.jpg"))
    except (tweepy.TweepyException, tweepy.HTTPException) as e:
        print("[Error] TweepyException in check_followers: " + str(e))
        return follower_list
    return followers


# THIS IS THE LOOP FOR THE TWITTER BOT
@tasks.loop(seconds=75)
async def twitter_bot_loop():
    global since_id
    global latest_followers
    global user_json

    # execute this every 75 seconds
    try:
        since_id = await check_mentions(api, since_id)
    # random Runtime and NameErrors can occur in these async functions that cannot be handled otherwise atm
    # RtE's occur due to currently unknown reasons in asyncio locking
    # NE's occur when asyncio tries to log after 'open' has been deleted by gc before fileHandler could use it
    # this is fixed in 3.10 but the bot currently runs on 3.8 as of 11.2022
    # for more info see https://stackoverflow.com/questions/64679139/
    except (RuntimeError, NameError) as e:
        # don't change since_id
        print("[Error] Exception in 'check_mentions' in integral background task 'twitter_bot_loop': " + str(e))

    try:
        latest_followers = await check_followers(api, latest_followers)
    except (RuntimeError, NameError) as e:
        print("[Error] Exception in 'check_followers' in integral background task 'twitter_bot_loop': " + str(e))

    # then dump updated user json to file
    try:
        with open('user_interact.json', 'w') as f:
            json.dump(user_json, f)
    except Exception as e:
        print("[Error] Couldn't write 'user_interact.json': " + str(e))

    # and dump overflowing tweets to another file
    try:
        with open('tweet_overflow.json', 'w') as f2:
            json.dump(tweet_json, f2)
    except Exception as e:
        print("[Error] Couldn't write 'tweet_overflow.json': " + str(e))


@tasks.loop(seconds=360)
async def decr_interactions_loop():
    global user_json
    to_remove = []
    for u in user_json:
        user_json[u] = (int(user_json[u])-1) if (int(user_json[u]) > 0) else 0
        # remove user from dict if he has no more activity
    #     if int(user_json[u]==0):
    #         #to_remove.append(u)
    #         pass
    # for tr in to_remove:
    #     pass
    #     #user_json.pop(tr, None)

bot.run(TOKEN)
