import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI
import agentops

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")

agentops.init(api_key=AGENTOPS_API_KEY, default_tags=["clawbot", "discord"])

openai_client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are Clawbot, a sharp and helpful AI assistant on Discord. "
    "Keep responses concise and friendly. Use Discord markdown formatting "
    "where appropriate (bold, code blocks, etc)."
)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

conversation_history = {}


def get_ai_reply(user_id: str, user_message: str) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({"role": "user", "content": user_message})

    # keep last 10 messages per user to avoid token overflow
    recent = conversation_history[user_id][-10:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + recent

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
    )

    reply = response.choices[0].message.content
    conversation_history[user_id].append({"role": "assistant", "content": reply})
    return reply


@bot.event
async def on_ready():
    print(f"Clawbot is online as {bot.user} (ID: {bot.user.id})")
    print("------")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # respond when mentioned or in DMs
    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = bot.user in message.mentions

    if not is_dm and not is_mentioned:
        await bot.process_commands(message)
        return

    content = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not content:
        return

    async with message.channel.typing():
        try:
            reply = get_ai_reply(str(message.author.id), content)
            # split long replies to stay under Discord's 2000 char limit
            if len(reply) <= 2000:
                await message.reply(reply)
            else:
                chunks = [reply[i:i+1990] for i in range(0, len(reply), 1990)]
                for chunk in chunks:
                    await message.channel.send(chunk)
        except Exception as e:
            await message.reply(f"Sorry, something went wrong: {e}")

    await bot.process_commands(message)


@bot.command(name="reset")
async def reset(ctx):
    """Clear your conversation history with Clawbot."""
    user_id = str(ctx.author.id)
    if user_id in conversation_history:
        del conversation_history[user_id]
    await ctx.reply("Conversation reset! Fresh start.")


@bot.command(name="ping")
async def ping(ctx):
    await ctx.reply(f"Pong! Latency: {round(bot.latency * 1000)}ms")


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set in .env")
    bot.run(DISCORD_TOKEN)
