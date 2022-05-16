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
import traceback
import math
import gc
import tweepy
from numpy import interp
from argparse import ArgumentParser
from datetime import datetime, timedelta
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv, set_key
from io import BytesIO
from glob import glob
from PIL import Image
from pympler.tracker import SummaryTracker
from pympler import summary, muppy

VERSION = "1.3_dev"
# Turn off in production!
DEBUG = True

# load the env variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CONSUMER_KEY = os.getenv('TWITTER_OAUTH_CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('TWITTER_OAUTH_CONSUMER_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
BEARER_TOKEN = os.getenv('BEARER_TOKEN_MANAGE')
USER_ID = os.getenv('DB_USER_ID')
since_id = int(os.getenv('last_id'))

#the bot's command prefix for discord
COMMAND_PREFIX = '§'

lock = asyncio.Lock()  # Doesn't require event loop
tracker = SummaryTracker()
process = psutil.Process(os.getpid())
start_time = datetime.now()
arg_error_flag = False


# UNFORTUNATELY THIS WORKS ONLY IN v1.1 API
# Authenticate to Twitter
auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True) # twitter api object

bot = commands.Bot(command_prefix=COMMAND_PREFIX, help_command=None,
                   description="an Open Source image distortion discord bot")
client = discord.Client()
bot.mutex = True  # mutex lock

embed_nofile_error = discord.Embed(
    description="No attachments", color=0xFF5555)
embed_nofile_error.set_author(name="[Error]", url="https://bjarne.dev/",
                              icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/9e/Barrier_%28held%29_JE2_BE2.png/revision/latest?cb=20200224220440")

embed_wrongfile_error = discord.Embed(
    description="Can't process this filetype. Only `.jpg`, `.jpeg` and `.png` are supported at the moment", color=0xFF5555)
embed_wrongfile_error.set_author(name="[Error]", url="https://bjarne.dev/",
                                 icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/9e/Barrier_%28held%29_JE2_BE2.png/revision/latest?cb=20200224220440")

argument_error = discord.Embed(
    description="Invalid argument: " + ".\nFor argument usage refer to `§help`", color=0xFF5555)
argument_error.set_author(name="[Error]", url="https://github.com/bj4rnee/DeformBot#command-arguments",
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


def fetch_image(message):
    return


# args: seam-carving, noise, blur, contrast, swirl, implode, distort (conventional), invert, disable compression, grayscale
#       l=60,         n=0,   b=0,  c=0,      s=0,   o=0      d=0                     i=False,u=False,             g=False
# defaults values if flag is not set or otherwise specified
# TODO better noise! -anagraph, wave
def distort_image(fname, args):
    """function to distort an image using the magick library"""
    global arg_error_flag
    global argument_error
    invalid_args_list = []
    image = Image.open(os.path.join("raw", fname))
    imgdimens = image.width, image.height

    # build the command string
    build_str = " -background '#36393f' "
    l = 60

    if ("u" not in args):  # disable-compression flag
        # no '-colorspace RGB'
        build_str += " -define jpeg:dct-method=float -strip -interlace Plane -sampling-factor 4:2:0 -quality 80% "
    if not any("l" in value for value in args):  # if l-flag is not in args
        build_str += f" -liquid-rescale {l}x{l}%! -resize {imgdimens[0]}x{imgdimens[1]}\! "

    for e in args:
        if e.startswith('l'):  # sc-factor-flag
            cast_int = int(e[1:3])
            if cast_int >= 1 and cast_int <= 100:
                l = cast_int
                build_str += f" -liquid-rescale {l}x{l}%! -resize {imgdimens[0]}x{imgdimens[1]}\! "
            else:  # no seam-carivng
                l = 0
            continue
        if e.startswith('n'):  # noise-flag
            cast_int = int(e[1:4])
            if cast_int >= 1 and cast_int <= 100:
                cast_float = float(cast_int)/100
                build_str += f" +noise Gaussian -attenuate {cast_float} "
            continue
        if e.startswith('b'):  # blur-flag
            cast_int = int(e[1:4])
            if cast_int >= 1 and cast_int <= 100:
                build_str += f" -blur 0x{cast_int} "
            continue
        if e.startswith('c'):  # contrast-flag
            cast_int = int(e[1:5])
            if cast_int >= -100 and cast_int <= 100:
                build_str += f" -brightness-contrast 0x{cast_int} "
            continue
        if e.startswith('s'):  # swirl-flag
            cast_int = int(e[1:5])
            if cast_int >= -360 and cast_int <= 360:
                build_str += f" -swirl {cast_int} "
            continue
        if e.startswith('o'):  # implode-flag
            cast_int = int(e[1:4])
            if cast_int >= 1 and cast_int <= 100:
                cast_float = float(cast_int)/100
                build_str += f" -implode {cast_float} "
            continue
        if e.startswith('d'):  # shepards-distortion-flag
            cast_int = int(e[1:4])
            if cast_int >= 1 and cast_int <= 100:
                # map float to meaningful power range
                cast_float = "{:.1f}".format(
                    interp(cast_int, [1, 100], [0.1, 12.0]))
                points = []
                x_th = round(0.15*imgdimens[0]) # threshholds
                y_th = round(0.15*imgdimens[1])
                # radius of circle taking up 20% of the area. r^2*π=0.2*x*y
                max_radius = (math.sqrt(imgdimens[0]) * math.sqrt(imgdimens[1]))/(math.sqrt(5*math.pi))
                number_of_points = 3
                for i in range(number_of_points):  # generate 3 random points
                    points.append(tuple([random.randint(x_th, imgdimens[0]-x_th), random.randint(y_th, imgdimens[1]-y_th)]))
                    # for every point, generate another random point in a short range
                    alpha = 2 * math.pi * random.random()  # random angle
                    # random radius within max_radius. Note: the distribution is not linear
                    sigma = interp(random.randint(1,1000), [1, 1000], [0.25, 1])
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
        if e.startswith('i'):  # invert-flag
            build_str += f" -negate "
            continue
        if e.startswith('u'):
            continue
        if e.startswith('g'):  # greyscale-flag
            build_str += f" -grayscale average "
            continue
        invalid_args_list.append(e)
        argument_error.description = "Invalid argument(s): " + \
            str(invalid_args_list) + ".\nFor argument usage refer to `§help`"
        arg_error_flag = True
        if DEBUG:
            print("[ERROR]: invalid argument '" + e + "'")

    # note: added compression in command
    distortcmd = f"magick " + \
        os.path.join(
            "raw", f"{fname}") + build_str + os.path.join("results", f"{fname}")

    os.system(distortcmd)

    buf = BytesIO()
    buf.name = 'image.jpeg'

    # save file to /results/
    image = Image.open(f"results/{fname}")
    filetype = "JPEG" if fname.endswith(".jpg") else "PNG"
    image.save(buf, filetype)
    image.close()

    # backup file to /db_outputs
    bkp_path = os.path.join("/home", "db_outputs")
    if os.path.exists(bkp_path):
        if DEBUG:
            print("[DEBUG]: free backup space: " +
                  str(psutil.disk_usage(bkp_path).free) + "B")
        if psutil.disk_usage(bkp_path).free >= 536870912:  # around 500MiB
            try:
                shutil.copy(f"results/{fname}", bkp_path)
                if DEBUG:
                    print(f"stored image: {fname}")
            except:
                traceback.print_exc()
        else:
            print(
                "IOError: couldn't save the output file to db_outputs. Maybe check disk...?")
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
    # Create API object
    try:
        api.verify_credentials()
    except Exception as e:
        raise e
    if DEBUG:
        print("[Twitter] Authentication Successful!")
        print("──────────────────────────────────────────────────────────────")
    twitter_bot_loop.start()
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
        response = "```[Debug]\n" + timestr + \
            memstr + "Vers..:\t" + VERSION + "```"
        await message.channel.send(response)

    await bot.process_commands(message)


@bot.command(name='memtrace', help='Outputs last memorytrace', aliases=['t', 'trace'])
async def memtrace(ctx):
    #tracker.print_diff() # this termporarly solves schroedingers memory leak??
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
    collected = gc.collect() # manually collect garbage
    print("[Debug] garbage collected: " + str(collected) + " objects")
    embed_crash = discord.Embed(title=':white_check_mark: Garbage collected.', color=0x55FF55)
    embed_crash.description = f"```diff\n+ {collected} objects purged```"
    embed_crash.timestamp = datetime.utcnow()
    await ctx.send(embed=embed_crash)


@bot.command(name='help', help='Shows usage info', aliases=['h', 'info', 'usage'])
async def help(ctx):
    rand_color = random.randint(0, 0xFFFFFF)
    helpstr_args = "\n\n**Arguments:**\n`l`:  Seam-Carving factor\n`s`:  swirl (degrees)\n`n`:  noise\n`b`:  blur\n`c`:  contrast (allows negative values)\n`o`:  implode\n`d`:  shepard's distortion\n`i`:  invert colors\n`g`:  grayscale image\n`u`:  disable compression\nAll arguments can be arbitrarily combined or left out.\nOnly integer values are accepted, I advise to play around with those values to find something that looks good."
    helpstr_usage = "\n\n**Usage:**\n`§deform [option0][value] [option1][value] ...`\nExamples:\n _§deform s35 n95 l45 c+40 b1_\n_§deform l50 s25 c+30 n70 g_"
    help_embed = discord.Embed(
        description="[Website](https://bjarne.dev)\n[Github](https://github.com/bj4rnee/DeformBot)\n[Twitter](https://twitter.com/DeformBot)\n\n**Commands:**\n`help`:  Shows this help message\n`deform`:  Distort an attached image\nYou can also react to an image with `🤖` to quickly deform it." + helpstr_args + helpstr_usage, color=rand_color)
    help_embed.set_author(name="Hi, I'm an Open Source image distortion discord bot!", url="https://bjarne.dev/",
                          icon_url="https://cdn.discordapp.com/avatars/971742838024978463/4e6548403fb46347b84de17fe31a45b9.webp")
    await ctx.send(embed=help_embed)


@bot.command(name='deform', help='deform an image', aliases=['d', 'D' 'distort'])
async def deform(ctx, *args):
    global arg_error_flag
    async with lock:
        # set error flag to false
        arg_error_flag = False
        # first delete the existing files
        for delf in os.listdir("raw"):
            if delf.endswith(".jpg"):
                os.remove(os.path.join("raw", delf))

        for delf2 in os.listdir("results"):
            if delf2.endswith(".jpg"):
                os.remove(os.path.join("results", delf2))

        msg = ctx.message  # msg with command in it
        reply_msg = None  # original msg which was replied to with command
        ch = msg.channel

        if msg.reference != None:  # if msg is a reply
            reply_msg = await ctx.channel.fetch_message(msg.reference.message_id)
            msg = reply_msg

        try:
            if len(msg.embeds) <= 0: # no embeds
                url = msg.attachments[0].url
            else:
                url = msg.embeds[0].image.url
                if isinstance(url, str) == False:
                    await ctx.send(embed=embed_nofile_error)
                    return
        except (IndexError, TypeError):
            await ctx.send(embed=embed_nofile_error)
            return
        else:
            if url[0:26] == "https://cdn.discordapp.com":
                if url[-4:].casefold() == ".jpg".casefold() or url[-4:].casefold() == ".png".casefold() or url[-5:].casefold() == ".jpeg".casefold():
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
                            await ctx.send("[Debug] Processed image: " + image_name + "\nargs=" + str(args), file=distorted_file)
                            return
                        await ctx.send(file=distorted_file)
                        return
                else:
                    await ctx.send(embed=embed_wrongfile_error)
                    return


@bot.event
async def on_reaction_add(reaction, user):  # if reaction is on a cached message
    if user != bot.user:
        if str(reaction.emoji) == "🤖":
            async with lock:
                # first delete the existing files
                for delf in os.listdir("raw"):
                    if delf.endswith(".jpg"):
                        os.remove(os.path.join("raw", delf))

                for delf2 in os.listdir("results"):
                    if delf2.endswith(".jpg"):
                        os.remove(os.path.join("results", delf2))

                # fetch and process the image
                msg = reaction.message
                ch = msg.channel

                try:
                    if len(msg.embeds) <= 0: # no embeds
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
                        if url[-4:].casefold() == ".jpg".casefold() or url[-4:].casefold() == ".png".casefold() or url[-5:].casefold() == ".jpeg".casefold():
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
                                distorted_file = distort_image(image_name, ())

                                if DEBUG:
                                    print("distorted image: " + image_name)
                                    print(
                                        "──────────────────────────────────────────────────────────────")
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


async def check_mentions(api, s_id):
    """check mentions in v1.1 api"""
    # Retrieving mentions
    new_since_id = s_id
    twitter_media_url = ""
    for tweet in tweepy.Cursor(api.mentions_timeline, since_id=new_since_id, count=100, tweet_mode='extended').items():
        new_since_id = max(tweet.id, new_since_id)
        #os.environ['last_id'] = str(new_since_id)
        set_key(".env", 'last_id', str(new_since_id)) # only works when process is terminated
        if hasattr(tweet, 'text'):
            tweet_txt = tweet.text.lower()
        else:
            tweet_txt = tweet.full_text.lower()
        if hasattr(tweet, 'possibly_sensitive'):
            sensitive = tweet.possibly_sensitive
        else:
            sensitive = False
        reply_og_id  = tweet.in_reply_to_status_id # original status (if 'tweet' is a reply)
        if DEBUG:
            print("[DEBUG] tweet from " + tweet.user.screen_name + ": '" + tweet_txt + "', sensitive: " + str(sensitive) + ", reply: " + str(reply_og_id))
        
        if 'media' in tweet.entities: # tweet that mentionions db contains image
            raw_image = tweet.entities.get('media', [])
            if(len(raw_image) > 0):
                twitter_media_url = raw_image[0]['media_url']
            else:
                twitter_media_url = "[ERROR] No url found"
            print(twitter_media_url)
        else: # tweet that the mentioner replies to contains image
            if isinstance(reply_og_id, str) or isinstance(reply_og_id, int):
                r_tweet = api.get_status(reply_og_id)
                if 'media' in r_tweet.entities:
                    raw_image = r_tweet.entities.get('media', [])
                    if(len(raw_image) > 0):
                        twitter_media_url = raw_image[0]['media_url']
                    else:
                        twitter_media_url = "[ERROR] No url found"
                    print(twitter_media_url)
                else:
                    api.update_status(status="[ERROR] no media found.", in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True, possibly_sensitive=sensitive)
                    continue
            else:
                continue
        async with lock: # from here proceed with lock!
            if twitter_media_url[0:26] == "http://pbs.twimg.com/media":
                if twitter_media_url[-4:].casefold() == ".jpg".casefold() or twitter_media_url[-4:].casefold() == ".png".casefold() or twitter_media_url[-5:].casefold() == ".jpeg".casefold():
                    r = requests.get(twitter_media_url, stream=True)
                    image_name = str(uuid.uuid4()) + '.jpg'  # generate uuid

                    with open(os.path.join("raw", image_name), 'wb') as out_file:
                        if DEBUG:
                            print("───────────" + image_name + "───────────")
                            print("saving image: " + image_name)
                        shutil.copyfileobj(r.raw, out_file)
                        out_file.flush()
                        args = tuple([x for x in tweet_txt.split() if all(y not in x for y in '@.')]) # remove mention and links from args
                        # distort the file
                        distort_image(image_name, args)

                        if arg_error_flag:
                            pass # we're not sending massive amounts of error msgs to twitter

                        if DEBUG:
                            print("distorted image: " + image_name)
                            print(
                                "──────────────────────────────────────────────────────────────")
                        # send distorted image
                        result_img = api.media_upload(os.path.join("results", image_name)) # TODO 5MB FILESIZE LIMIT!!!!!!!!!!!!!
                        if DEBUG:
                            api.update_status(status="[DEBUG] Processed image: " + image_name + "\nargs=" + str(args), in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True, possibly_sensitive=sensitive, media_ids=[result_img.media_id])
                            continue
                        api.update_status(status=" ", in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True, possibly_sensitive=sensitive, media_ids=[result_img.media_id])
                        continue
                else:
                    api.update_status(status="[ERROR] no media found.", in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True, possibly_sensitive=sensitive)
                    continue

#api.update_status('@' + tweet.user.screen_name + " Here's your Quote", tweet.id, media_ids=[result_img.media_id])

    return new_since_id


# THIS IS THE LOOP FOR THE TWITTER BOT
@tasks.loop(seconds=60)
async def twitter_bot_loop():
    global since_id
    # execute this every minute
    #s_id = int(os.getenv('last_id'))
    #set_key("../discord/.env", 'last_id', str(new_since_id)) = 
    since_id = await check_mentions(api, since_id)

bot.run(TOKEN)
