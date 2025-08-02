import discord
from discord import app_commands, Interaction

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

async def register_distribute_command(bot):

    @bot.tree.command(name="분배", description="닉네임별 분배 버튼을 생성합니다.")
    @app_commands.describe(
        제목="분배 제목",
        닉네임="닉네임 목록 (띄어쓰기 구분)"
    )
    async def 분배(interaction: Interaction, 제목: str, 닉네임: str):
        names = 닉네임.split()
        view = MultiSelectButton(labels=names, author_id=interaction.user.id, title=제목)
        await interaction.response.send_message(embed=view.embed, view=view)
