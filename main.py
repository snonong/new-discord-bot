import discord
from discord.ext import commands
from discord import app_commands
from keep_alive import keep_alive

import asyncio
from typing import List

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
client = commands.Bot(command_prefix="/", intents=intents)

REQUIRED_ROLE_NAME = "별의상흔"

keep_alive()


def get_emoji_by_channel(channel_name: str) -> str:
    emojis = {
        "자유모집": "🔥",
        "크롬바스-모집": "💀",
        "글렌베르나-모집": "❄️",
        "브리레흐-모집": "🍕"
    }
    return emojis.get(channel_name, "🔥")


class PartyView(discord.ui.View):
    def __init__(self, author: discord.Member, dungeon: str, time: str, max_members: int, description: str):
        super().__init__(timeout=None)
        self.author = author
        self.dungeon = dungeon
        self.time = time
        self.max_members = max_members
        self.description = description
        self.party_roles = {"세가": [], "세바": [], "딜러": []}
        self.message = None
        self.finished = False

    def format_user(self, user: discord.Member, current_role: str) -> str:
        swapped_roles = [r for r in self.party_roles if r != current_role and user in self.party_roles[r]]
        if swapped_roles:
            return f"{user.mention}({'/'.join(swapped_roles)}O)"
        return user.mention

    def get_embed(self) -> discord.Embed:
        total_users = set()
        for users in self.party_roles.values():
            total_users.update(users)
        current_count = len(total_users)

        embed = discord.Embed(
            title=f"{get_emoji_by_channel(self.message.channel.name)} {self.dungeon} 파티 모집!",
            description=(
                f"출발 시간: {self.time}\n"
                f"인원: {current_count} / {self.max_members}\n"
                f"설명: {self.description}\n\n"
                f"세가: {'、'.join([self.format_user(u, '세가') for u in self.party_roles['세가']]) or '-'}\n"
                f"세바: {'、'.join([self.format_user(u, '세바') for u in self.party_roles['세바']]) or '-'}\n"
                f"딜러: {'、'.join([self.format_user(u, '딜러') for u in self.party_roles['딜러']]) or '-'}"
            ),
            color=discord.Color.blue() if self.finished else discord.Color.red()
        )
        return embed

    async def update_message(self):
        await self.message.edit(embed=self.get_embed(), view=self)

    async def toggle_user(self, interaction: discord.Interaction, role: str):
        user = interaction.user
        if user in self.party_roles[role]:
            self.party_roles[role].remove(user)
        else:
            self.party_roles[role].append(user)
        await self.update_message()
        thread = discord.utils.get(self.message.guild.threads, name=f"{self.dungeon} - 파티 모집")
        if user not in thread.members:
            await thread.add_user(user)

    @discord.ui.button(label="세가", style=discord.ButtonStyle.primary, row=0)
    async def sega(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_user(interaction, "세가")

    @discord.ui.button(label="세바", style=discord.ButtonStyle.success, row=0)
    async def seba(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_user(interaction, "세바")

    @discord.ui.button(label="딜러", style=discord.ButtonStyle.danger, row=0)
    async def dealer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_user(interaction, "딜러")

    @discord.ui.button(label="모집 완료", style=discord.ButtonStyle.secondary, row=1)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("명령어를 사용한 유저만 모집 완료할 수 있습니다.", ephemeral=True)
            return
        self.finished = True
        await self.update_message()


@client.tree.command(name="파티모집")
@app_commands.describe(
    던전명="던전 이름을 입력하세요",
    출발시간="출발 시간을 입력하세요",
    인원="총 인원 수를 입력하세요",
    설명="파티에 대한 설명을 입력하세요"
)
async def 모집(interaction: discord.Interaction, 던전명: str, 출발시간: str, 인원: int, 설명: str):
    role = discord.utils.get(interaction.guild.roles, name=REQUIRED_ROLE_NAME)
    if role not in interaction.user.roles:
        await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
        return

    view = PartyView(interaction.user, 던전명, 출발시간, 인원, 설명)
    embed = view.get_embed()
    await interaction.response.send_message(content="@everyone", embed=embed, view=view)
    msg = await interaction.original_response()
    view.message = msg
    thread = await msg.create_thread(name=f"{던전명} - 파티 모집")
    await thread.add_user(interaction.user)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    try:
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Sync failed: {e}")


# 수정된 코드 (환경변수 체크 포함)
TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN is None:
    raise RuntimeError("DISCORD_TOKEN 환경변수가 설정되어 있지 않습니다.")

client.run(TOKEN)
