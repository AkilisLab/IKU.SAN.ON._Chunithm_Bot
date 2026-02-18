import discord
from discord import app_commands
from discord.ext import commands, tasks

from parser.team_point import get_team_scores

from exceptions import team_point_exceptions

from utils.embed import error_embed, info_embed, warning_embed

import datetime

import json

import asyncio

import logging

logger = logging.getLogger(__name__)

from typing import Optional

STATE_FILE = 'data/_team_points_state.json'

def _load_state():
  try:
    with open(STATE_FILE, 'r') as f:
      return json.load(f)
  except FileNotFoundError:
    return {}

def _save_state(tp_msg_channel_id: int | None, tp_msg_msg_id: int | None):
  with open(STATE_FILE, 'w') as f:
    json.dump({
      'tp_msg_channel': tp_msg_channel_id,
      'tp_msg_msg_id': tp_msg_msg_id
    }, f)

class TeamPointCog(commands.GroupCog, name='teampoint'):
  def __init__(self, bot: commands.Bot):
    self.bot = bot

    states = _load_state()
    self.channel_id: Optional[int] = states.get('tp_msg_channel', None)
    self.msg_id: Optional[int] = states.get('tp_msg_msg_id', None)

    self.update_team_points.start()


  def _save_state_to_file(self):
    _save_state(self.channel_id, self.msg_id)


  async def get_channel_message(self):
    def nullify():
      self.channel_id = None
      self.msg_id = None
      self._save_state_to_file()

    if self.channel_id is None or self.msg_id is None:
      nullify()
      raise team_point_exceptions.NoTeamPointMessageSetException()


    channel = self.bot.get_channel(self.channel_id)
    if channel is None or not isinstance(channel, discord.TextChannel):
      nullify()
      raise team_point_exceptions.ChannelNotFoundException()

    message = None
    try:
      if channel and channel.fetch_message:
        message = await channel.fetch_message(self.msg_id)
    except (discord.NotFound, discord.Forbidden):
      # Message not found or bot has no access
      nullify()
      raise team_point_exceptions.MessageNotFoundException()

    if channel is None or message is None:
      nullify()

    return channel, message

  async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for app commands in this cog."""
    if isinstance(error, team_point_exceptions.TeamPointError):
      embed = error_embed(
        description=error.args[0].get('message'),
      )
      if not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, ephemeral=True)
      else:
        await interaction.edit_original_response(embed=embed, view=None)

      return
    
    raise error  # Propagate to global handler if unhandled.
    

  @tasks.loop(time=datetime.time(hour=7, minute=15, second=0, tzinfo=datetime.timezone(offset=datetime.timedelta(hours=9))))
  async def update_team_points(self):
    """Periodically fetches and updates the team point message."""
    logger.info("Started updating team points...")

    try:
      channel, message = await self.get_channel_message()
    except team_point_exceptions.TeamPointError as e:
      logger.warning(f"Cannot update team points due to: {e}")
      return

    try:
      team_scores = await get_team_scores()
    except Exception as e:
      # Log the error, but do not raise
      logger.error(f"Error fetching team scores: {e}")
      return
    
    sum_scores = sum(team_scores.values())

    embed = info_embed(
      title="團隊積分排行榜",
      description=f"=== 每天07:15 JST更新一次 | 最後更新：<t:{int(discord.utils.utcnow().timestamp())}:F> ===",
      fields=[(player, f"{score} 分", False) for player, score in team_scores.items()]
    )

    embed.set_footer(text=f"總積分: {sum_scores} 分")

    try:
      await message.edit(content='', embed=embed)
    except discord.Forbidden:
      logger.error("Bot does not have permission to edit the team point message.")
    except discord.NotFound:
      logger.error("Team point message not found.")
    except Exception as e:
      logger.error(f"Unexpected error while updating team point message: {e}")

    logger.info("Team points update task completed.")
    
    
  @app_commands.command(name='update', description='立即更新團隊積分訊息。')
  async def update_now(self, interaction: discord.Interaction):
    """Immediately updates the team point message."""
    if not self.msg_id or not self.channel_id:
      raise team_point_exceptions.NoTeamPointMessageSetException()
  
    if None in (await self.get_channel_message()):
      raise team_point_exceptions.MessageNotFoundException()
    
    await interaction.response.send_message("已觸發團隊積分更新。請稍後片刻後查看。", ephemeral=True)
    await self.update_team_points()


  @app_commands.command(name='set_channel', description='設定或更新團隊積分訊息的位置。')
  @app_commands.rename(channel='頻道')
  @app_commands.describe(channel='要發送團隊積分訊息的頻道')
  async def set_team_point_msg(self, interaction: discord.Interaction, channel: discord.TextChannel):
    if self.channel_id == channel.id:
      raise team_point_exceptions.SameChannelException()

    if (self.channel_id is not None) and (self.msg_id is not None):
      # confirm if want to overwrite
      existing_channel, _ = await self.get_channel_message()
      if not await self.confirm_overwrite_tp_msg(interaction):
        embed = info_embed(
          title='❎ 已取消覆寫團隊積分訊息位置',
          description=f'團隊積分訊息仍然發送至 {existing_channel.mention} 。'
        )
        try:
          await interaction.edit_original_response(embed=embed, view=None)
        except discord.NotFound:
          # original response deleted, this is not very critical and can be ignored
          pass
        return

    # Send message
    try:
      message = await channel.send('團隊積分訊息會隨著定時爬取而自動更新。')
    except discord.Forbidden:
      raise team_point_exceptions.MessageForbiddenException()
    
    # save channel id and message id
    self.channel_id = channel.id
    self.msg_id = message.id
    self._save_state_to_file()

    embed = info_embed(
      title='✅ 已設定團隊積分訊息位置',
      description=f'團隊積分訊息將會發送至 {channel.mention} 。'
    )
    if not interaction.response.is_done():
      await interaction.response.send_message(embed=embed)
    else:
      await interaction.edit_original_response(embed=embed, view=None)


  async def confirm_overwrite_tp_msg(self, interaction: discord.Interaction) -> bool:
    """Asks the user to confirm overwriting the existing team point message location.
    Sends a confirmation prompt via `discord.Interaction.response.send_message` and waits for the user's response.
    
    :param interaction: The interaction object from the command invocation.
    :return: True if the user confirms, False if they cancel or timeout.
    :rtype: bool
    """
    channel, _ = await self.get_channel_message()
    embed = warning_embed(
      title='⚠️ 確定要覆寫團隊積分訊息位置嗎？',
      description=f'目前團隊積分訊息頻道已設置為 {channel.mention if channel else "Unknown"} 。確定要覆寫嗎？\n如不覆寫，請無需操作。',
    )
    view = discord.ui.View(timeout=60.0)
    view.add_item(discord.ui.Button(
      label='確定',
      style=discord.ButtonStyle.danger,
      custom_id='confirm_overwrite_tp_msg'
    ))
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    try:
      await self.bot.wait_for(
        'interaction',
        check=lambda i: i.data.get('custom_id') == 'confirm_overwrite_tp_msg' and i.user.id == interaction.user.id,
        timeout=60.0
      )
      return True
    except asyncio.TimeoutError:
      return False


async def add(bot: commands.Bot):
  cog = TeamPointCog(bot)
  await bot.add_cog(cog)
