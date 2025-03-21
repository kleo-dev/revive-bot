
import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timezone
from base64 import b64decode
import requests
from random import shuffle
from os import environ as env

# Channel ids
CUSTOM_CHANNELS = set([
    int(env['CHANNEL_ID'])
])

TOKEN = env['TOKEN']
MINUTES = 30
ROLE = int(env['ROLE'])
CHANNELS = set([])

def decode(value):
    return b64decode(value).decode('utf-8')

OPENTDB_URL = 'https://opentdb.com/api.php?amount=1&category=28&encode=base64'

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    for cc in CUSTOM_CHANNELS:
        print(f'Custom channel: {cc}')
        CHANNELS.add(bot.get_channel(cc))
    check_inactivity.start()

active_trivia = {}  # Format: {message_id: {"correct_answer": answer, "count": 0}}

@tasks.loop(seconds=150)
async def check_inactivity():
    if ROLE is not None:
        current_time = datetime.now(timezone.utc)
        print(f"{current_time.strftime('%H:%M:%S')} - Running inactivity check")
        current_question = None
        for channel in CHANNELS:
            print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} - Checking channel {channel.name}")
            async for message in channel.history(limit=1):
                # seconds_since = (current_time - message.created_at).total_seconds()
                # print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} - Time since last message: {seconds_since} seconds")
                minutes_since = (current_time - message.created_at).total_seconds() / 60
                print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} - Time since last message: {minutes_since} minutes")
                if minutes_since > MINUTES:
                    print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} - Channel is inactive, sending message")
                    if current_question is None:
                        current_question = requests.get(OPENTDB_URL).json()['results'][0]

                    decoded_data = {k: decode(v) if isinstance(v, str) else [decode(i) for i in v] for k, v in current_question.items()}
                    answers = list(decoded_data['incorrect_answers']) + [decoded_data['correct_answer']]
                    shuffle(answers)

                    role_mention = f"<@&{ROLE}>"
                    embedVar = discord.Embed(title=decoded_data['question'], description="", color=0x00ff00)
                    embedVar.add_field(name="Difficulty", value=str(decoded_data['difficulty']).capitalize(), inline=False)
                    embedVar.add_field(name="Answers", value='**'+('\n'.join(['- '+str(a) for a in answers]))+'**', inline=False)
                    msg = await channel.send(role_mention, embed=embedVar)

                    # Store this question in our tracking dict
                    active_trivia[msg.id] = {
                        "correct_answer": str(decoded_data['correct_answer']).lower(),
                        "count": 0,
                        "max_replies": 10
                    }
                    print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} - Added trivia question ID {msg.id}")


@bot.event
async def on_message(message):
    # Process commands first (important for command handling)
    await bot.process_commands(message)

    # Skip if it's a bot message
    if message.author.bot:
        return

    # Check if this is a reply to a trivia question
    if message.reference and message.reference.message_id in active_trivia:
        trivia_data = active_trivia[message.reference.message_id]

        # Check answer
        if message.content.lower() == trivia_data["correct_answer"]:
            await message.add_reaction("✅")
        else:
            await message.add_reaction("❌")

        # Increment the count
        trivia_data["count"] += 1

        # If we've reached max replies, remove this question from tracking
        if trivia_data["count"] >= trivia_data["max_replies"]:
            del active_trivia[message.reference.message_id]
            print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} - Removed trivia question ID {message.reference.message_id} after {trivia_data['max_replies']} replies")

bot.run(TOKEN)
