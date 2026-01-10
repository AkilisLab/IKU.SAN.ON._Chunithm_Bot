import discord
from discord import app_commands
from discord.ext import commands

from datetime import date

from utils.date_utils import parse_iso_date, next_month, is_month_key_format
from utils.embed import error_embed, info_embed

from sqlite3 import IntegrityError as sqlite3IntegrityError

from services.boost_day_service import add_proposal, get_user_proposals, get_month_proposals

from exceptions import boost_day_exceptions

import logging

CUT_OFF_DAY = 15  # Mid-month cutoff for current-month proposals.
logger = logging.getLogger(__name__)

class BoostDayCog(commands.GroupCog, name='boostday'):
  def __init__(self, bot: commands.Bot):
    self.bot = bot

  async def month_key_parser(self, month: str | None) -> str:
    """Parse month key from input or default to current month."""
    today = date.today()
    
    if month is None:
      month_key = f"{today.year}-{today.month:02d}"
    else:
      if not is_month_key_format(month):
        raise boost_day_exceptions.InvalidMonthFormatException()
      month_key = month
    
    return month_key

  async def cog_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError) -> None:
    """Global error handler for app commands in this cog."""

    if isinstance(error, boost_day_exceptions.BoostDayError):
      embed = error_embed(
        description=error.args[0].get("message", "執行指令時發生錯誤，請檢查輸入並重試。")
      )

      if not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, ephemeral=True)
      else:
        await interaction.edit_original_response(embed=embed, view=None)

      return
    
    raise error  # Propagate to global handler if unhandled.

  @app_commands.command(
    name='propose',
    description='提案本月或下月的加成日。'
  )
  @app_commands.rename(target_date="日期")
  @app_commands.describe(target_date="目標日期，格式為 YYYY-MM-DD")
  async def boost_day_propose(self, interaction: discord.Interaction, target_date: str):

    today = date.today()
    parsed = parse_iso_date(target_date)

    if parsed is None:
      raise boost_day_exceptions.InvalidDateFormatException()
    
    if parsed < today:
      raise boost_day_exceptions.DateInPastException()
    
    current_month_key = (today.year, today.month)
    next_m = next_month(today)
    next_month_key = (next_m.year, next_m.month)
    target_key = (parsed.year, parsed.month)

    if target_key not in (current_month_key, next_month_key):
      raise boost_day_exceptions.MonthOutOfRangeException()
    
    if today.day > CUT_OFF_DAY and target_key == current_month_key:
      raise boost_day_exceptions.RegistrationClosedException()
    
    db_month_key = f"{parsed.year}-{parsed.month:02d}"
    try:
      add_proposal(interaction.user.id, parsed, db_month_key)
      await interaction.response.send_message(
        f"✅ 已成功提案加成日：{parsed.isoformat()}！"
      )
    except sqlite3IntegrityError:
      raise boost_day_exceptions.DuplicateProposalException()

  @app_commands.command(
    name='view_self',
    description='查看自己在指定月份的所有加成日提案 。'
  )
  @app_commands.rename(month="月份")
  @app_commands.describe(month="欲查詢的月份，格式為 YYYY-MM，預設為本月")
  async def my_boost_proposals(self, interaction: discord.Interaction, month: str = None):
    month_key = await self.month_key_parser(month)

    proposals = get_user_proposals(interaction.user.id, month_key)

    if not proposals:
      embed = info_embed(
        title="沒有加成日提案",
        description=f"您在 {month_key} 沒有任何加成日提案。",
        color=discord.Color.blue()
      )
    else:
      proposal_list = "\n".join([
        f"• **{p.target_date.isoformat()}** （於 <t:{int(p.created_at.timestamp())}:f> 提交）"
        for p in sorted(proposals, key=lambda x: x.target_date)
      ])
      embed = info_embed(
          title=f"你的加成日提案：{month_key}",
          color=discord.Color.blue(),
          fields=[
            ("提案列表", proposal_list, False)
          ]
      )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
  @app_commands.command(
    name='view_all',
    description='查看指定月份的所有加成日提案 。'
  )
  @app_commands.rename(month="月份")
  @app_commands.describe(month="欲查詢的月份，格式為 YYYY-MM，預設為本月")
  async def boost_proposals(self, interaction: discord.Interaction, month: str = None):
    month_key = await self.month_key_parser(month)

    proposals = get_month_proposals(month_key)
    
    if not proposals:
      embed = info_embed(
        title="沒有加成日提案",
        description=f"{month_key} 沒有任何加成日提案。",
        color=discord.Color.blue()
      )
    else:
      # Build a list of all proposals
      proposal_list = "\n".join([
        f"• **{p.target_date.isoformat()}** (提出者: <@{p.user_id}>)"
        for p in sorted(proposals, key = lambda x: x.target_date)
      ])
      
      embed = info_embed(
        title=f"加成日提案一覽：{month_key}",
        description=proposal_list,
        color=discord.Color.green()
      )
      embed.set_footer(text = f"提案總數：{len(proposals)}")
      
    await interaction.response.send_message(embed=embed, ephemeral=True)
    

async def add(bot: commands.Bot):
  await bot.add_cog(BoostDayCog(bot))

async def remove(bot: commands.Bot):
  await bot.remove_cog("BoostDayCog")