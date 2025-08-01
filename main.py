import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ========== /분배 명령어 ==========
class DistributeView(View):
    def __init__(self, names, author):
        super().__init__(timeout=None)
        self.clicked = set()
        self.names = names
        self.author = author
        for name in names:
            self.add_item(self.create_button(name))

    def create_button(self, label):
        button = Button(label=label, style=discord.ButtonStyle.success)

        async def callback(interaction):
            if interaction.user in self.clicked:
                await interaction.response.send_message("이미 클릭했어요!", ephemeral=True)
                return
            self.clicked.add(interaction.user)
            button.disabled = True
            await interaction.response.edit_message(view=self)

            if len(self.clicked) == len(self.names):
                embed = discord.Embed(
                    title=f"💰 {interaction.message.embeds[0].title[2:]}",
                    description="분배 완료! 👍",
                    color=discord.Color.green()
                )
                await interaction.message.edit(embed=embed, view=self)

        button.callback = callback
        return button

@bot.tree.command(name="분배", description="유물 분배용 버튼 생성")
@app_commands.describe(제목="분배 제목", 닉네임목록="띄어쓰기로 닉네임 구분")
async def 분배(interaction: discord.Interaction, 제목: str, 닉네임목록: str):
    names = 닉네임목록.split()
    embed = discord.Embed(
        title=f"💰 {제목} 분배 시작!",
        description=f"{' '.join(names)} 님에게 분배금 받아 가세요 😍",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=DistributeView(names, interaction.user))

# ========== /파티모집 명령어 ==========
class PartyView(View):
    def __init__(self, author: discord.Member, max_count: int, description: str):
        super().__init__(timeout=None)
        self.author = author
        self.max_count = max_count
        self.description = description
        self.roles = {"세가": {}, "세바": {}, "딜러": {}}
        self.message = None
        self.thread = None

        self.add_item(self.create_button("세가", discord.ButtonStyle.primary))
        self.add_item(self.create_button("세바", discord.ButtonStyle.success))
        self.add_item(self.create_button("딜러", discord.ButtonStyle.danger))
        self.add_item(self.create_complete_button())

    def create_button(self, label, style):
        button = Button(label=label, style=style)

        async def callback(interaction: discord.Interaction):
            user = interaction.user
            role_dict = self.roles[label]

            if user.id in role_dict:
                del role_dict[user.id]
                await interaction.response.send_message(f"{label} 역할에서 제거되었습니다.", ephemeral=True)
            else:
                role_dict[user.id] = user.display_name

            # 스레드 자동 초대
            if self.thread and user not in self.thread.members:
                await self.thread.add_user(user)

            await interaction.message.edit(embed=self.get_embed())

        button.callback = callback
        return button

    def create_complete_button(self):
        button = Button(label="모집 완료", style=discord.ButtonStyle.secondary)

        async def callback(interaction: discord.Interaction):
            if interaction.user != self.author:
                await interaction.response.send_message("모집 완료는 작성자만 가능합니다.", ephemeral=True)
                return

            embed = self.get_embed(done=True)
            await interaction.message.edit(embed=embed, view=self)

        button.callback = callback
        return button

    def get_embed(self, done=False):
        total_users = set()
        role_lines = []
        for role, members in self.roles.items():
            for uid in members:
                total_users.add(uid)

        count_text = f"{len(total_users)} / {self.max_count}"
        desc = f"출발 시간: \n인원: {count_text}\n설명: {self.description}\n\n"
        for role, members in self.roles.items():
            users = []
            for uid, name in members.items():
                swaps = [
                    other_role for other_role, other_members in self.roles.items()
                    if other_role != role and uid in other_members
                ]
                suffix = f"({', '.join(swaps)}O)" if swaps else ""
                users.append(f"<@{uid}>{suffix}")
            role_lines.append(f"{role}: " + ", ".join(users) if users else f"{role}: -")

        desc += "\n".join(role_lines)
        if done:
            desc += "\n\n모집 완료!"

        embed = discord.Embed(
            title="🔥 파티 모집!" if not done else "🔥 파티 완료!",
            description=desc,
            color=discord.Color.blue() if done else discord.Color.red()
        )
        return embed

@bot.tree.command(name="파티모집", description="파티 모집을 시작합니다.")
@app_commands.describe(던전명="던전 이름", 출발시간="출발 시간", 인원="모집 인원", 설명="설명")
async def 파티모집(interaction: discord.Interaction, 던전명: str, 출발시간: str, 인원: int, 설명: str):
    view = PartyView(interaction.user, 인원, 설명)
    embed = view.get_embed()
    embed.title = f"{던전명} 파티 모집!"
    await interaction.response.send_message(content="@everyone", embed=embed, view=view)
    view.message = await interaction.original_response()
    view.thread = await view.message.create_thread(name=f"{던전명} 파티", auto_archive_duration=60)

# ========== Keep Alive + 실행 ==========
keep_alive()
TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
