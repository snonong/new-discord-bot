import discord
from discord.ext import commands
from discord import app_commands
from keep_alive import keep_alive
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---------- 분배 명령어 ----------
class DistributionView(discord.ui.View):
    def __init__(self, labels: list[str], author_id: int, title: str):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.title = title
        self.selected = set()
        self.total = set(labels)
        for label in labels:
            self.add_item(DistributionButton(label, self))

    def is_complete(self):
        return self.selected == self.total

    def get_embed(self, username: str):
        done = self.is_complete()
        color = discord.Color.green() if done else discord.Color.gold()
        title_text = f"💰 **{self.title}**" + ("" if done else " 분배 시작!")
        desc = "분배 완료! 👍" if done else f"**{username}** 님에게 분배금 받아 가세요 😍"
        return discord.Embed(title=title_text, description=desc, color=color)

class DistributionButton(discord.ui.Button):
    def __init__(self, label: str, parent: DistributionView):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.parent_view = parent

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.author_id:
            await interaction.response.send_message("❌ 명령어 작성자만 클릭할 수 있어요.", ephemeral=True)
            return
        self.disabled = True
        self.style = discord.ButtonStyle.success
        self.label = f"✅ {self.label}"
        self.parent_view.selected.add(self.label.replace("✅ ", ""))
        embed = self.parent_view.get_embed(interaction.user.display_name)
        await interaction.message.edit(embed=embed, view=self.parent_view)
        await interaction.response.defer()

@tree.command(name="분배", description="분배명과 닉네임을 입력하면 버튼이 생성됩니다.")
@app_commands.describe(분배명="예: 상금 분배", 닉네임="띄어쓰기로 구분된 이름들")
async def 분배(interaction: discord.Interaction, 분배명: str, 닉네임: str):
    labels = 닉네임.strip().split()
    if not labels:
        await interaction.response.send_message("❗ 이름을 하나 이상 입력해주세요.", ephemeral=True)
        return
    view = DistributionView(labels, interaction.user.id, 분배명)
    embed = view.get_embed(interaction.user.display_name)
    await interaction.response.send_message(embed=embed, view=view)

# ---------- 파티모집 명령어 ----------
class PartyView(discord.ui.View):
    def __init__(self, author_id: int, roles: list[str], max_participants: int, thread: discord.Thread, title: str, time: str):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.max_participants = max_participants
        self.thread = thread
        self.title = title
        self.time = time
        self.participants = {role: [] for role in roles}
        self.user_roles = {}

        for role in roles:
            self.add_item(PartyButton(role, self))

        self.add_item(FinishButton(self))

    def get_embed(self, done=False):
        desc = f"출발 시간: {self.time}\n\n"
        counted_users = set()

        for role, users in self.participants.items():
            line = f"{role}:  "
            mentions = []
            for uid in users:
                swaps = self.user_roles.get(uid, set()) - {role}
                mention = f"<@{uid}>"
                if swaps:
                    mention += f"({','.join(swaps)}O)"
                mentions.append(mention)
                counted_users.add(uid)
            desc += line + " ".join(mentions) + "\n"

        if done:
            desc += "\n\n모집 완료! 🎉"

        color = discord.Color.blue() if done else discord.Color.red()
        return discord.Embed(title=f"🔥 {self.title} 파티 모집!", description=desc, color=color)

class PartyButton(discord.ui.Button):
    def __init__(self, role: str, parent: PartyView):
        super().__init__(label=role, style=discord.ButtonStyle.primary)
        self.role = role
        self.parent_view = parent

    async def callback(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if uid not in self.parent_view.user_roles:
            self.parent_view.user_roles[uid] = set()
        if uid not in self.parent_view.participants[self.role]:
            self.parent_view.participants[self.role].append(uid)
            self.parent_view.user_roles[uid].add(self.role)

        embed = self.parent_view.get_embed()
        await interaction.message.edit(embed=embed, view=self.parent_view)
        await self.parent_view.thread.add_user(interaction.user)
        await interaction.response.defer()

class FinishButton(discord.ui.Button):
    def __init__(self, parent: PartyView):
        super().__init__(label="모집 완료", style=discord.ButtonStyle.success)
        self.parent_view = parent

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.author_id:
            await interaction.response.send_message("이 버튼은 모집자만 사용할 수 있습니다.", ephemeral=True)
            return
        embed = self.parent_view.get_embed(done=True)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.defer()

@tree.command(name="파티모집", description="던전 파티를 모집합니다.")
@app_commands.describe(던전명="던전 이름", 출발시간="출발 시간", 인원="최대 인원 수")
async def 파티모집(interaction: discord.Interaction, 던전명: str, 출발시간: str, 인원: int):
    thread = await interaction.channel.create_thread(name=던전명, type=discord.ChannelType.public_thread)
    view = PartyView(interaction.user.id, ["세가", "세바", "딜러"], 인원, thread, 던전명, 출발시간)
    embed = view.get_embed()
    await interaction.response.send_message(embed=embed, view=view)
    await thread.send(f"{interaction.user.mention} 님이 파티를 모집했습니다!")

# ---------- 봇 실행 ----------
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ 봇 실행됨: {bot.user}")

# keep_alive 웹 서버 실행
keep_alive()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN 환경변수가 설정되지 않았습니다.")
bot.run(TOKEN)
