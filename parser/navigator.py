from playwright.async_api import async_playwright, expect
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from parser.util import _wait_random, is_state_file_exists

import asyncio

from dotenv import dotenv_values

import json

import logging

from typing import Optional, Tuple

logger = logging.getLogger("discord.parser.navigator")

with open('parser/cfg.json', 'r', encoding='utf-8') as cfg_file:
  user_cfg = json.load(cfg_file)
  BASE_URL = user_cfg.get('CHUNITHM_NET_ENGLISH_URL_BASE', 'https://chunithm-net-eng.com/mobile')
  ERROR_URL = f'{BASE_URL}/error'

env_cfg = dotenv_values()

class Navigator:
  """
  Context manager for navigating to a specified Chunithm Net English URL using Playwright. When using with `async with`,
  it handles login if necessary and ensures the page is loaded correctly. yields a `Page` object.

  :param url: The URL to navigate to.
  :type url: str
  
  :raises ValueError: If the provided URL is not related to Chunithm Net English.
  :raises RuntimeError: If login fails or the desired page cannot be loaded after retries.
  """

  def __init__(self, url: str):
    # Check if link is CHUNITHM related
    if BASE_URL not in url:
      raise ValueError('The provided URL appears to not be related to Chunithm Net English.')
    
    self.url = url

  def _get_username_password(self) -> Tuple[str, str]:
    username: Optional[str] = env_cfg.get('PARSER_SEGA_ID')
    password: Optional[str] = env_cfg.get('PARSER_SEGA_PW')
    if not username or not password:
      raise ValueError('SEGA ID or password not found in environment variables.')
    return username, password

  async def _load_page(self, retry_limit: int) -> Tuple[Page, bool]:
    retry_count = 0
    is_success = False
    while (retry_count < retry_limit):
      await self.page.goto(self.url)
      await self.page.wait_for_load_state("networkidle", timeout=60000)
      retry_count += 1
      if not self.page.url.startswith(ERROR_URL):
        is_success = True
        break

    if not is_success:
      logger.warning(f'Failed to load page {self.url} after {retry_limit} attempts.')
    return self.page, is_success

  async def __aenter__(self) -> Page:

    # Get state file from user config
    state_file = user_cfg.get('PARSER_STATE_FILE', 'data/_parser_state.json')

    # initialize playwright stuff
    self.playwright = await async_playwright().start()
    self.browser = await self.playwright.chromium.launch(headless=True)
    self.context = await self.browser.new_context(storage_state=state_file if (await is_state_file_exists(state_file)) else None)
    self.page = await self.context.new_page()

    # attempt to go to page
    self.page, success = await self._load_page(1)
    if success:
      return self.page

    
    logger.info('Redirected to error page, possibly due to expired session. Pressing "back" button...')

    await _wait_random(0.5, 1.2)
    await self.page.locator('div.btn_back').click()

    try:
      await self.page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
      # sometimes loading gets stuck for whatever reason, so we retry 1 time here
      logger.warning('Timeout while waiting for page to load after going back from error page. Retrying...')
      await self.page.reload(timeout=60000, wait_until="networkidle")

    # got to home page, now try to go to desired page again
    if await self.page.locator('li.btn_team').count() > 0:
      logger.info('Returned to home page successfully.')
      # try two more times
      self.page, success = await self._load_page(2)
      if success:
        return self.page
      else:
        logger.error(f'Failed to load the desired page after returning to home page: {self.url}')
        raise RuntimeError(f'Failed to load the desired page after returning to home page: {self.url}')

    # need to login
    logger.info('Not logged in, proceeding to login...')
    
    username, password = self._get_username_password()

    # tick agree to terms
    await _wait_random(0.5, 1.1)
    await self.page.get_by_role("checkbox", name="Agree to the terms of use for").check()
    await _wait_random(1.4, 2.5)

    # open sega id login box
    await self.page.locator('span.c-button--openid--segaId').click()
    await asyncio.sleep(0.5)

    # enter id and pw
    sega_id_textbox = self.page.locator('input#sid')
    await sega_id_textbox.fill(username)
    await _wait_random(2.5, 3.8)
    sega_pw_textbox = self.page.locator('input#password')
    await sega_pw_textbox.fill(password)
    await _wait_random(2.7, 4.0)

    # click login
    await self.page.locator('button#btnSubmit').click()
    logger.info('Login submitted.')
    await _wait_random(0.5, 1.2)

    # Check if login was successful by verifying the URL
    try:
      await expect(self.page.locator('li.btn_team')).to_be_visible(timeout=15000)
      logger.info('Login successful, navigating to team member page.')
    except PlaywrightTimeoutError:
      raise RuntimeError('Login failed or took too long. Please check your SEGA ID and password.')
    
    return self.page

  async def __aexit__(self, exc_type, exc, tb):
    await self.context.storage_state(path=user_cfg.get('PARSER_STATE_FILE', 'data/_parser_state.json'))
    logger.info('Parser storage state saved.')

    await self.browser.close()
    logger.info('Browser closed.')

    await self.playwright.stop()
    logger.info('Playwright stopped.')