import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
from base64 import b64decode
import requests
from random import shuffle
from os import environ as env

# Channel ids
TOKEN = env['TOKEN']
MINUTES = 30
ROLE = int(env['ROLE'])
CHANNEL = None  # Global variable

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
    global CHANNEL  # Fixing scope issue
    print(f"Logged in as {bot.user}")
    CHANNEL = bot.get_channel(int(env['CHANNEL_ID']))

    if CHANNEL is None:
        print("Error: Channel ID is invalid or bot lacks permissions.")
        return

    await send_trivia()
    check_inactivity.start()  # Now starts only if CHANNEL is valid

active_trivia = {}  # Format: {message_id: {"correct_answer": answer, "count": 0}}

@tasks.loop(seconds=150)
async def check_inactivity():
    global CHANNEL
    if CHANNEL is None:
        print("Error: CHANNEL is None, skipping inactivity check.")
        return

    if ROLE is not None:
        current_time = datetime.now(timezone.utc)
        print(f"{current_time.strftime('%H:%M:%S')} - Running inactivity check")
        print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} - Checking channel {CHANNEL.name}")
        async for message in CHANNEL.history(limit=1):
            minutes_since = (current_time - message.created_at).total_seconds() / 60
            print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} - Time since last message: {minutes_since} minutes")
            if minutes_since > MINUTES:
                await send_trivia()


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

        if message.author.id in trivia_data["replies"]:
            return

        if message.content.lower().startswith(trivia_data["correct_answer"].lower()):
            await message.add_reaction("✅")
        else:
            await message.add_reaction("❌")

        trivia_data["replies"].append(message.author.id)

        # If we've reached max replies, remove this question from tracking
        if len(trivia_data["replies"]) >= trivia_data["max_replies"]:
            del active_trivia[message.reference.message_id]
            print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} - Removed trivia question ID {message.reference.message_id} after {trivia_data['max_replies']} replies")

async def send_trivia():
    global CHANNEL
    if CHANNEL is None:
        print("Error: CHANNEL is None, cannot send trivia.")
        return

    print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} - Channel is inactive, sending message")
    current_question = requests.get(OPENTDB_URL).json()['results'][0]

    decoded_data = {k: decode(v) if isinstance(v, str) else [decode(i) for i in v] for k, v in current_question.items()}
    answers = list(decoded_data['incorrect_answers']) + [decoded_data['correct_answer']]
    shuffle(answers)

    role_mention = f"<@&{ROLE}>"
    embedVar = discord.Embed(title=decoded_data['question'], description="Reply to answer", color=0x00ff00)
    embedVar.add_field(name="Difficulty", value=str(decoded_data['difficulty']).capitalize(), inline=False)
    embedVar.add_field(name="Answers", value='**'+('\n'.join(['- '+str(a) for a in answers]))+'**', inline=False)
    msg = await CHANNEL.send(role_mention, embed=embedVar)

    # Store this question in our tracking dict
    active_trivia[msg.id] = {
        "correct_answer": str(decoded_data['correct_answer']).lower(),
        "replies": [],
        "max_replies": 40
    }
    print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} - Added trivia question ID {msg.id}")

bot.run(TOKEN)
