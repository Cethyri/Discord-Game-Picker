from itertools import count
import os
import random
import re
from typing import Match

import discord
from discord.channel import TextChannel
from discord.flags import Intents
from discord.guild import Guild
from discord.member import Member
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents: Intents = discord.Intents.none()
intents.members = True
intents.guilds = True
intents.messages = True

client = discord.Client(intents = intents)

bot.gameChannel: TextChannel = None
bot.general: TextChannel = None

bot.games: list = []

@client.event
async def on_ready():
    guild: Guild = discord.utils.get(client.guilds, name=GUILD)

    for channel in guild.channels:
        if (channel.name == 'random-pick'):
            bot.gameChannel = channel
        if (channel.name == 'general'):
            bot.general = channel
    
    if gameChannel == None:
        await general.send('I couldn''t find a channel called "random-pick"')
        


@client.event
async def on_member_join(member):
    await member.create_dm()
    await member.dm_channel.send(
        f'Hi {member.name}, welcome to my Discord server!'
    )

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    print(f'{message.content}')

    if 'boop' in message.content:

        if gameChannel != None and games.count == 0:
            async for message in gameChannel.history():
                if message.author != client.user:
                    gameEntries = re.findall('(?:\r\n|^)\s+\d+\s*-\s*(.+)')
                    for gameEntry in gameEntries:
                        games.append(gameEntry)
        elif gameChannel == None:
            await message.channel.send('I couldn''t find a channel called "random-pick"')

        if games.count == 0:
            await message.channel.send('I couldn''t find any games')
        else:
            game = random.choice(games)
            await message.channel.send(f'How about {game}.')


@client.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise()

client.run(TOKEN)