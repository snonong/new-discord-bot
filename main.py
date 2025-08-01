import discord
from discord.ext import commands
from discord import app_commands
import os
from keep_alive import keep_alive
from flask import Flask

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# GUILD_ID = discord.Object(id=YOUR_GUILD_ID)

# 🧩 /분배 명령어
class MultiSelectButton(discord.ui.View):
    def __init__(self, labels, author_id, title):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.labels = labels
        self.title = title
        self.clicked = set()
        self.buttons = []
        for label in labels:
            button = NameButton(label=label, author_id=author_id, view=self)
            self.add_item(button)
            self.buttons.append(button)

    async def update_message(self, interaction):
        if all(b.disabled for b in self.buttons):
            embed = discord.Embed(
                title=f"💰 {self.title}",
                description="분배 완료! 👍",
                color=discord.Color.green()
            )
            await interaction.message.edit(embed=embed, view=self)

class NameButton(discord.ui.Button):
    def __init__(self, label, author_id, view):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.original_label = label
        self.author_id = author_id
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ 명령어 작성자만 클릭할 수 있어요.", ephemeral=True)
            return

        self.disabled = True
        self.style = discord.ButtonStyle.success
        self.label = f"✅ {self.original_label}"
        await interaction.response.edit_message(view=self.view)
        await self.view.update_message(interaction)

@tree.command(name="분배", description="분배명과 닉네임을 입력하면 버튼이 생성됩니다.")
@app_commands.describe(분배명="예: 야식비, 회의비 등", 닉네임="띄어쓰기로 이름을 입력 (예: 철수 영희 민수)")
async def 분배(interaction: discord.Interaction, 분배명: str, 닉네임: str):
    names = 닉네임.strip().split()
    if not names:
        await interaction.response.send_message("❗ 이름을 하나 이상 입력해주세요.", ephemeral=True)
        return
    if len(names) > 25:
        await interaction.response.send_message("❗ 최대 25명까지만 입력할 수 있어요.", ephemeral=True)
        return

    view = MultiSelectButton(labels=names, author_id=interaction.user.id, title=분배명)
    embed = discord.Embed(
        title=f"💰 {분배명} 분배 시작!",
        description=f"**{interaction.user.display_name}** 님에게 분배금 받아 가세요 😍",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=view)

# 🧩 /파티 명령어
class PartyButton(discord.ui.Button):
    def __init__(self, label, style, role, parent):
        super().__init__(label=label, style=style)
        self.role = role
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        added = False

        if user.id in self.parent.member_ids:
            if user.id not in self.parent.roles_map:
                self.parent.roles_map[user.id] = set()
            if self.role in self.parent.roles_map[user.id]:
                self.parent.roles_map[user.id].remove(self.role)
                if not self.parent.roles_map[user.id]:
                    del self.parent.roles_map[user.id]
                self.parent.member_ids.remove(user.id)
                added = False
            else:
                self.parent.roles_map[user.id].add(self.role)
                added = True
        else:
            self.parent.member_ids.add(user.id)
            self.parent.roles_map[user.id] = {self.role}
            added = True

        desc = self.parent.generate_description()
        embed = discord.Embed(
            title=self.parent.title,
            description=desc,
            color=discord.Color.blue() if self.parent.complete() else discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=self.parent)

class PartyCompleteButton(discord.ui.Button):
    def __init__(self, parent, author_id):
        super().__init__(label="모집 완료", style=discord.ButtonStyle.grey)
        self.parent = parent
        self.author_id = author_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ 작성자만 완료할 수 있어요!", ephemeral=True)
            return

        self.parent.disable_all_buttons()
        desc = self.parent.generate_description()
        embed = discord.Embed(
            title=self.parent.title,
            description=desc + "\n\n✅ 모집 완료!",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=self.parent)

class PartyView(discord.ui.View):
    def __init__(self, author, title, time, capacity, description, channel):
        super().__init__(timeout=None)
        self.author_id = author.id
        self.title = get_title_with_emoji(channel, title)
        self.time = time
        self.capacity = capacity
        self.description = description
        self.roles_map = {}
        self.member_ids = set()

        self.add_item(PartyButton("세가", discord.ButtonStyle.primary, "세가", self))
        self.add_item(PartyButton("세바", discord.ButtonStyle.success, "세바", self))
        self.add_item(PartyButton("딜러", discord.ButtonStyle.danger, "딜러", self))
        self.add_item(PartyCompleteButton(self, self.author_id))

    def disable_all_buttons(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    def complete(self):
        return len(self.member_ids) >= self.capacity

    def generate_description(self):
        result = [
            f"출발 시간: {self.time}",
            f"인원: {len(self.member_ids)} / {self.capacity}",
            f"설명: {self.description}"
        ]
        roles = {"세가": [], "세바": [], "딜러": []}
        for user_id, roles_set in self.roles_map.items():
            mentions = []
            for role in roles_set:
                swap = [r for r in roles_set if r != role]
                mention = f"<@{user_id}>"
                if swap:
                    mention += f"({swap[0]}O)"
                roles[role].append(mention)
        for role, users in roles.items():
            result.append(f"{role}: " + " ".join(users) if users else f"{role}:")
        return "\n".join(result)

@tree.command(name="파티", description="파티 모집을 시작합니다.")
@app_commands.describe(던전명="던전 이름", 출발시간="예: 오후 9시", 인원="필요한 인원 수", 설명="파티 설명")
async def 파티(interaction: discord.Interaction, 던전명: str, 출발시간: str, 인원: int, 설명: str):
    view = PartyView(
        author=interaction.user,
        title=던전명,
        time=출발시간,
        capacity=인원,
        description=설명,
        channel=interaction.channel.name
    )
    embed = discord.Embed(
        title=view.title,
        description=view.generate_description(),
        color=discord.Color.red()
    )
    await interaction.response.send_message(content="@everyone", embed=embed, view=view)
    thread = await interaction.channel.create_thread(name=f"{던전명} 파티 모집", type=discord.ChannelType.public_thread)
    await thread.send(f"{interaction.user.mention} 님이 파티 모집을 시작했어요!")

# 채널별 이모티콘 매핑
def get_title_with_emoji(channel_name, title):
    emoji_map = {
        "자유모집": "🔥",
        "크롬바스-모집": "💀",
        "글렌베르나-모집": "❄️",
        "브리레흐-모집": "🍕"
    }
    emoji = emoji_map.get(channel_name, "🔥")
    return f"{emoji} {title} 파티 모집!"

# 봇 시작
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ 봇 실행됨: {bot.user}")

# 실행
keep_alive()
bot.run(os.environ["TOKEN"])
