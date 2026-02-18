import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs.boost_day import add as boost_day_setup
from cogs.team_point import add as team_point_setup
from cogs.team_draw import add as team_draw_setup

from exceptions.boost_day_exceptions import BoostDayError
from exceptions.team_draw_exceptions import TeamDrawError
from exceptions.team_point_exceptions import TeamPointError

import logging
import os

from utils.embed import error_embed

from data.db import db


load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
intents = discord.Intents.default()
# intents.message_content = True
# intents.members = True


class ChunithmBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self) -> None:
        # Initialize database on startup.
        db.init_db()

        # Load cogs.
        await boost_day_setup(self)
        await team_point_setup(self)
        await team_draw_setup(self)

        # Sync application (slash) commands on startup.
        await self.tree.sync()

bot = ChunithmBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} - {bot.user.id}")


@bot.tree.command(name="hello", description="Say hello")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello {interaction.user.mention}!")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Global error handler for app commands."""
    if isinstance(error, (BoostDayError, TeamDrawError, TeamPointError)):
        return  # Handled in respective cogs

    logging.error(f"Unhandled app command error: {error}", exc_info=error)
    embed = error_embed(
        description="發生未預期的錯誤。請稍後再試，或聯絡機器人管理員。",
    )
    embed.add_field(name="錯誤詳情", value=str(error), inline=False)
    
    if not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.edit_original_response(embed=embed, view=None)

bot.run(token, log_handler=handler, log_level=logging.DEBUG)