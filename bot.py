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
	games:			List[GameInfo]	= json_list('games', GameInfo)
	suggestions:	List[str]		= json_list('suggestions', str)
	greetings:		List[str]		= json_list('greetings', str)
	farewells:		List[str]		= json_list('farewells', str)
	no_greeting:	List[str]		= json_list('no_greeting', str)
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

bot: GamePickerBot = GamePickerBot(commands.Bot(command_prefix='', case_insensitive=True), GlobalInfo(json_info))
bot.temp = SimpleNamespace()


def save_info(bot: GamePickerBot):
	with open(SAVE, 'w') as outfile:
		json.dump(bot.g, outfile, sort_keys=True, indent=4)

	print('saved')

def get_start_of_day():
	todaydate = datetime.now().date()
	today = datetime(todaydate.year, todaydate.month, todaydate.day)
	start = today.astimezone(tz=timezone.utc)
	return start.replace(tzinfo=None)

@bot.event
async def on_ready():
	
	guild: Guild = discord.utils.get(bot.guilds, name=GUILD)

	print("ready")

	bot.ch = SimpleNamespace()

	for channel in guild.channels:
		if (channel.name == 'general'):
			bot.ch.general = channel

	await send_greeting(bot)

async def send_greeting(bot: GamePickerBot, channel: TextChannel = None):
	if channel is None:
		channel = bot.ch.general
	if channel.name in bot.g.no_greeting:
		return
	

	doWakeUp = True
	
	guild: Guild = discord.utils.get(bot.guilds, name=GUILD)

	for otherChannel in guild.channels:
		if isinstance(otherChannel, TextChannel):
			async for message in otherChannel.history(after=get_start_of_day()):
				if message.author == bot.user:
					doWakeUp = False
					break
			if not doWakeUp:
				break
	if doWakeUp:
		await channel.send(random.choice(bot.g.greetings))


@bot.event
async def on_message(message):
	if message.author == bot.user or message.author.bot:
		return

	content = message.content.lower()
	channel = message.channel

	await send_greeting(bot, channel)

	await bot.process_commands(message)

@bot.command(name='bot-sleep', help='Disconnect the bot and save info.', aliases=['hey-bot-take-a-nap', 'no-more-bot', 'kill-boop', 'go-slep-pls', 'bot-slep-pls', 'bot-go-sleep'])
async def sleep(ctx):
	await ctx.channel.send(random.choice(bot.g.farewells))
	save_info(bot)
	await bot.close()


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
	save_info(bot)
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
				if game.name not in (x.name for x in bot.temp.games):
					bot.temp.games.append(game)

	bot.temp.games = (g for g in bot.temp.games if g.name.upper() not in (game.name.upper() for game in bot.g.games))
	
	if len(bot.temp.games) == 0:
		await channel.send('I couldn\'t find any games')
	else:
		message = 'Here\'s what I found:\n' + '\n'.join(g.name for g in bot.temp.games) + '\n\nkeep or discard?'
		await channel.send(message)

@bot.command(name='keep', help='Keep games found by the load-from command.')
async def keep(ctx):
	if len(bot.temp.games) > 0:
		bot.g.games += bot.temp.games
		save_info(bot)
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

@bot.command(name='add-game', help='Add a game to the list.', aliases=['add-boop', 'more-boop', 'have-boop'])
async def add_game(ctx, gameName: str):
	if gameName.upper() not in (x.name.upper() for x in bot.g.games) and len(gameName) > 0:
		game = GameInfo()
		game.name = gameName
		bot.g.games.append(game)
		save_info(bot)
		await ctx.channel.send(f'I\'ve added {gameName} to the list of games.')
	else:
		await ctx.channel.send(f'{gameName} is already in the list of games.')

@bot.command(name='remove-game', help='Remove a game from the list.', aliases=['remove-boop', 'less-boop', 'yeet-boop'])
async def add_game(ctx, gameName: str):
	removeGame = None
	for game in bot.g.games:
		if gameName.upper() == game.name.upper():
			removeGame = game
	if removeGame is not None:
		bot.g.games.remove(removeGame)
		save_info(bot)
		await ctx.channel.send(f'I\'ve removed {gameName} from the list of games.')
	else:
		await ctx.channel.send(f'{gameName} isn\'t in the list of games.')

@bot.command(name='poof', help='Delete all Game-Picker bot messages in this channel.')
async def poof(ctx):
	channel = ctx.channel

	async for message in channel.history(after=get_start_of_day()):
		if message.author == bot.user:
			await message.delete()

@bot.command(name='no-greeting', help='Stop the bot from sending greetings in a channel.\nUse here or leave the argument blank to stop greetings in the current channel.', aliases=['no-greetings', 'no-greet'])
async def no_greeting(ctx, channelName: str = 'here'):
	channel = ctx.channel

	name = channel.name if channelName == 'here' else channelName
	messagePart = 'this channel' if channelName == 'here' else f'channel:{channelName}'
	if name not in bot.g.no_greeting:
		bot.g.no_greeting.append(name)
		save_info(bot)
		await channel.send(f'No more greetings will be sent in {messagePart}')
	else:
		await channel.send(f'I already dont send greetings in {messagePart}')
	
@bot.command(name='allow-greeting', help='Allow the bot to send greetings in a channel.\nUse here or leave the argument blank to allow greetings in the current channel.', aliases=['allow-greetings', 'allow-greet'])
async def allow_greeting(ctx, channelName: str = 'here'):
	channel = ctx.channel

	name = channel.name if channelName == 'here' else channelName
	messagePart = 'this channel' if channelName == 'here' else f'channel:{channelName}'
	if name in bot.g.no_greeting:
		bot.g.no_greeting.remove(name)
		save_info(bot)
		await channel.send(f'Greetings can be sent in {messagePart}')
	else:
		await channel.send(f'I can already send greetings in {messagePart}')


@bot.event
async def on_disconnect():
	save_info(bot)

@bot.event
async def on_error(event, *args, **kwargs):
    print(f'Unhandled message: {kwargs}\n')
    # with open('err.log', 'a') as errorLog:
    #     if event == 'on_message':
    #         errorLog.write(f'Unhandled message: {args[0]}\n')
    #     else:
    #         raise()

bot.run(TOKEN)