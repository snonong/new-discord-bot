import os
import discord
from discord.ext import commands
from discord import app_commands, Interaction
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

        # 모든 버튼 클릭 완료 시 상태 업데이트
        if len(view.clicked_users) == len(view.children):
            embed = view.embed
            embed.color = discord.Color.green()
            embed.title = f"💰 {view.title}"
            embed.description = f"분배 완료! 👍"
            await interaction.message.edit(embed=embed)

class MultiSelectButton(discord.ui.View):
    def __init__(self, labels, author_id, title):
        super().__init__(timeout=None)
        self.clicked_users = []
        self.author_id = author_id
        self.embed = discord.Embed(
            title=f"💰 {title} 분배 시작!",
            description=f"{title} 님에게 분배금 받아 가세요 😍",
            color=discord.Color.gold()
        )
        self.title = title

        for label in labels:
            self.add_item(NameButton(label=label, author_id=author_id))

@bot.tree.command(name="분배", description="닉네임별 분배 버튼을 생성합니다.")
@app_commands.describe(제목="분배 제목", 닉네임="닉네임들 (띄어쓰기 구분)")
async def 분배(interaction: Interaction, 제목: str, 닉네임: str):
    names = 닉네임.split()
    view = MultiSelectButton(labels=names, author_id=interaction.user.id, title=interaction.user.display_name)
    await interaction.response.send_message(embed=view.embed, view=view)

# -------------------------- /파티 명령어 --------------------------
class RoleButton(discord.ui.Button):
    def __init__(self, role: str, author_id: int):
        super().__init__(label=role, style=discord.ButtonStyle.primary)
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

        view.unique_users.add(interaction.user)

        embed.description = view.generate_description()
        await interaction.response.edit_message(embed=embed, view=view)

class PartyView(discord.ui.View):
    def __init__(self, author_id, roles, party_name, time, capacity, description):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.roles = roles
        self.party_name = party_name
        self.time = time
        self.capacity = capacity
        self.description_text = description
        self.unique_users = set()
        self.embed = discord.Embed(
            title=f"🔥 {party_name} 파티 모집!",
            color=discord.Color.red()
        )
        for role in roles:
            self.add_item(RoleButton(role, author_id))

    def generate_description(self):
        desc = f"출발 시간: {self.time}\n"
        desc += f"인원: {len(self.unique_users)} / {self.capacity}\n"
        desc += f"설명: {self.description_text}\n"
        for button in self.children:
            if isinstance(button, RoleButton):
                mentions = ' '.join(f"{u.mention}" for u in button.clicked_users)
                desc += f"{button.role}: {mentions or '없음'}\n"
        if len(self.unique_users) >= self.capacity:
            desc += "\n모집 완료!"
            self.embed.color = discord.Color.blue()
        return desc

@bot.tree.command(name="파티", description="던전 파티를 모집합니다.")
@app_commands.describe(던전명="던전 이름", 출발시간="예: 오후 9시", 인원="모집 인원", 설명="추가 설명")
async def 파티(interaction: Interaction, 던전명: str, 출발시간: str, 인원: int, 설명: str):
    view = PartyView(
        author_id=interaction.user.id,
        roles=["세가", "세바", "딜러"],
        party_name=던전명,
        time=출발시간,
        capacity=인원,
        description=설명
    )
    view.embed.description = view.generate_description()
    await interaction.response.send_message(embed=view.embed, view=view)

# -------------------------- 봇 실행 --------------------------
@bot.event
async def on_ready():
    try:
        await bot.tree.sync(guild=TEST_GUILD_ID)
        print("✅ 테스트 서버 명령어 등록 완료")

        await bot.tree.sync(guild=LIVE_GUILD_ID)
        print("✅ 운영 서버 명령어 등록 완료")

    except Exception as e:
        print(f"❌ 명령어 등록 중 오류 발생: {e}")

    print(f"🤖 봇 로그인 완료: {bot.user}")


keep_alive()
bot.run(TOKEN)
