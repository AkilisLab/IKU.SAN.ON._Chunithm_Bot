import random
import asyncio

import os

import logging

logger = logging.getLogger(__name__)

async def _wait_random(min_seconds: float, max_seconds: float) -> None:
  """
  Simply a function that waits for a random amount of time specified.

  :param min_seconds: Minimum number of seconds to wait.
  :param max_seconds: Maximum number of seconds to wait.
  :type min_seconds: float
  :type max_seconds: float

  :return: None
  :rtype: None
  """
  wait_time = random.uniform(min_seconds, max_seconds)
  logger.debug(f'Waiting for {wait_time:.2f} seconds to mimic human behavior.')
  await asyncio.sleep(wait_time)

async def is_state_file_exists(state_file_path: str) -> bool:
  """
  Checks if the specified state file exists.

  :param state_file_path: Path to the state file.
  :type state_file_path: str

  :return: True if the state file exists, False otherwise.
  :rtype: bool
  """
  return os.path.exists(state_file_path)