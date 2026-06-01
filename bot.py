"""
アドラー心理学 Discord Bot - 確実送信版
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

CHANNEL_IDS = [
    "1510674681525698754",
    "1510696478123888702",
]

MESSAGES_FILE = Path(__file__).parent / "messages.json"

with open(MESSAGES_FILE, encoding="utf-8") as f:
    ALL_MESSAGES = json.load(f)

MORNING_MESSAGES = [m for m in ALL_MESSAGES if m["time"] == "morning"]
EVENING_MESSAGES = [m for m in ALL_MESSAGES if m["time"] == "evening"]

sent_today: dict = {}
sent_keys: set = set()

def get_jst_now() -> datetime.datetime:
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    jst = datetime.timezone(datetime.timedelta(hours=TIMEZONE_OFFSET))
    return utc_now.astimezone(jst)

def pick_message(pool: list, channel_id: str) -> dict:
    if channel_id not in sent_today:
        sent_today[channel_id] = set()
    available = [m for m in pool if m["id"] not in sent_today[channel_id]]
    if not available:
        sent_today[channel_id].clear()
        available = pool
    msg = random.choice(available)
    sent_today[channel_id].add(msg["id"])
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

async def send_to_all(label: str, pool: list):
    for channel_id in CHANNEL_IDS:
        try:
            channel = client.get_channel(int(channel_id))
            if channel is None:
                print(f"チャンネルが見つかりません: {channel_id}")
                continue
            msg = pick_message(pool, channel_id)
            await channel.send(embed=build_embed(msg, label))
            print(f"? 送信完了 channel={channel_id} id={msg['id']}")
        except Exception as e:
            print(f"? 送信エラー channel={channel_id}: {e}")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@tasks.loop(seconds=30)
async def scheduler():
    now = get_jst_now()
    date_str = str(now.date())

    # 朝: 6:00?6:10の間に1回だけ送信
    morning_key = f"{date_str}-morning"
    if now.hour == 6 and now.minute <= 10 and morning_key not in sent_keys:
        sent_keys.add(morning_key)
        print(f"[{now}] 朝の送信開始")
        await send_to_all("　 朝", MORNING_MESSAGES)

    # 夕: 18:00?18:10の間に1回だけ送信
    evening_key = f"{date_str}-evening"
    if now.hour == 18 and now.minute <= 10 and evening_key not in sent_keys:
        sent_keys.add(evening_key)
        print(f"[{now}] 夕の送信開始")
        await send_to_all("　 夕", EVENING_MESSAGES)

@client.event
async def on_ready():
    print(f"? ログイン完了: {client.user}")
    print(f"　 朝={len(MORNING_MESSAGES)}件 / 夕={len(EVENING_MESSAGES)}件")
    scheduler.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    channel_id = str(message.channel.id)

    if message.content == "!adler" or message.content.startswith("!adler "):
        parts = message.content.split()
        pool = EVENING_MESSAGES if len(parts) > 1 and parts[1] == "evening" else MORNING_MESSAGES
        label = "　 夕" if pool is EVENING_MESSAGES else "　 朝"
        await message.channel.send(embed=build_embed(pick_message(pool, channel_id), label))

    elif message.content == "!adler-help":
        await message.channel.send(
            "**アドラーBotコマンド**\n"
            "`!adler` ? 朝のメッセージを今すぐ表示\n"
            "`!adler evening` ? 夕のメッセージを今すぐ表示\n"
            "`!adler-help` ? このヘルプを表示\n\n"
            "? 自動送信: 毎日 **6:00**（朝）と **18:00**（夕）JST"
        )

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
