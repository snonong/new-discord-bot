import os
import discord
from discord.ext import commands
from discord import app_commands, Interaction, TextChannel
from keep_alive import keep_alive

TOKEN = os.environ["DISCORD_TOKEN"]
TEST_GUILD_ID = discord.Object(id=int(os.environ["TEST_GUILD_ID"]))
LIVE_GUILD_ID = discord.Object(id=int(os.environ["LIVE_GUILD_ID"]))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------- /분배 명령어 --------------------------
class NameButton(discord.ui.Button):
    def __init__(self, label, author_id):
        super().__init__(label=label, style=discord.ButtonStyle.success)
        self.author_id = author_id

    async def callback(self, interaction: Interaction):
        view = self.view
        if interaction.user in view.clicked_users:
            await interaction.response.send_message("이미 클릭했습니다!", ephemeral=True)
            return

        view.clicked_users.append(interaction.user)
        self.disabled = True
        await interaction.response.edit_message(view=view)

        if len(view.clicked_users) == len(view.children):
            embed = view.embed
            embed.color = discord.Color.green()
            embed.title = f"💰 {view.title}"
            embed.description = "분배 완료! 👍"
            await interaction.message.edit(embed=embed)

class MultiSelectButton(discord.ui.View):
    def __init__(self, labels, author_id, title):
        super().__init__(timeout=None)
        self.clicked_users = []
        self.author_id = author_id
        self.title = title
        self.embed = discord.Embed(
            title=f"💰 {title} 분배 시작!",
            description=f"{title} 님에게 분배금 받아 가세요 😍",
            color=discord.Color.gold()
        )
        for label in labels:
            self.add_item(NameButton(label=label, author_id=author_id))

@bot.tree.command(name="분배", description="닉네임별 분배 버튼을 생성합니다.")
@app_commands.describe(
    제목="분배 제목",
    닉네임="닉네임 목록 (띄어쓰기 구분)"
)
async def 분배(interaction: Interaction, 제목: str, 닉네임: str):
    names = 닉네임.split()
    view = MultiSelectButton(labels=names, author_id=interaction.user.id, title=제목)
    await interaction.response.send_message(embed=view.embed, view=view)

# -------------------------- /파티 명령어 --------------------------
class RoleButton(discord.ui.Button):
    def __init__(self, role: str, author_id: int):
        color_map = {"세가": discord.ButtonStyle.primary, "세바": discord.ButtonStyle.success, "딜러": discord.ButtonStyle.danger}
        style = color_map.get(role, discord.ButtonStyle.secondary)
        super().__init__(label=role, style=style)
        self.role = role
        self.author_id = author_id
        self.clicked_users = []

    async def callback(self, interaction: Interaction):
        if interaction.user in self.clicked_users:
            await interaction.response.send_message("이미 선택하셨습니다!", ephemeral=True)
            return

        self.clicked_users.append(interaction.user)
        view = self.view
        embed = view.embed

        view.user_roles.setdefault(interaction.user, []).append(self.role)
        view.unique_users.add(interaction.user)

        embed.description = view.generate_description()
        await interaction.response.edit_message(embed=embed, view=view)

class CompleteButton(discord.ui.Button):
    def __init__(self, author_id):
        super().__init__(label="모집 완료", style=discord.ButtonStyle.secondary)
        self.author_id = author_id

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("모집자만 완료할 수 있습니다!", ephemeral=True)
            return

        view = self.view
        embed = view.embed
        embed.color = discord.Color.blue()
        embed.description += "\n\n모집 완료!"
        await interaction.response.edit_message(embed=embed, view=view)
        for child in view.children:
            child.disabled = True
        await interaction.message.edit(view=view)

class PartyView(discord.ui.View):
    def __init__(self, interaction: Interaction, roles, party_name, time, capacity, description):
        super().__init__(timeout=None)
        self.author_id = interaction.user.id
        self.roles = roles
        self.party_name = party_name
        self.time = time
        self.capacity = capacity
        self.description_text = description
        self.unique_users = set()
        self.user_roles = {}
        self.channel = interaction.channel

        icon = "💀"
        if "글렌베르나-모집" in self.channel.name:
            icon = "❄️"
        elif "브리레흐-모집" in self.channel.name:
            icon = "🍕"
        elif "자유모집" in self.channel.name:
            icon = "🔥"

        self.embed = discord.Embed(
            title=f"{icon} {party_name} 파티 모집!",
            color=discord.Color.red()
        )
        for role in roles:
            self.add_item(RoleButton(role, self.author_id))
        self.add_item(CompleteButton(self.author_id))

    def generate_description(self):
        role_lines = {role: [] for role in self.roles}
        for button in self.children:
            if isinstance(button, RoleButton):
                for u in button.clicked_users:
                    other_roles = [r for r in self.user_roles[u] if r != button.role]
                    if other_roles:
                        role_lines[button.role].append(f"{u.mention}({', '.join(other_roles)} O)")
                    else:
                        role_lines[button.role].append(f"{u.mention}")

        lines = [
            f"**출발 시간**: {self.time}",
            f"**인원**: {len(self.unique_users)} / {self.capacity}",
            f"**설명**: {self.description_text}",
            "",
            "•❅───────────✧❅✦❅✧───────────❅•",
            "세가       세바       딜러"
        ]

        max_rows = max(len(role_lines[r]) for r in self.roles)
        for i in range(max_rows):
            row = []
            for r in self.roles:
                row.append(role_lines[r][i] if i < len(role_lines[r]) else " ")
            lines.append("   ".join(row))

        lines.append("•❅───────────✧❅✦❅✧───────────❅•")
        return "\n".join(lines)

@bot.tree.command(name="파티", description="던전 파티를 모집합니다.")
@app_commands.describe(
    던전명="던전 이름",
    출발시간="예: 오후 9시",
    인원="모집 인원",
    설명="추가 설명"
)
async def 파티(interaction: Interaction, 던전명: str, 출발시간: str, 인원: int, 설명: str):
    view = PartyView(
        interaction=interaction,
        roles=["세가", "세바", "딜러"],
        party_name=던전명,
        time=출발시간,
        capacity=인원,
        description=설명
    )
    view.embed.description = view.generate_description()
    await interaction.response.send_message(content="@everyone", embed=view.embed, view=view)
    thread = await interaction.channel.create_thread(name=f"{던전명} 파티 모집", type=discord.ChannelType.public_thread)
    await thread.add_user(interaction.user)

# -------------------------- 배포 --------------------------
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

keep_alive()
bot.run(TOKEN)
