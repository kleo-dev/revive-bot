
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
    1352404223127588924
])

TOKEN = env['TOKEN']
HOURS = 10
ROLE = env['ROLE']
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

@tasks.loop(seconds=HOURS)
async def check_inactivity():
    if ROLE is not None:
        current_question = None
        for channel in CHANNELS:
            async for message in channel.history(limit=1):
                if (datetime.now(timezone.utc) - message.created_at).total_seconds() > HOURS:
                    if current_question is None:
                        current_question = requests.get(OPENTDB_URL).json()['results'][0]

                    decoded_data = {k: decode(v) if isinstance(v, str) else [decode(i) for i in v] for k, v in current_question.items()}

                    answers: list[str] = list(decoded_data['incorrect_answers'] + [decoded_data['correct_answer']])

                    shuffle(answers)

                    role_mention = f"<@&{ROLE}>"
                    embedVar = discord.Embed(title=decoded_data['question'], description="", color=0x00ff00)
                    embedVar.add_field(name="Difficulty", value=decoded_data['difficulty'].capitalize(), inline=False)
                    embedVar.add_field(name="Answers", value='**'+('\n'.join(['- '+a for a in answers]))+'**', inline=False)
                    msg = await channel.send(role_mention, embed=embedVar)

                    def check(m):
                        return m.reference and m.reference.message_id == msg.id and m.author != bot.user

                    for _ in range(0, 10):
                        reply = await bot.wait_for("message", check=check)

                        if reply.content.lower() == decoded_data['correct_answer'].lower():
                            await reply.add_reaction("✅")
                        else:
                            await reply.add_reaction("❌")

bot.run(TOKEN)
