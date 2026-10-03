from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if BOT_TOKEN is None or ADMIN_ID is None:
    raise ValueError("Не найдены BOT_TOKEN или ADMIN_ID в .env")

ADMIN_ID = int(ADMIN_ID)