#!/usr/bin/env python3
PYTHONUNBUFFERED=1

from enum import Enum
from itertools import count
import json
import os
import random
import re
from datetime import datetime, time, timezone
from typing import List, Text
from types import SimpleNamespace
from discord.activity import Game

from dotenv import load_dotenv

import discord
from discord.channel import TextChannel
from discord.flags import Intents
from discord.guild import Guild
from discord.member import Member
from discord.ext import commands

from base import JsonDict
from properties import json_basic, json_dict, json_list

random.seed(datetime.now().microsecond)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

SAVE='botInfo.json'
STARTER='starterInfo.json'

intents: Intents = discord.Intents.none()
intents.members = True
intents.guilds = True
intents.messages = True

class JulianVote(str, Enum):
	up		= 'up'
	down	= 'down'
	not_set	= 'na'

class GameInfo(JsonDict):
	name:		str			= json_basic('name', str)
	upVotes:	int			= json_basic('upvotes', int)
	downVotes:	int			= json_basic('downVotes', int)
	julianVote:	JulianVote	= json_basic('julianVote', JulianVote)
	flags:		List[str]	= json_list('flags', str)

class GlobalInfo(JsonDict):
	gameChannel:	str				= json_basic('gameChannel', str)
	general:		str				= json_basic('general', str)
	games:			List[GameInfo]	= json_list('games', GameInfo)
	suggestions:	List[str]		= json_list('suggestions', str)
	greetings:		List[str]		= json_list('greetings', str)
	farewells:		List[str]		= json_list('farewells', str)
	pass

class GamePickerBot(commands.Bot):
	def __init__(self, bot: commands.Bot, globals: GlobalInfo):
		self.__bot = bot
		self.g = globals

	def __getattr__(self, attr):
		return object.__getattribute__(self.__bot, attr)

	def __setattr__(self, attr, val):
		if attr == '_GamePickerBot__bot':
			object.__setattr__(self, attr, val)
		else:
			return setattr(self.__bot, attr, val)

if os.path.exists(SAVE):
	with open(SAVE, 'r') as save_file:
		json_info = json.load(save_file)
else:
	with open(STARTER, 'r') as save_file:
		json_info = json.load(save_file)

bot = commands.Bot(command_prefix='', case_insensitive=True)
bot = GamePickerBot(bot, GlobalInfo(json_info))
bot.temp = SimpleNamespace()


@bot.event
async def on_ready():
	
	guild: Guild = discord.utils.get(bot.guilds, name=GUILD)

	print("ready")

	bot.ch = SimpleNamespace()

	for channel in guild.channels:
		if (channel.name == 'game-channel'):
			bot.ch.gameChannel = channel
		elif (channel.name == 'general'):
			bot.ch.general = channel
	
	# if bot.ch.gameChannel == None:
	# 	category = await guild.create_category('BOT CHANNELS')

	# 	overwrites = {
	# 		guild.default_role: discord.PermissionOverwrite(view_channel=False),
	# 		guild.me: discord.PermissionOverwrite(view_channel=True),
	# 		discord.utils.get(guild.roles, name='ADMON'): discord.PermissionOverwrite(view_channel=True),
	# 		discord.utils.get(guild.roles, name='Capitan'): discord.PermissionOverwrite(view_channel=True)
	# 	}

	# 	bot.ch.gameChannel = await guild.create_text_channel('secret-game-channel', overwrites=overwrites, category=category)
	await send_greeting(bot)

async def send_greeting(bot: commands.Bot, channel: TextChannel = None):
	if channel is None:
		channel = bot.ch.general
	todaydate = datetime.now().date()
	today = datetime(todaydate.year, todaydate.month, todaydate.day)
	start = today.astimezone(tz=timezone.utc)
	start = start.replace(tzinfo=None)
	doWakeUp = True
	async for message in channel.history(after=start):
		if message.author == bot.user:
			doWakeUp = False
	if doWakeUp:
		await channel.send(random.choice(bot.g.greetings))


@bot.event
async def on_message(message):
	if message.author == bot.user or message.author.bot:
		return

	content = message.content.lower()
	channel = message.channel

	await send_greeting(bot, channel)

	if 'hey bot, take a nap' in content or 'no more bot' in content:
		await channel.send(random.choice(bot.g.farewells))
		with open(SAVE, 'w') as outfile:
			json.dump(bot.g, outfile, sort_keys=True, indent=4)
		await bot.close()

	await bot.process_commands(message)

@bot.command(name='boop', help='Pick a random game.')
async def boop(ctx):
	channel = ctx.channel

	if len(bot.g.games) != 0:
		game = random.choice(bot.g.games)
		await channel.send(random.choice(bot.g.suggestions).format(game.name))
	else:
		await channel.send('I couldn\'t find any games')


@bot.command(name='save', help='Save game and bot information.')
async def save(ctx, silent = False):
	channel = ctx.channel
	with open(SAVE, 'w') as outfile:
		json.dump(bot.g, outfile, sort_keys=True, indent=4)
	if not silent:
		await channel.send('information saved!')

@bot.command(name='load-from', help='Load games from a channel using regex.\n\tRegex must be surrounded by quotes and quotes in the regex must be escaped.', aliases=['load'])
async def load_from(ctx, load_channel_name, regex):
	channel = ctx.channel

	guild: Guild = discord.utils.get(bot.guilds, name=GUILD)

	for find_channel in guild.channels:
		if (find_channel.name == load_channel_name):
			load_channel = find_channel

	bot.temp.games = []
	async for gameMessage in load_channel.history():
		if gameMessage.author != bot.user:
			gameEntries = re.findall(regex, gameMessage.content)
			for gameEntry in gameEntries:
				game = GameInfo()
				game.name = gameEntry
				bot.temp.games.append(game)

	bot.temp.games = (g for g in bot.temp.games if g.name not in (game.name for game in bot.g.games))
	
	if len(bot.temp.games) == 0:
		await channel.send('I couldn\'t find any games')
	else:
		message = 'Here\'s what I found:\n' + '\n'.join(g.name for g in bot.temp.games) + '\n\nkeep or discard?'
		await channel.send(message)

@bot.command(name='keep', help='Keep games found by the load-from command.')
async def keep(ctx):
	if len(bot.temp.games) > 0:
		bot.g.games += bot.temp.games
		await save(ctx, True)
		await ctx.channel.send('Games saved!')
	else:
		await ctx.channel.send('There are no games dummy.')

@bot.command(name='discard', help='Discard games found by the load-from command.')
async def discard(ctx):
	if len(bot.temp.games) > 0:
		bot.temp.games = []
		await ctx.channel.send('Games discarded.')
	else:
		await ctx.channel.send('I can\'t delete nothing...')

@bot.command(name='poof', help='Delete all Game-Picker bot messages in this channel.')
async def load_from(ctx):
	channel = ctx.channel

	async for message in channel.history():
		if message.author == bot.user:
			await message.delete()

@bot.event
async def on_disconnect():
	with open(SAVE, 'w') as outfile:
		json.dump(bot.g, outfile, sort_keys=True, indent=4)
	print('saved')

# @bot.event
# async def on_error(event, *args, **kwargs):
#     print(f'Unhandled message: {kwargs}\n')
#     # with open('err.log', 'a') as errorLog:
#     #     if event == 'on_message':
#     #         errorLog.write(f'Unhandled message: {args[0]}\n')
#     #     else:
#     #         raise()

bot.run(TOKEN)