# main.py (루트 엔트리 파일)
import os
import discord
from discord.ext import commands
from discord import app_commands
from keep_alive import keep_alive
from handlers.party import register_party_command
from handlers.distribute import register_distribute_command

TOKEN = os.environ["DISCORD_TOKEN"]
TEST_GUILD_ID = discord.Object(id=int(os.environ["TEST_GUILD_ID"]))
LIVE_GUILD_ID = discord.Object(id=int(os.environ["LIVE_GUILD_ID"]))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------- 명령어 등록 --------------------------
@bot.event
async def on_ready():
    try:
        await bot.tree.clear_commands(guild=TEST_GUILD_ID)
        await bot.tree.sync(guild=TEST_GUILD_ID)
        print("✅ 테스트 서버 명령어 초기화 및 재등록 완료")

        await bot.tree.clear_commands(guild=LIVE_GUILD_ID)
        await bot.tree.sync(guild=LIVE_GUILD_ID)
        print("✅ 운영 서버 명령어 초기화 및 재등록 완료")

    except Exception as e:
        print(f"❌ 명령어 등록 중 오류: {e}")

    print(f"🤖 봇 로그인 완료: {bot.user}")

    await register_party_command(bot)
    await register_distribute_command(bot)

keep_alive()
bot.run(TOKEN)
