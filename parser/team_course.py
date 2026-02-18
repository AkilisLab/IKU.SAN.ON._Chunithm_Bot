from bs4 import BeautifulSoup
from parser.navigator import Navigator

from typing import Dict

import json

with open('parser/cfg.json', 'r', encoding='utf-8') as cfg_file:
  user_cfg = json.load(cfg_file)
CHUNITHM_NET_ENGLISH_URL = user_cfg.get('CHUNITHM_NET_ENGLISH_URL_BASE', 'https://chunithm-net-eng.com/mobile')
TEAM_COURSE_URL = f'{CHUNITHM_NET_ENGLISH_URL}/team/teamCourse'

async def get_team_course_scores() -> Dict[str, int]:
  """
  Gets team course scores from the CHUNITHM team course page.

  :return: A dictionary mapping player names to their scores.
  :rtype: Dict[str, int]
  """
  async with Navigator(TEAM_COURSE_URL) as page:
    # obtain html content
    html_content = await page.content()

    # parsing team course scores
    course_scores = _parser_team_course_scores(html_content)

    return course_scores

def _parser_team_course_scores(html) -> Dict[str, int]:
  team_course_attrs = "rank_block"
  name_attr = "rank_block_name"
  score_attr = "rank_block_num"

  soup = BeautifulSoup(html, 'html.parser')

  course_scores = {}

  for course in soup.find_all("div", class_=team_course_attrs):
    name_div = course.find("div", class_=name_attr)
    score_div = course.find("div", class_=score_attr)

    if name_div and score_div:
      name = name_div.get_text(strip=True)
      score_text = score_div.get_text(strip=True).replace(',', '')

      try:
        score = int(score_text)
      except ValueError:
        score = 0

      course_scores[name] = score

  return course_scores