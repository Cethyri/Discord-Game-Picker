from itertools import count
import os
import random
import re

from dotenv import load_dotenv

import discord
from discord.channel import TextChannel
from discord.flags import Intents
from discord.guild import Guild
from discord.member import Member
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents: Intents = discord.Intents.none()
intents.members = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix='')

class GlobalInfo:
    pass

bot.g = GlobalInfo()

bot.g.gameChannel = None
bot.g.general = None

bot.g.games = []

@bot.event
async def on_ready():
    guild: Guild = discord.utils.get(bot.guilds, name=GUILD)

    for channel in guild.channels:
        if (channel.name == 'random-pick'):
            bot.g.gameChannel = channel
        if (channel.name == 'general'):
            bot.g.general = channel
    
    if bot.g.gameChannel == None:
        await bot.g.general.send('I couldn''t find a channel called "random-pick"')
        


@bot.event
async def on_member_join(member):
    await member.create_dm()
    await member.dm_channel.send(
        f'Hi {member.name}, welcome to my Discord server!'
    )

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    print(f'{message.content}: {"boop" in message.content}')

    if 'boop' in message.content:
        if bot.g.gameChannel != None:
            if len(bot.g.games) == 0:
                print(f'here 1')
                async for message in bot.g.gameChannel.history():
                    if message.author != bot.user:
                        print(f'not here')
                        gameEntries = re.findall('(?:\r\n|^)\s+\d+\s*-\s*(.+)')
                        for gameEntry in gameEntries:
                            print(f'{gameEntry}')
                            bot.g.games.append(gameEntry)

            if len(bot.g.games) == 0:
                print(f'here 3')
                await message.channel.send('I couldn''t find any games')
            else:
                print(f'here 4')
                game = random.choice(bot.g.games)
                await message.channel.send(f'How about {game}.')
        elif bot.g.gameChannel == None:
            print(f'here 2')
            await message.channel.send('I couldn''t find a channel called "random-pick"')


@bot.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise()

bot.run(TOKEN)