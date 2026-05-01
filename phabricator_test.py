import os
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = os.getenv("ENV_FILE", ".env")
ENV_PATH = BASE_DIR / ENV_FILE

if load_dotenv and ENV_PATH.exists():
    load_dotenv(ENV_PATH)
elif load_dotenv:
    load_dotenv()

PHABRICATOR_BASE_URL = os.getenv(
    "PHABRICATOR_BASE_URL",
    "https://phabricator.wikimedia.org"
)
API_TOKEN = os.getenv("PHABRICATOR_API_TOKEN")
PROJECT_ID = os.getenv("PHABRICATOR_PROJECT_ID", "8675")

APP_NAME = os.getenv("APP_NAME", "GLAM-Tool-Hospital")
APP_VERSION = os.getenv("APP_VERSION", "0.1")
APP_URL = os.getenv(
    "APP_URL",
    "https://meta.wikimedia.org/wiki/User:Dactylantha/GLAM_Tool_Hospital"
)
CONTACT_EMAIL = os.getenv("PHABRICATOR_CONTACT_EMAIL", "")

HEADERS = {
    "User-Agent": (
        f"{APP_NAME}/{APP_VERSION} "
        f"({APP_URL}; contact: {CONTACT_EMAIL})"
    )
}

if not API_TOKEN:
    raise RuntimeError("PHABRICATOR_API_TOKEN is not set")

url = f"{PHABRICATOR_BASE_URL}/api/project.query"

payload = {
    "api.token": API_TOKEN,
    "ids[0]": PROJECT_ID,
}

response = requests.post(
    url,
    data=payload,
    headers=HEADERS,
    timeout=30
)

print("Status:", response.status_code)
print(response.text)