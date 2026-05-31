"""
アドラー心理学 Discord Bot - 固定チャンネル版（複数サーバー対応）
"""
 
import discord
from discord.ext import tasks
import json
import random
import datetime
import os
from pathlib import Path
 
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
TIMEZONE_OFFSET = 9
 
# ─── 送信先チャンネルID（固定）───────────────────────────
# {サーバーID: チャンネルID} の形式で追加できます
FIXED_CHANNELS = {
    "1510696478123888702": "1510674681525698754",
}
 
MESSAGES_FILE = Path(__file__).parent / "messages.json"
 
with open(MESSAGES_FILE, encoding="utf-8") as f:
    ALL_MESSAGES = json.load(f)
 
MORNING_MESSAGES = [m for m in ALL_MESSAGES if m["time"] == "morning"]
EVENING_MESSAGES = [m for m in ALL_MESSAGES if m["time"] == "evening"]
 
sent_today: dict = {}
 
def get_jst_now() -> datetime.datetime:
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    jst = datetime.timezone(datetime.timedelta(hours=TIMEZONE_OFFSET))
    return utc_now.astimezone(jst)
 
def pick_message(pool: list, guild_id: str) -> dict:
    if guild_id not in sent_today:
        sent_today[guild_id] = set()
    available = [m for m in pool if m["id"] not in sent_today[guild_id]]
    if not available:
        sent_today[guild_id].clear()
        available = pool
    msg = random.choice(available)
    sent_today[guild_id].add(msg["id"])
    return msg
 
def build_embed(msg: dict, label: str) -> discord.Embed:
    color_map = {
        "課題の分離": 0x7F77DD, "目的論": 0x1D9E75, "共同体感覚": 0x378ADD,
        "勇気づけ": 0xEF9F27, "承認欲求からの解放": 0xD4537E, "今ここに生きる": 0x5DCAA5,
        "劣等感の活用": 0xD85A30, "対等な人間関係": 0x639922,
        "ライフスタイルの選択": 0xBA7517, "不完全である勇気": 0x888780,
    }
    embed = discord.Embed(
        title=f"{label}のアドラーメッセージ",
        description=f"**{msg['text']}**",
        color=color_map.get(msg["category"], 0x7F77DD),
        timestamp=get_jst_now(),
    )
    embed.add_field(name=f"📖 {msg['category']}", value=msg["theme"], inline=False)
    embed.add_field(name="🌅 今日の問いかけ", value=msg["question"], inline=False)
    embed.set_footer(text="アドラー心理学ボット")
    return embed
 
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
 
@tasks.loop(minutes=1)
async def scheduler():
    now = get_jst_now()
    if now.second > 5:
        return
    is_morning = now.hour == 6 and now.minute == 0
    is_evening = now.hour == 18 and now.minute == 0
    if not (is_morning or is_evening):
        return
    for guild_id, channel_id in FIXED_CHANNELS.items():
        channel = client.get_channel(int(channel_id))
        if channel is None:
            print(f"チャンネルが見つかりません: {channel_id}")
            continue
        if is_morning:
            msg = pick_message(MORNING_MESSAGES, guild_id)
            await channel.send(embed=build_embed(msg, "🌄 朝"))
            print(f"[{now}] 朝送信 guild={guild_id}")
        else:
            msg = pick_message(EVENING_MESSAGES, guild_id)
            await channel.send(embed=build_embed(msg, "🌆 夕"))
            print(f"[{now}] 夕送信 guild={guild_id}")
 
@client.event
async def on_ready():
    print(f"✅ ログイン完了: {client.user}")
    print(f"📚 朝={len(MORNING_MESSAGES)}件 / 夕={len(EVENING_MESSAGES)}件")
    scheduler.start()
 
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    guild_id = str(message.guild.id) if message.guild else "dm"
 
    if message.content == "!adler" or message.content.startswith("!adler "):
        parts = message.content.split()
        pool = EVENING_MESSAGES if len(parts) > 1 and parts[1] == "evening" else MORNING_MESSAGES
        label = "🌆 夕" if pool is EVENING_MESSAGES else "🌄 朝"
        await message.channel.send(embed=build_embed(pick_message(pool, guild_id), label))
 
    elif message.content == "!adler-help":
        await message.channel.send(
            "**アドラーBotコマンド**\n"
            "`!adler` — 朝のメッセージを今すぐ表示\n"
            "`!adler evening` — 夕のメッセージを今すぐ表示\n"
            "`!adler-help` — このヘルプを表示\n\n"
            "⏰ 自動送信: 毎日 **6:00**（朝）と **18:00**（夕）JST"
        )
 
if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
 
