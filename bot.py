"""
アドラー心理学 Discord Bot
毎朝6時・毎夕18時にメッセージを送信します
"""

import discord
from discord.ext import tasks
import json
import random
import datetime
import os
from pathlib import Path

# ─── 設定 ───────────────────────────────────────────────
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "ここにBotトークンを入力")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))  # 送信先チャンネルID
TIMEZONE_OFFSET = 9  # JST (UTC+9)

# メッセージファイルのパス
MESSAGES_FILE = Path(__file__).parent / "messages.json"

# ─── メッセージ読み込み ───────────────────────────────────
with open(MESSAGES_FILE, encoding="utf-8") as f:
    ALL_MESSAGES = json.load(f)

MORNING_MESSAGES = [m for m in ALL_MESSAGES if m["time"] == "morning"]
EVENING_MESSAGES = [m for m in ALL_MESSAGES if m["time"] == "evening"]

# 今日送ったIDを管理（重複防止）
sent_today: set = set()


def get_jst_now() -> datetime.datetime:
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    jst = datetime.timezone(datetime.timedelta(hours=TIMEZONE_OFFSET))
    return utc_now.astimezone(jst)


def pick_message(pool: list) -> dict:
    """未送信のメッセージからランダムに1件選ぶ"""
    available = [m for m in pool if m["id"] not in sent_today]
    if not available:
        sent_today.clear()
        available = pool
    msg = random.choice(available)
    sent_today.add(msg["id"])
    return msg


def build_embed(msg: dict, label: str) -> discord.Embed:
    """メッセージをDiscord Embedに変換"""
    color_map = {
        "課題の分離": 0x7F77DD,
        "目的論": 0x1D9E75,
        "共同体感覚": 0x378ADD,
        "勇気づけ": 0xEF9F27,
        "承認欲求からの解放": 0xD4537E,
        "今ここに生きる": 0x5DCAA5,
        "劣等感の活用": 0xD85A30,
        "対等な人間関係": 0x639922,
        "ライフスタイルの選択": 0xBA7517,
        "不完全である勇気": 0x888780,
    }
    color = color_map.get(msg["category"], 0x7F77DD)

    embed = discord.Embed(
        title=f"{label}のアドラーメッセージ",
        description=f"**{msg['text']}**",
        color=color,
        timestamp=get_jst_now(),
    )
    embed.add_field(name=f"📖 {msg['category']}", value=msg["theme"], inline=False)
    embed.add_field(name="🌅 今日の問いかけ", value=msg["question"], inline=False)
    embed.set_footer(text="アドラー心理学ボット | 新潟リカビリー")
    return embed


# ─── Discord クライアント ─────────────────────────────────
intents = discord.Intents.default()
client = discord.Client(intents=intents)


@tasks.loop(minutes=1)
async def scheduler():
    """毎分チェックして6時・18時にメッセージ送信"""
    now = get_jst_now()
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        return

    # 秒が0〜59秒の間に一度だけ送信（:00に合わせる）
    if now.second > 5:
        return

    if now.hour == 6 and now.minute == 0:
        msg = pick_message(MORNING_MESSAGES)
        embed = build_embed(msg, "🌄 朝")
        await channel.send(embed=embed)
        print(f"[{now}] 朝のメッセージ送信: ID={msg['id']} {msg['category']}")

    elif now.hour == 18 and now.minute == 0:
        msg = pick_message(EVENING_MESSAGES)
        embed = build_embed(msg, "🌆 夕")
        await channel.send(embed=embed)
        print(f"[{now}] 夕のメッセージ送信: ID={msg['id']} {msg['category']}")


@client.event
async def on_ready():
    print(f"✅ ログイン完了: {client.user} (ID: {client.user.id})")
    print(f"📨 送信先チャンネルID: {CHANNEL_ID}")
    print(f"📚 メッセージ数: 朝={len(MORNING_MESSAGES)}件 / 夕={len(EVENING_MESSAGES)}件")
    scheduler.start()


@client.event
async def on_message(message):
    """コマンド対応"""
    if message.author == client.user:
        return

    # !adler でその場でメッセージ送信（テスト用）
    if message.content.startswith("!adler"):
        parts = message.content.split()
        time_pref = parts[1] if len(parts) > 1 else "morning"
        pool = EVENING_MESSAGES if time_pref == "evening" else MORNING_MESSAGES
        msg = pick_message(pool)
        label = "🌆 夕" if time_pref == "evening" else "🌄 朝"
        embed = build_embed(msg, label)
        await message.channel.send(embed=embed)

    # !adler-help でヘルプ表示
    elif message.content.startswith("!adler-help"):
        await message.channel.send(
            "**アドラーBotコマンド**\n"
            "`!adler` — 朝のメッセージを今すぐ表示\n"
            "`!adler evening` — 夕のメッセージを今すぐ表示\n"
            "`!adler-help` — このヘルプを表示\n\n"
            "⏰ 自動送信: 毎日 **6:00**（朝）と **18:00**（夕）に送信します。"
        )


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
