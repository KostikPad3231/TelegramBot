import os
import logging

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

token = os.getenv('TOKEN')
if not token:
    logging.error('Bot token not set')

bot = Bot(token=token)
dp = Dispatcher()

GITHUB_PAT = os.getenv('GITHUB_PAT')
if not GITHUB_PAT:
    logging.error('Github personal access token not set')
endpoint = 'https://models.github.ai/inference'
model = 'openai/gpt-4.1-nano'
client = AsyncOpenAI(
    base_url=endpoint,
    api_key=GITHUB_PAT,
)
