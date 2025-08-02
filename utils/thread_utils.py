import asyncio
import re
from datetime import datetime, timedelta
import discord

def schedule_thread_deletion(thread: discord.Thread, time_text: str):
    now = datetime.now()
    try:
        date_match = re.search(r'(\d{1,2})/(\d{1,2})', time_text)
        time_match = re.search(r'(오전|오후)?\s?(\d{1,2})(시)?', time_text)

        if date_match and time_match:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            hour = int(time_match.group(2))

            if '오후' in time_match.group(1):
                hour = (hour % 12) + 12
            elif '오전' in time_match.group(1):
                hour = hour % 12

            year = now.year
            party_time = datetime(year, month, day, hour)
            delete_time = party_time + timedelta(hours=12)
            delay = (delete_time - now).total_seconds()

            if delay > 0:
                async def delete_later():
                    await asyncio.sleep(delay)
                    await thread.delete(reason="출발 후 12시간 경과로 자동 삭제")
                asyncio.create_task(delete_later())

    except Exception as e:
        print(f"[자동 삭제 오류] {e}")
