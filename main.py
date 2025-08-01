import discord
from discord.ext import commands
from discord import app_commands

# 웹 서버를 켜서 24시간 유지
from keep_alive import keep_alive
keep_alive()

import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ===============================
# 🔹 분배 명령어 관련
# ===============================
class DistributionView(discord.ui.View):
    def __init__(self, labels, author_id, title):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.title = title
        self.selected = set()
        self.total = set(labels)
        for label in labels:
            self.add_item(DistributionButton(label, self))

    def is_complete(self):
        return self.selected == self.total

    def get_embed(self, username):
        done = self.is_complete()
        color = discord.Color.green() if done else discord.Color.gold()
        title_text = f"💰 **{self.title}**" + ("" if done else " 분배 시작!")
        desc = "분배 완료! 👍" if done else f"**{username}** 님에게 분배금 받아 가세요 😍"
        return discord.Embed(title=title_text, description=desc, color=color)

class DistributionButton(discord.ui.Button):
    def __init__(self, label, parent_view):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction):
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

# ===============================
# 🔹 파티모집 명령어 관련
# ===============================
class PartyView(discord.ui.View):
    def __init__(self, author_id, roles, max_participants, thread, title, time, description, channel_emoji):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.max_participants = max_participants
        self.thread = thread
        self.title = title
        self.time = time
        self.description = description
        self.emoji = channel_emoji
        self.participants = {role: [] for role in roles}
        self.user_roles = {}

        for idx, role in enumerate(roles):
            style = {
                "세가": discord.ButtonStyle.primary,
                "세바": discord.ButtonStyle.success,
                "딜러": discord.ButtonStyle.danger
            }.get(role, discord.ButtonStyle.secondary)
            self.add_item(PartyButton(role, self, style=style, row=0))

        self.add_item(FinishButton(self, row=1))

    def get_embed(self, done=False):
        unique_users = set()
        desc = f"출발 시간: {self.time}\n"
        desc += f"인원: {len(set.union(*[set(users) for users in self.participants.values()]))} / {self.max_participants}\n"
        desc += f"설명: {self.description}\n\n"

        for role, users in self.participants.items():
            mentions = []
            for uid in users:
                swaps = self.user_roles.get(uid, set()) - {role}
                mention = f"<@{uid}>"
                if swaps:
                    mention += f"({','.join(swaps)}O)"
                mentions.append(mention)
                unique_users.add(uid)
            desc += f"{role}:  " + " ".join(mentions) + "\n"

        if done:
            desc += "\n모집 완료! 🎉"

        color = discord.Color.blue() if done else discord.Color.red()
        return discord.Embed(title=f"{self.emoji} {self.title} 파티 모집!", description=desc, color=color)

class PartyButton(discord.ui.Button):
    def __init__(self, role, parent_view, style=discord.ButtonStyle.primary, row=0):
        super().__init__(label=role, style=style, row=row)
        self.role = role
        self.parent_view = parent_view

    async def callback(self, interaction):
        uid = interaction.user.id
        removed = False

        if uid in self.parent_view.participants[self.role]:
            self.parent_view.participants[self.role].remove(uid)
            self.parent_view.user_roles[uid].discard(self.role)
            removed = True
        else:
            self.parent_view.participants[self.role].append(uid)
            self.parent_view.user_roles.setdefault(uid, set()).add(self.role)

        embed = self.parent_view.get_embed()
        await interaction.message.edit(embed=embed, view=self.parent_view)

        if removed:
            try:
                await self.parent_view.thread.remove_user(interaction.user)
            except:
                pass
        else:
            await self.parent_view.thread.add_user(interaction.user)

        await interaction.response.defer()

class FinishButton(discord.ui.Button):
    def __init__(self, parent, row=1):
        super().__init__(label="모집 완료", style=discord.ButtonStyle.secondary, row=row)
        self.parent_view = parent

    async def callback(self, interaction):
        if interaction.user.id != self.parent_view.author_id:
            await interaction.response.send_message("모집자만 사용할 수 있습니다.", ephemeral=True)
            return
        embed = self.parent_view.get_embed(done=True)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.defer()

# 채널 이름에 따른 이모지 매핑
channel_emojis = {
    "자유모집": "🔥",
    "크롬바스-모집": "💀",
    "글렌베르나-모집": "❄️",
    "브리레흐-모집": "🍕"
}

@tree.command(name="파티모집", description="던전 파티를 모집합니다.")
@app_commands.describe(던전명="던전 이름", 출발시간="출발 시간", 인원="최대 인원 수", 설명="파티 설명")
async def 파티모집(interaction: discord.Interaction, 던전명: str, 출발시간: str, 인원: int, 설명: str):
    channel_name = interaction.channel.name
    emoji = channel_emojis.get(channel_name, "🔥")
    thread = await interaction.channel.create_thread(name=던전명, type=discord.ChannelType.public_thread)
    view = PartyView(interaction.user.id, ["세가", "세바", "딜러"], 인원, thread, 던전명, 출발시간, 설명, emoji)
    embed = view.get_embed()
    await interaction.response.send_message(content="@everyone", embed=embed, view=view)
    await thread.send(f"{interaction.user.mention} 님이 파티를 모집했습니다!")

# ===============================
# 🔹 봇 실행
# ===============================
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ 봇 실행됨: {bot.user}")

bot.run(os.getenv("TOKEN"))
