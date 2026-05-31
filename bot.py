"""
アドラー心理学 Discord Bot - 複数サーバー対応版
各サーバーで !adler-setup #チャンネル名 で送信先を設定できます
"""

import discord
from discord.ext import tasks
import json
import random
import datetime
import os
from pathlib import Path

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "ここにBotトークンを入力")
TIMEZONE_OFFSET = 9

MESSAGES_FILE = Path(__file__).parent / "messages.json"
SETTINGS_FILE = Path(__file__).parent / "server_settings.json"

with open(MESSAGES_FILE, encoding="utf-8") as f:
    ALL_MESSAGES = json.load(f)

MORNING_MESSAGES = [m for m in ALL_MESSAGES if m["time"] == "morning"]
EVENING_MESSAGES = [m for m in ALL_MESSAGES if m["time"] == "evening"]

sent_today: dict = {}

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

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
    embed.add_field(name=f"　 {msg['category']}", value=msg["theme"], inline=False)
    embed.add_field(name="　 今日の問いかけ", value=msg["question"], inline=False)
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
    settings = load_settings()
    for guild_id, channel_id in settings.items():
        channel = client.get_channel(int(channel_id))
        if channel is None:
            continue
        if is_morning:
            msg = pick_message(MORNING_MESSAGES, guild_id)
            await channel.send(embed=build_embed(msg, "　 朝"))
        else:
            msg = pick_message(EVENING_MESSAGES, guild_id)
            await channel.send(embed=build_embed(msg, "　 夕"))

@client.event
async def on_ready():
    print(f"? ログイン完了: {client.user}")
    print(f"　 参加サーバー数: {len(client.guilds)}")
    scheduler.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    guild_id = str(message.guild.id) if message.guild else "dm"

    if message.content.startswith("!adler-setup"):
        if not message.author.guild_permissions.manage_channels:
            await message.channel.send("? チャンネル管理権限が必要です。")
            return
        ch = message.channel_mentions[0] if message.channel_mentions else message.channel
        settings = load_settings()
        settings[guild_id] = str(ch.id)
        save_settings(settings)
        await message.channel.send(f"? **{ch.name}** を送信チャンネルに設定しました！\n毎朝6時・毎夕18時にアドラーメッセージを送ります。")

    elif message.content.startswith("!adler-stop"):
        if not message.author.guild_permissions.manage_channels:
            await message.channel.send("? チャンネル管理権限が必要です。")
            return
        settings = load_settings()
        settings.pop(guild_id, None)
        save_settings(settings)
        await message.channel.send("? このサーバーへの自動送信を停止しました。")

    elif message.content.startswith("!adler"):
        parts = message.content.split()
        pool = EVENING_MESSAGES if len(parts) > 1 and parts[1] == "evening" else MORNING_MESSAGES
        label = "　 夕" if pool is EVENING_MESSAGES else "　 朝"
        await message.channel.send(embed=build_embed(pick_message(pool, guild_id), label))

    elif message.content.startswith("!adler-help"):
        await message.channel.send(
            "**アドラーBotコマンド**\n"
            "`!adler-setup` ? このチャンネルを送信先に設定\n"
            "`!adler-setup #チャンネル名` ? 指定チャンネルを送信先に設定\n"
            "`!adler-stop` ? 自動送信を停止\n"
            "`!adler` ? 朝のメッセージを今すぐ表示\n"
            "`!adler evening` ? 夕のメッセージを今すぐ表示\n"
            "`!adler-help` ? このヘルプを表示\n\n"
            "? 自動送信: 毎日 **6:00**（朝）と **18:00**（夕）JST"
        )

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)

