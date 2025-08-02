import discord
from discord import app_commands, Interaction
from views.party_view import PartyView
from utils.thread_utils import schedule_thread_deletion

async def register_party_command(bot):

    @bot.tree.command(name="파티", description="던전 파티를 모집합니다.")
    @app_commands.describe(
        던전명="던전 이름",
        출발시간="예: 8/3(일) 오후 9시",
        인원="모집 최대 인원",
        설명="파티 모집 이유, 분배 등 편하게 작성해주세요."
    )
    async def 파티(interaction: Interaction, 던전명: str, 출발시간: str, 인원: int, 설명: str):
        await interaction.response.defer(thinking=True)  # 유효 시간 확보

        view = PartyView(
            interaction=interaction,
            roles=["세가", "세바", "딜러"],
            party_name=던전명,
            time=출발시간,
            capacity=인원,
            description=설명
        )
        view.embed.description = view.generate_description()

        await interaction.followup.send(content="@everyone", embed=view.embed, view=view)

        try:
            parts = 출발시간.split()
            date_part = parts[0]
            time_part = parts[1] if len(parts) > 1 else ""
            thread_name = f"{date_part} {time_part} {던전명}"
        except Exception:
            thread_name = f"출발일시 미정 {던전명}"

        thread = await interaction.channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread)
        await thread.add_user(interaction.user)
        view.thread = thread
        schedule_thread_deletion(thread, 출발시간)
