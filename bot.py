import asyncio
import os
import re
from collections import Counter
from contextlib import asynccontextmanager

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

DB_PATH = "mentions.sqlite3"
MENTION_RE = re.compile(r"<@!?(\d+)>")   # robust against nick‑mentions <@!id>

INITIAL_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS mention_counts (
    guild_id    INTEGER,
    channel_id  INTEGER,
    user_id     INTEGER,
    count       INTEGER  DEFAULT 0,
    PRIMARY KEY (guild_id, channel_id, user_id)
);
"""

###############################################################################
# ──  Persistence helpers  ────────────────────────────────────────────────────
###############################################################################
@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
        await db.commit()

async def ensure_db():
    async with get_db() as db:
        await db.execute(INITIAL_TABLE_SQL)

async def bump_counts(guild_id: int, channel_id: int, user_ids: list[int], delta: int = 1):
    async with get_db() as db:
        for uid in user_ids:
            await db.execute(
                """INSERT INTO mention_counts VALUES(?,?,?,?)
                   ON CONFLICT(guild_id,channel_id,user_id)
                   DO UPDATE SET count = count + ?""",
                (guild_id, channel_id, uid, delta, delta),
            )

async def fetch_count(guild_id: int, channel_id: int | None, user_id: int) -> int:
    clause = "AND channel_id = ?" if channel_id else ""
    async with get_db() as db:
        row = await db.execute_fetchone(
            f"SELECT SUM(count) AS c FROM mention_counts "
            f"WHERE guild_id = ? {clause} AND user_id = ?",
            (guild_id, *(channel_id,) if channel_id else tuple(), user_id),
        )
        return row["c"] or 0

async def fetch_leaderboard(guild_id: int, channel_id: int | None, limit: int = 10):
    clause = "AND channel_id = ?" if channel_id else ""
    async with get_db() as db:
        rows = await db.execute_fetchall(
            f"""SELECT user_id, SUM(count) AS c
                   FROM mention_counts
                  WHERE guild_id = ? {clause}
               GROUP BY user_id
               ORDER BY c DESC
               LIMIT ?""",
            (guild_id, *(channel_id,) if channel_id else tuple(), limit),
        )
        return [(r["user_id"], r["c"]) for r in rows]

###############################################################################
# ──  Bot setup  ──────────────────────────────────────────────────────────────
###############################################################################
intents = discord.Intents.default()
intents.message_content = True
intents.members = True   # needed only for pretty names in /leaderboard

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await ensure_db()
    await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

###############################################################################
# ──  Message handler ─────────────────────────────────────────────────────────
###############################################################################
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    mentioned_ids = {m.id for m in message.mentions}
    # Also catch raw mention strings in case message.mentions misses edits / partials
    mentioned_ids.update(map(int, MENTION_RE.findall(message.content)))

    if mentioned_ids:
        await bump_counts(message.guild.id, message.channel.id, list(mentioned_ids))

    await bot.process_commands(message)   # let command framework run too

###############################################################################
# ──  Slash commands  ─────────────────────────────────────────────────────────
###############################################################################
@bot.tree.command(description="How many times has a user been @‑mentioned?")
@app_commands.describe(
    user="The person you care about",
    channel="Limit to a specific channel (optional)",
)
async def mentions(interaction: discord.Interaction, user: discord.User,
                   channel: discord.TextChannel | None = None):
    total = await fetch_count(interaction.guild.id, channel.id if channel else None, user.id)
    scope = f"in {channel.mention}" if channel else "server‑wide"
    await interaction.response.send_message(
        f"{user.mention} has been mentioned **{total}** times {scope}.",
        ephemeral=True,
    )

@bot.tree.command(description="Top chatter magnets")
@app_commands.describe(
    channel="Limit to a specific channel",
    limit="How many users to display (default 10)"
)
async def leaderboard(interaction: discord.Interaction,
                      channel: discord.TextChannel | None = None,
                      limit: app_commands.Range[int, 1, 50] = 10):
    rows = await fetch_leaderboard(interaction.guild.id, channel.id if channel else None, limit)
    if not rows:
        await interaction.response.send_message("No data yet.", ephemeral=True)
        return

    lines = []
    for rank, (uid, c) in enumerate(rows, start=1):
        member = interaction.guild.get_member(uid) or await interaction.guild.fetch_member(uid)
        lines.append(f"`#{rank:02}` {member.mention} – **{c}** mentions")
    header = f"**Leaderboard {'in ' + channel.mention if channel else '(server‑wide)'}**\n"
    await interaction.response.send_message(header + "\n".join(lines))

###############################################################################
# ──  Run it ──────────────────────────────────────────────────────────────────
###############################################################################
asyncio.run(bot.start(os.environ["DISCORD_TOKEN"]))
