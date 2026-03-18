import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI
import agentops
import yt_dlp

load_dotenv()

DISCORD_TOKEN   = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")

agentops.init(api_key=AGENTOPS_API_KEY, default_tags=["clawbot", "discord"])

openai_client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are Clawbot, a sharp and helpful AI assistant on Discord. "
    "Keep responses concise and friendly. Use Discord markdown where appropriate."
)

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

conversation_history: dict[str, list] = {}

# ── Active listening channels (bot responds to all messages, no mention needed)
active_channels: set[int] = set()

# ── Music queue per guild ──────────────────────────────────────────────────────
music_queues: dict[int, list] = {}

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "extractor_args": {"youtube": {"player_client": ["web"]}},
    "js_runtimes": [f"node:{r'C:\Program Files\nodejs\node.exe'}"],
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


def get_ai_reply(user_id: str, user_message: str) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    conversation_history[user_id].append({"role": "user", "content": user_message})
    recent = conversation_history[user_id][-10:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + recent
    response = openai_client.chat.completions.create(
        model="gpt-4o", messages=messages, max_tokens=1024, temperature=0.7
    )
    reply = response.choices[0].message.content
    conversation_history[user_id].append({"role": "assistant", "content": reply})
    return reply


async def get_audio_source(query: str):
    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
        data = await loop.run_in_executor(
            None, lambda: ydl.extract_info(query, download=False)
        )
        if "entries" in data:
            data = data["entries"][0]
        url   = data["url"]
        title = data.get("title", "Unknown")
        return url, title


# ── Events ─────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"Clawbot online as {bot.user} (ID: {bot.user.id})")
    print("Commands: !ask !imagine !listen !unlisten !play !stop !pause !resume !skip !queue !reset !ping")
    print("------")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    is_dm          = isinstance(message.channel, discord.DMChannel)
    is_mentioned   = bot.user in message.mentions
    is_command     = message.content.startswith(bot.command_prefix)
    is_active_ch   = message.channel.id in active_channels

    # always process commands first (works in both DMs and servers)
    if is_command:
        await bot.process_commands(message)
        return

    # in a server: respond when mentioned OR in an active listening channel
    if not is_dm and not is_mentioned and not is_active_ch:
        return

    # strip the mention if present and get clean content
    content = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not content:
        return

    async with message.channel.typing():
        try:
            reply = get_ai_reply(str(message.author.id), content)
            if len(reply) <= 2000:
                await message.reply(reply)
            else:
                for chunk in [reply[i:i+1990] for i in range(0, len(reply), 1990)]:
                    await message.channel.send(chunk)
        except Exception as e:
            await message.reply(f"Sorry, something went wrong: {e}")


# ── Chat commands ───────────────────────────────────────────────────────────────

@bot.command(name="ask")
async def ask(ctx, *, question: str):
    """Ask Clawbot anything: !ask <question>"""
    async with ctx.typing():
        try:
            reply = get_ai_reply(str(ctx.author.id), question)
            if len(reply) <= 2000:
                await ctx.reply(reply)
            else:
                for chunk in [reply[i:i+1990] for i in range(0, len(reply), 1990)]:
                    await ctx.send(chunk)
        except Exception as e:
            await ctx.reply(f"Error: {e}")


@bot.command(name="listen")
async def listen(ctx):
    """Make Clawbot respond to ALL messages in this channel (no @mention needed)."""
    if isinstance(ctx.channel, discord.DMChannel):
        return await ctx.reply("Already active in DMs by default!")
    active_channels.add(ctx.channel.id)
    await ctx.reply(
        f"Now listening to **#{ctx.channel.name}**! "
        f"I'll respond to every message here. Use `!unlisten` to stop."
    )


@bot.command(name="unlisten")
async def unlisten(ctx):
    """Stop Clawbot from responding to every message in this channel."""
    active_channels.discard(ctx.channel.id)
    await ctx.reply(f"Stopped listening to **#{ctx.channel.name}**. Mention me to chat.")


@bot.command(name="reset")
async def reset(ctx):
    """Clear your conversation history."""
    conversation_history.pop(str(ctx.author.id), None)
    await ctx.reply("Conversation cleared! Fresh start.")


@bot.command(name="ping")
async def ping(ctx):
    await ctx.reply(f"Pong! `{round(bot.latency * 1000)}ms`")


# ── Image generation ────────────────────────────────────────────────────────────

@bot.command(name="imagine")
async def imagine(ctx, *, prompt: str):
    """Generate an image with DALL-E 3: !imagine <prompt>"""
    async with ctx.typing():
        try:
            await ctx.reply(f"Generating: **{prompt}** ...")
            response = openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            embed = discord.Embed(title=prompt[:256], color=0x6c63ff)
            embed.set_image(url=image_url)
            embed.set_footer(text="Generated by Clawbot · DALL-E 3")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.reply(f"Image generation failed: {e}")


# ── Music commands ──────────────────────────────────────────────────────────────

@bot.command(name="play")
async def play(ctx, *, query: str):
    """Play a song: !play <song name or YouTube URL>"""
    if isinstance(ctx.channel, discord.DMChannel):
        return await ctx.reply("Music only works in a server voice channel, not in DMs.")
    if not ctx.author.voice:
        return await ctx.reply("You need to be in a voice channel first!")

    voice_channel = ctx.author.voice.channel
    vc = ctx.voice_client

    if vc is None:
        vc = await voice_channel.connect()
    elif vc.channel != voice_channel:
        await vc.move_to(voice_channel)

    guild_id = ctx.guild.id
    if guild_id not in music_queues:
        music_queues[guild_id] = []

    async with ctx.typing():
        try:
            url, title = await get_audio_source(query)
            music_queues[guild_id].append((url, title))
            if vc.is_playing() or vc.is_paused():
                await ctx.reply(f"Added to queue: **{title}**")
            else:
                await _play_next(ctx, vc)
        except Exception as e:
            await ctx.reply(f"Could not play that: {e}")


async def _play_next(ctx, vc):
    guild_id = ctx.guild.id
    if not music_queues.get(guild_id):
        return
    url, title = music_queues[guild_id].pop(0)
    source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
    source = discord.PCMVolumeTransformer(source, volume=0.5)

    def after_play(error):
        if error:
            print(f"Music error: {error}")
        fut = asyncio.run_coroutine_threadsafe(_play_next(ctx, vc), bot.loop)
        try:
            fut.result()
        except Exception:
            pass

    vc.play(source, after=after_play)
    await ctx.send(f"Now playing: **{title}**")


@bot.command(name="skip")
async def skip(ctx):
    """Skip the current song."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.reply("Skipped!")
    else:
        await ctx.reply("Nothing is playing.")


@bot.command(name="pause")
async def pause(ctx):
    """Pause the music."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.reply("Paused.")
    else:
        await ctx.reply("Nothing is playing.")


@bot.command(name="resume")
async def resume(ctx):
    """Resume the music."""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.reply("Resumed!")
    else:
        await ctx.reply("Nothing is paused.")


@bot.command(name="stop")
async def stop(ctx):
    """Stop music and clear the queue."""
    guild_id = ctx.guild.id
    music_queues[guild_id] = []
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
    await ctx.reply("Stopped and disconnected.")


@bot.command(name="queue")
async def queue(ctx):
    """Show the current music queue."""
    guild_id = ctx.guild.id
    q = music_queues.get(guild_id, [])
    if not q:
        return await ctx.reply("Queue is empty.")
    lines = [f"`{i+1}.` {title}" for i, (_, title) in enumerate(q)]
    embed = discord.Embed(title="Music Queue", description="\n".join(lines), color=0x3ecfcf)
    await ctx.send(embed=embed)


# ── Run ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set in .env")
    bot.run(DISCORD_TOKEN)
