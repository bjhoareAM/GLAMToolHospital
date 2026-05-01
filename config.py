import os
from pathlib import Path

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
    "https://phabricator.wikimedia.org",
)

PHABRICATOR_MANIPHEST_EDIT_URL = f"{PHABRICATOR_BASE_URL}/api/maniphest.edit"

API_TOKEN = os.getenv("PHABRICATOR_API_TOKEN")
PROJECT_PHID = os.getenv("PHABRICATOR_PROJECT_PHID")

APP_NAME = os.getenv("APP_NAME", "GLAM-Tool-Hospital")
APP_VERSION = os.getenv("APP_VERSION", "0.1")
APP_URL = os.getenv(
    "APP_URL",
    "https://meta.wikimedia.org/wiki/User:Dactylantha/GLAM_Tool_Hospital",
)
CONTACT_EMAIL = os.getenv("PHABRICATOR_CONTACT_EMAIL", "")

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

MAX_SCREENSHOTS = int(os.getenv("MAX_SCREENSHOTS", "3"))
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(8 * 1024 * 1024)))

FILE_VIEW_POLICY = os.getenv("PHABRICATOR_FILE_VIEW_POLICY", "")

ALLOWED_SCREENSHOT_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "pdf",
}

HEADERS = {
    "User-Agent": (
        f"{APP_NAME}/{APP_VERSION} "
        f"({APP_URL}; contact: {CONTACT_EMAIL})"
    )
}


ISSUE_TYPE_OPTIONS = [
    {
        "value": "Bug",
        "label": "Something is broken",
    },
    {
        "value": "Support request",
        "label": "I need help using a tool",
    },
    {
        "value": "Documentation problem",
        "label": "The instructions are confusing or missing",
    },
    {
        "value": "Feature request",
        "label": "I have an idea for improving a tool",
    },
    {
        "value": "Untriaged",
        "label": "I am not sure",
    },
]


PROJECT_TAG_OPTIONS = [
    {
        "value": "openrefine",
        "label": "OpenRefine",
        "phid_env": "PHABRICATOR_PROJECT_PHID_OPENREFINE",
    },
    {
        "value": "pattypan",
        "label": "Pattypan / PattyPan",
        "phid_env": "PHABRICATOR_PROJECT_PHID_PATTYPAN",
    },
    {
        "value": "quickstatements",
        "label": "QuickStatements",
        "phid_env": "PHABRICATOR_PROJECT_PHID_QUICKSTATEMENTS",
    },
    {
        "value": "petscan",
        "label": "PetScan",
        "phid_env": "PHABRICATOR_PROJECT_PHID_PETSCAN",
    },
    {
        "value": "glamorgan",
        "label": "GLAMorgan",
        "phid_env": "PHABRICATOR_PROJECT_PHID_GLAMORGAN",
    },
    {
        "value": "glamorous",
        "label": "GLAMorous",
        "phid_env": "PHABRICATOR_PROJECT_PHID_GLAMOROUS",
    },
    {
        "value": "other",
        "label": "Other / I am not sure",
        "phid_env": None,
    },
]

IMPACT_OPTIONS = [
    ("Blocked", "I cannot continue my work"),
    ("Major", "This is slowing down important work"),
    ("Moderate", "This is inconvenient but I have a workaround"),
    ("Minor", "This is a small issue or question"),
    ("Not sure", "I am not sure"),
]