import discord
from discord.ui import View, Button
from typing import List

class RoleButton(discord.ui.Button):
    def __init__(self, role: str, author_id: int):
        color_map = {"세가": discord.ButtonStyle.primary, "세바": discord.ButtonStyle.success, "딜러": discord.ButtonStyle.danger}
        style = color_map.get(role, discord.ButtonStyle.secondary)
        super().__init__(label=role, style=style)
        self.role = role
        self.author_id = author_id
        self.clicked_users = []

    async def callback(self, interaction: discord.Interaction):
        view: PartyView = self.view
        embed = view.embed

        if interaction.user in self.clicked_users:
            self.clicked_users.remove(interaction.user)
            view.user_roles[interaction.user].remove(self.role)
            if not view.user_roles[interaction.user]:
                del view.user_roles[interaction.user]
                view.unique_users.discard(interaction.user)
            embed.description = view.generate_description()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        self.clicked_users.append(interaction.user)
        view.user_roles.setdefault(interaction.user, []).append(self.role)
        view.unique_users.add(interaction.user)

        embed.description = view.generate_description()
        await interaction.response.edit_message(embed=embed, view=view)

        await view.check_auto_complete(interaction)

class CompleteButton(discord.ui.Button):
    def __init__(self, author_id):
        super().__init__(label="모집 완료", style=discord.ButtonStyle.secondary)
        self.author_id = author_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("모집자만 완료할 수 있습니다!", ephemeral=True)
            return

        view: PartyView = self.view
        embed = view.embed
        embed.color = discord.Color.blue()
        embed.description += "\n\n🌟모집 완료🌟"
        for child in view.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=view)
        await interaction.message.edit(view=view)

class PartyView(View):
    def __init__(self, interaction: discord.Interaction, roles: List[str], party_name: str, time: str, capacity: int, description: str):
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
        self.thread = None
        self.author = interaction.user

        icon = "🔥"
        if "크롬바스-모집" in self.channel.name:
            icon = "💀"
        elif "글렌베르나-모집" in self.channel.name:
            icon = "❄️"
        elif "브리레흐-모집" in self.channel.name:
            icon = "🍕"

        self.embed = discord.Embed(
            title=f"{icon} {party_name}",
            color=discord.Color.red()
        )
        for role in roles:
            self.add_item(RoleButton(role, self.author_id))
        self.add_item(CompleteButton(self.author_id))

    def generate_description(self) -> str:
        role_lines = {role: [] for role in self.roles}
        for button in self.children:
            if isinstance(button, RoleButton):
                for u in button.clicked_users:
                    other_roles = [r for r in self.user_roles.get(u, []) if r != button.role]
                    mention = u.mention
                    if other_roles:
                        role_lines[button.role].append(f"{mention}({', '.join(other_roles)} O)")
                    else:
                        role_lines[button.role].append(mention)

        lines = [
            f"**출발 시간**: {self.time}",
            f"**인원**: {len(self.unique_users)} / {self.capacity}",
            f"**설명**: {self.description_text}",
            "",
            "•❅──────────✧❅✦❅✧──────────❅•"
        ]

        for r in self.roles:
            members = ", ".join(role_lines[r]) if role_lines[r] else ""
            lines.append(f"{r}:  {members}")

        lines.append("•❅──────────✧❅✦❅✧──────────❅•")
        return "\n".join(lines)

    async def check_auto_complete(self, interaction: discord.Interaction):
        if len(self.unique_users) >= self.capacity and not getattr(self, "completed", False):
            self.completed = True
            self.embed.color = discord.Color.blue()
            self.embed.description += "\n\n🌟모집 완료🌟"
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(embed=self.embed, view=self)
            if self.thread and self.author:
                await self.thread.send(f"{self.author.mention} 모집 인원이 모두 찼어요! 🎉")
