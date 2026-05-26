"""
Discord bot that proxies messages to a NousResearch Hermes model
served via any OpenAI-compatible API (Ollama, LM Studio, vLLM, etc.).

Configuration via environment variables — see .env.example.
"""

import os
import asyncio
from collections import defaultdict, deque

import discord
from discord.ext import commands
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
DISCORD_TOKEN   = os.environ["DISCORD_BOT_TOKEN"]
API_BASE        = os.getenv("HERMES_API_BASE", "http://localhost:11434/v1")
API_KEY         = os.getenv("HERMES_API_KEY", "ollama")
MODEL           = os.getenv("HERMES_MODEL", "hermes3")
SYSTEM_PROMPT   = os.getenv(
    "HERMES_SYSTEM_PROMPT",
    "You are Hermes, a helpful and knowledgeable AI assistant.",
)
MAX_HISTORY     = int(os.getenv("HERMES_MAX_HISTORY", "20"))   # messages kept per channel
MAX_RESPONSE    = 1900                                          # Discord limit is 2000

# ── OpenAI-compatible client ──────────────────────────────────────────────────
hermes = AsyncOpenAI(api_key=API_KEY, base_url=API_BASE)

# ── Discord bot ───────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Per-channel conversation history  {channel_id: deque([{role, content}, ...])}
history: dict[int, deque] = defaultdict(lambda: deque(maxlen=MAX_HISTORY))


def _build_messages(channel_id: int, user_message: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    msgs.extend(history[channel_id])
    msgs.append({"role": "user", "content": user_message})
    return msgs


async def _ask_hermes(channel_id: int, user_message: str) -> str:
    messages = _build_messages(channel_id, user_message)
    response = await hermes.chat.completions.create(
        model=MODEL,
        messages=messages,
    )
    reply = response.choices[0].message.content or ""
    # Save the exchange in history
    history[channel_id].append({"role": "user", "content": user_message})
    history[channel_id].append({"role": "assistant", "content": reply})
    return reply


def _split_response(text: str) -> list[str]:
    """Split text into Discord-sized chunks, preferring newline boundaries."""
    if len(text) <= MAX_RESPONSE:
        return [text]
    chunks = []
    while len(text) > MAX_RESPONSE:
        cut = text.rfind("\n", 0, MAX_RESPONSE)
        if cut == -1:
            cut = MAX_RESPONSE
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


# ── Events ────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id={bot.user.id})")
    print(f"Connected to Hermes at {API_BASE}  model={MODEL}")


@bot.event
async def on_message(message: discord.Message):
    # Ignore own messages
    if message.author == bot.user:
        return

    # Respond when mentioned or in DMs; also process commands
    is_dm      = isinstance(message.channel, discord.DMChannel)
    is_mention = bot.user in message.mentions

    if is_dm or is_mention:
        content = message.content
        # Strip the mention text so Hermes doesn't see "<@123456>"
        if is_mention:
            content = content.replace(f"<@{bot.user.id}>", "").strip()

        if not content:
            await message.reply("Hey! Ask me anything.")
            return

        async with message.channel.typing():
            try:
                reply = await _ask_hermes(message.channel.id, content)
            except Exception as exc:
                await message.reply(f"⚠️ Hermes error: {exc}")
                return

        for chunk in _split_response(reply):
            await message.reply(chunk)
        return

    # Let command prefix fall through
    await bot.process_commands(message)


# ── Commands ──────────────────────────────────────────────────────────────────
@bot.command(name="chat")
async def chat_cmd(ctx: commands.Context, *, message: str):
    """Send a message to Hermes: !chat <message>"""
    async with ctx.typing():
        try:
            reply = await _ask_hermes(ctx.channel.id, message)
        except Exception as exc:
            await ctx.reply(f"⚠️ Hermes error: {exc}")
            return

    for chunk in _split_response(reply):
        await ctx.reply(chunk)


@bot.command(name="reset")
async def reset_cmd(ctx: commands.Context):
    """Clear the conversation history for this channel: !reset"""
    history[ctx.channel.id].clear()
    await ctx.reply("Conversation history cleared.")


@bot.command(name="help")
async def help_cmd(ctx: commands.Context):
    """Show available commands: !help"""
    embed = discord.Embed(
        title="Hermes Bot",
        description="Chat with the NousResearch Hermes model right inside Discord.",
        color=discord.Color.blurple(),
    )
    embed.add_field(name="@mention  <message>",  value="Chat in any channel by mentioning the bot.", inline=False)
    embed.add_field(name="DM the bot",            value="Send a DM directly to the bot to chat privately.", inline=False)
    embed.add_field(name="!chat <message>",       value="Explicitly send a message to Hermes.", inline=False)
    embed.add_field(name="!reset",                value="Wipe the conversation history for this channel.", inline=False)
    embed.add_field(name="!help",                 value="Show this message.", inline=False)
    embed.set_footer(text=f"Model: {MODEL}  |  API: {API_BASE}")
    await ctx.reply(embed=embed)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
