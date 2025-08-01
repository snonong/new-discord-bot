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
    buttons = [discord.ui.Button(label=name, style=discord.ButtonStyle.success, custom_id=name) for name in names]

    class 분배View(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.clicked = set()
            self.msg = None  # 메시지를 여기에 저장

        async def interaction_check(self, i: discord.Interaction) -> bool:
            return True

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True
            if self.msg:
                await self.msg.edit(view=self)

        async def update(self):
            if len(self.clicked) == len(buttons):
                embed = discord.Embed(title=f"💰 {제목}", description="분배 완료! 👍", color=discord.Color.green())
            else:
                embed = discord.Embed(title=f"💰 {제목} 분배 시작!", description="닉네임 님에게 분배금 받아 가세요 😍", color=discord.Color.gold())
            if self.msg:
                await self.msg.edit(embed=embed, view=self)

    view = 분배View()

    for btn in buttons:
        async def callback(interaction: discord.Interaction, name=btn.label, button=btn):
            if name not in view.clicked:
                view.clicked.add(name)
            button.disabled = True
            button.emoji = "✅"
            await view.update()
        btn.callback = callback
        view.add_item(btn)

    embed = discord.Embed(title=f"💰 {제목} 분배 시작!", description="닉네임 님에게 분배금 받아 가세요 😍", color=discord.Color.gold())
    msg = await interaction.followup.send(embed=embed, view=view)
    view.msg = msg  # 메시지를 저장



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

    세가 = set()
    세바 = set()
    딜러 = set()
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
            color = discord.Color.red() if not 완료됨 else discord.Color.blue()
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

        async def update(self, interaction: discord.Interaction):
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.custom_id != "done":
                    item.disabled = 완료됨
            await interaction.edit_original_response(embed=self.get_embed(), view=self)

        @discord.ui.button(label="세가", style=discord.ButtonStyle.primary, custom_id="세가")
        async def 세가버튼(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user in 세가:
                세가.remove(interaction.user)
            else:
                세가.add(interaction.user)
            await self.update(interaction)

        @discord.ui.button(label="세바", style=discord.ButtonStyle.success, custom_id="세바")
        async def 세바버튼(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user in 세바:
                세바.remove(interaction.user)
            else:
                세바.add(interaction.user)
            await self.update(interaction)

        @discord.ui.button(label="딜러", style=discord.ButtonStyle.danger, custom_id="딜러")
        async def 딜러버튼(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user in 딜러:
                딜러.remove(interaction.user)
            else:
                딜러.add(interaction.user)
            await self.update(interaction)

        @discord.ui.button(label="모집 완료", style=discord.ButtonStyle.secondary, custom_id="done")
        async def 완료버튼(self, interaction: discord.Interaction, button: discord.ui.Button):
            nonlocal 완료됨
            if interaction.user == 모집자:
                완료됨 = True
                await self.update(interaction)
            else:
                await interaction.response.send_message("모집자만 완료할 수 있어요!", ephemeral=True)

    view = 모집View()
    embed = view.get_embed()
    msg = await interaction.followup.send(content="@everyone", embed=embed, view=view)
    thread = await msg.create_thread(name=f"{던전명} 파티 모집 스레드")

@bot.event
async def on_ready():
    await tree.sync()
    print(f"{bot.user} is now running!")

TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
