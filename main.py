import discord
from discord.ext import commands
from discord import app_commands
from keep_alive import keep_alive
import os

keep_alive()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ------------------ /분배 ------------------
@tree.command(name="분배", description="분배 버튼을 생성합니다.")
@app_commands.describe(제목="분배 제목", 닉네임="띄어쓰기로 분리된 닉네임 목록")
async def 분배(interaction: discord.Interaction, 제목: str, 닉네임: str):
    await interaction.response.defer()
    names = 닉네임.strip().split()

    class 분배View(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.clicked = set()
            self.msg = None
            self.buttons = []
            for name in names:
                btn = discord.ui.Button(label=name, style=discord.ButtonStyle.success)
                btn.callback = self.make_callback(name, btn)
                self.add_item(btn)
                self.buttons.append(btn)

        def make_callback(self, name, button):
            async def callback(i: discord.Interaction):
                if name not in self.clicked:
                    self.clicked.add(name)
                    button.disabled = True
                    button.emoji = "✅"
                    await self.update(i)
            return callback

        async def update(self, i: discord.Interaction):
            if len(self.clicked) == len(names):
                embed = discord.Embed(title=f"💰 {제목}", description="분배 완료! 👍", color=discord.Color.green())
            else:
                embed = discord.Embed(title=f"💰 {제목} 분배 시작!", description=f"**{interaction.user.display_name}** 님에게 분배금 받아 가세요 😍", color=discord.Color.gold())
            if self.msg:
                await self.msg.edit(embed=embed, view=self)

    view = 분배View()
    embed = discord.Embed(title=f"💰 {제목} 분배 시작!", description=f"**{interaction.user.display_name}** 님에게 분배금 받아 가세요 😍", color=discord.Color.gold())
    msg = await interaction.followup.send(embed=embed, view=view)
    view.msg = msg

# ------------------ /파티 ------------------

EMOJI_MAP = {
    "자유모집": "🔥",
    "크롬바스-모집": "💀",
    "글렌베르나-모집": "❄️",
    "브리레흐-모집": "🍕"
}

@tree.command(name="파티", description="파티 모집 임베드를 생성합니다.")
@app_commands.describe(던전명="던전 이름", 출발시간="출발 시간", 인원="모집 인원 수", 설명="파티 설명 문구")
async def 파티(interaction: discord.Interaction, 던전명: str, 출발시간: str, 인원: int, 설명: str):
    await interaction.response.defer()

    세가, 세바, 딜러 = set(), set(), set()
    모집자 = interaction.user
    완료됨 = False

    class 모집View(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        def get_embed(self):
            def format_user(user_set, role_name):
                parts = []
                for u in user_set:
                    other_roles = []
                    if u in 세가 and role_name != "세가":
                        other_roles.append("세가")
                    if u in 세바 and role_name != "세바":
                        other_roles.append("세바")
                    if u in 딜러 and role_name != "딜러":
                        other_roles.append("딜러")
                    label = f"{u.mention}"
                    if other_roles:
                        label += f"({', '.join(other_roles)}O)"
                    parts.append(label)
                return " ".join(parts) or "-"

            참여인원 = len(set(세가 | 세바 | 딜러))
            이모지 = EMOJI_MAP.get(interaction.channel.name, "🔥")
            color = discord.Color.blue() if 완료됨 else discord.Color.red()
            description = (
                f"출발 시간: {출발시간}\n"
                f"인원: {참여인원} / {인원}\n"
                f"설명: {설명}\n\n"
                f"세가: {format_user(세가, '세가')}\n"
                f"세바: {format_user(세바, '세바')}\n"
                f"딜러: {format_user(딜러, '딜러')}"
            )
            if 완료됨:
                description += "\n\n모집 완료!"
            return discord.Embed(title=f"{이모지} {던전명} 파티 모집!", description=description, color=color)

        async def update(self, i: discord.Interaction):
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.custom_id != "done":
                    item.disabled = 완료됨
            await i.response.edit_message(embed=self.get_embed(), view=self)

        @discord.ui.button(label="세가", style=discord.ButtonStyle.primary, custom_id="세가")
        async def 세가버튼(self, i: discord.Interaction, button: discord.ui.Button):
            if i.user in 세가:
                세가.remove(i.user)
            else:
                세가.add(i.user)
            await self.update(i)

        @discord.ui.button(label="세바", style=discord.ButtonStyle.success, custom_id="세바")
        async def 세바버튼(self, i: discord.Interaction, button: discord.ui.Button):
            if i.user in 세바:
                세바.remove(i.user)
            else:
                세바.add(i.user)
            await self.update(i)

        @discord.ui.button(label="딜러", style=discord.ButtonStyle.danger, custom_id="딜러")
        async def 딜러버튼(self, i: discord.Interaction, button: discord.ui.Button):
            if i.user in 딜러:
                딜러.remove(i.user)
            else:
                딜러.add(i.user)
            await self.update(i)

        @discord.ui.button(label="모집 완료", style=discord.ButtonStyle.secondary, custom_id="done")
        async def 완료버튼(self, i: discord.Interaction, button: discord.ui.Button):
            nonlocal 완료됨
            if i.user == 모집자:
                완료됨 = True
                await self.update(i)
            else:
                await i.response.send_message("모집자만 완료할 수 있어요!", ephemeral=True)

    view = 모집View()
    embed = view.get_embed()
    msg = await interaction.followup.send(content="@everyone", embed=embed, view=view)
    await msg.create_thread(name=f"{던전명} 파티 모집 스레드")

# ------------------ 봇 실행 ------------------

@bot.event
async def on_ready():
    try:
        synced = await tree.sync()
        print(f"📝 {len(synced)}개의 명령어를 동기화했습니다.")
    except Exception as e:
        print(f"❌ 명령어 동기화 실패: {e}")
    print(f"✅ {bot.user} 봇이 온라인 상태입니다.")

TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
