import discord
from discord.ext import commands
from discord import app_commands
from keep_alive import keep_alive
import os

keep_alive()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

REQUIRED_ROLE = "별의상흔"

# 역할 확인 함수
def has_required_role(user: discord.Member, required_role: str) -> bool:
    return any(role.name == required_role for role in user.roles)

#####################################
# /분배 명령어
#####################################
class MultiSelectButton(discord.ui.View):
    def __init__(self, labels: list[str], author_id: int, embed: discord.Embed):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.remaining = set(labels)
        self.embed = embed
        self.message = None
        self.title = ""
        for label in labels:
            self.add_item(NameButton(label, author_id, self))

    def check_all_selected(self):
        return len(self.remaining) == 0

class NameButton(discord.ui.Button):
    def __init__(self, label: str, author_id: int, parent: MultiSelectButton):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.author_id = author_id
        self.parent = parent
        self.original_label = label

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ 이 버튼은 명령어 작성자만 클릭할 수 있어요.", ephemeral=True)
            return

        self.disabled = True
        self.style = discord.ButtonStyle.success
        self.label = f"✅ {self.original_label}"
        self.parent.remaining.discard(self.original_label)

        if self.parent.check_all_selected():
            self.parent.embed.color = discord.Color.green()
            self.parent.embed.title = f"💰 {self.parent.title}"
            self.parent.embed.description = "분배 완료! 👍"

        await interaction.response.edit_message(embed=self.parent.embed, view=self.parent)

@tree.command(name="분배", description="분배명과 닉네임들을 입력하면 버튼이 생성됩니다.")
@app_commands.describe(분배명="예: 주간 회의, 업무 분배 등", 닉네임="띄어쓰기로 구분된 이름들 (예: 철수 영희 민수)")
async def 분배(interaction: discord.Interaction, 분배명: str, 닉네임: str):
    if not has_required_role(interaction.user, REQUIRED_ROLE):
        await interaction.response.send_message("⛔ 이 명령어는 '별의상흔' 역할을 가진 사람만 사용할 수 있어요.", ephemeral=True)
        return

    labels = 닉네임.strip().split()
    if not labels:
        await interaction.response.send_message("❗ 이름을 하나 이상 입력해주세요.", ephemeral=True)
        return
    if len(labels) > 25:
        await interaction.response.send_message("❗ 최대 25개까지 입력할 수 있습니다.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"💰 {분배명} 분배 시작!",
        description=f"**{interaction.user.display_name}** 님에게 분배금 받아 가세요 😍",
        color=discord.Color.gold()
    )

    view = MultiSelectButton(labels, interaction.user.id, embed)
    view.title = 분배명

    await interaction.response.send_message(embed=embed, view=view)

#####################################
# /파티모집 명령어
#####################################
class PartyView(discord.ui.View):
    def __init__(self, author: discord.Member, title: str, time: str, total_slots: int, description: str, channel: discord.TextChannel):
        super().__init__(timeout=None)
        self.author = author
        self.title = title
        self.time = time
        self.total_slots = total_slots
        self.description = description
        self.channel = channel
        self.roles = {"세가": set(), "세바": set(), "딜러": set()}
        self.message = None
        self.emoji_map = {
            "자유모집": "🔥",
            "크롬바스-모집": "💀",
            "글렌베르나-모집": "❄️",
            "브리레흐-모집": "🍕",
        }
        self.add_item(RoleButton("세가", discord.ButtonStyle.primary))
        self.add_item(RoleButton("세바", discord.ButtonStyle.success))
        self.add_item(RoleButton("딜러", discord.ButtonStyle.danger))
        self.add_item(CompleteButton(discord.ButtonStyle.secondary))

    def get_embed(self, completed=False):
        color = discord.Color.blue() if completed else discord.Color.red()
        unique_users = set().union(*self.roles.values())
        count = len(unique_users)
        title_emoji = self.emoji_map.get(self.channel.name, "🔥")

        embed = discord.Embed(
            title=f"{title_emoji} {self.title} 파티 모집!",
            color=color
        )
        embed.description = (
            f"출발 시간: {self.time}\n"
            f"인원: {count} / {self.total_slots}\n"
            f"설명: {self.description}\n\n"
            f"세가: {', '.join(self.format_user(u, '세가')) or '-'}\n"
            f"세바: {', '.join(self.format_user(u, '세바')) or '-'}\n"
            f"딜러: {', '.join(self.format_user(u, '딜러')) or '-'}"
        )
        return embed

    def format_user(self, user: discord.Member, current_role: str):
        other_roles = [r for r in self.roles if user in self.roles[r] and r != current_role]
        if other_roles:
            return f"{user.mention}({', '.join(other_roles)}O)"
        return user.mention

class RoleButton(discord.ui.Button):
    def __init__(self, role: str, style: discord.ButtonStyle):
        super().__init__(label=role, style=style)
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        view: PartyView = self.view
        user = interaction.user

        if user in view.roles[self.role]:
            view.roles[self.role].remove(user)
        else:
            view.roles[self.role].add(user)

        await interaction.response.edit_message(embed=view.get_embed(), view=view)

class CompleteButton(discord.ui.Button):
    def __init__(self, style):
        super().__init__(label="모집 완료", style=style)

    async def callback(self, interaction: discord.Interaction):
        view: PartyView = self.view
        if interaction.user != view.author:
            await interaction.response.send_message("❌ 작성자만 완료할 수 있습니다.", ephemeral=True)
            return
        await interaction.response.edit_message(embed=view.get_embed(completed=True), view=view)

@tree.command(name="파티모집", description="파티원을 모집합니다.")
@app_commands.describe(
    던전명="던전 제목",
    출발시간="출발 시간",
    인원="모집 인원 수",
    설명="파티 설명")
async def 파티모집(interaction: discord.Interaction, 던전명: str, 출발시간: str, 인원: int, 설명: str):
    if not has_required_role(interaction.user, REQUIRED_ROLE):
        await interaction.response.send_message("⛔ 이 명령어는 '별의상흔' 역할을 가진 사람만 사용할 수 있어요.", ephemeral=True)
        return

    view = PartyView(interaction.user, 던전명, 출발시간, 인원, 설명, interaction.channel)
    embed = view.get_embed()
    await interaction.response.send_message(content="@everyone", embed=embed, view=view)

#####################################
# 봇 시작
#####################################
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ 봇 실행됨: {bot.user}")

bot.run(os.environ["DISCORD_TOKEN"])
