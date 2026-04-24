import os
from pathlib import Path
from datetime import datetime

import requests
from flask import Flask, render_template_string

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

app = Flask(__name__)

PHABRICATOR_BASE_URL = os.getenv(
    "PHABRICATOR_BASE_URL",
    "https://phabricator.wikimedia.org"
)
API_TOKEN = os.getenv("PHABRICATOR_API_TOKEN")
PROJECT_PHID = os.getenv("PHABRICATOR_PROJECT_PHID")

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

HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>GLAM Tool Hospital - Live Tracker</title>
    <meta http-equiv="refresh" content="60">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 32px auto;
            padding: 0 16px;
            line-height: 1.45;
        }
        .note {
            margin-bottom: 20px;
            padding: 10px 12px;
            background: #f7f7f7;
            border-left: 4px solid #999;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            align-items: start;
        }
        .column {
            border: 1px solid #ccc;
            background: #fafafa;
            padding: 12px;
            border-radius: 6px;
        }
        .card {
            border: 1px solid #ddd;
            background: white;
            padding: 10px;
            margin-top: 10px;
            border-radius: 6px;
        }
        .meta {
            color: #555;
            font-size: 0.92em;
        }
        .empty {
            color: #777;
            font-style: italic;
        }
        a {
            text-decoration: none;
        }
        h1, h2, h3 {
            margin-bottom: 0.4em;
        }
        @media (max-width: 900px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <h1>GLAM Tool Hospital - Live Tracker</h1>

    <div class="note">
        <strong>Tracking project PHID:</strong> {{ project_phid or "Not set" }}<br>
        <strong>Refreshed at:</strong> {{ refreshed_at }}<br>
        <strong>Auto-refresh:</strong> every 60 seconds
    </div>

    {% if error %}
    <div class="note" style="border-left-color:#c55; background:#fff0f0;">
        <strong>Error:</strong> {{ error }}
    </div>
    {% endif %}

    <div class="grid">
        {% for column_name, tasks in grouped.items() %}
        <div class="column">
            <h2>{{ column_name }} ({{ tasks|length }})</h2>
            {% if tasks %}
                {% for task in tasks %}
                <div class="card">
                    <div><strong><a href="{{ task.url }}" target="_blank" rel="noopener noreferrer">{{ task.id }} - {{ task.title }}</a></strong></div>
                    <div class="meta">Priority: {{ task.priority }}</div>
                    <div class="meta">Updated: {{ task.updated }}</div>
                </div>
                {% endfor %}
            {% else %}
                <div class="empty">No tasks in this group.</div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""


def phab_post(method: str, payload: dict) -> dict:
    if not API_TOKEN:
        raise RuntimeError("PHABRICATOR_API_TOKEN is not set")

    url = f"{PHABRICATOR_BASE_URL}/api/{method}"

    form_payload = {"api.token": API_TOKEN}
    form_payload.update(payload)

    response = requests.post(
        url,
        data=form_payload,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    if data.get("error_code"):
        raise RuntimeError(f"{data['error_code']}: {data.get('error_info')}")

    return data["result"]


def unix_to_string(ts) -> str:
    if not ts:
        return ""
    return datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M UTC")


def fetch_project_tasks(project_phid: str) -> list[dict]:
    if not project_phid:
        raise RuntimeError("PHABRICATOR_PROJECT_PHID is not set")

    payload = {
        "constraints[projects][0]": project_phid,
        "order": "updated",
        "limit": "100",
    }

    result = phab_post("maniphest.search", payload)
    data = result.get("data", [])

    tasks = []
    for item in data:
        fields = item.get("fields", {})
        task_id = item.get("id")
        title = fields.get("name", "(untitled)")
        status_info = fields.get("status") or {}
        priority_info = fields.get("priority") or {}

        tasks.append({
            "id": f"T{task_id}",
            "title": title,
            "status": status_info.get("name", "Unknown"),
            "priority": priority_info.get("name", "Unknown"),
            "updated": unix_to_string(fields.get("dateModified")),
            "url": f"{PHABRICATOR_BASE_URL}/T{task_id}",
        })

    return tasks


def group_tasks_by_status(tasks: list[dict]) -> dict:
    grouped = {
        "Open": [],
        "Stalled": [],
        "Resolved / Closed": [],
    }

    for task in tasks:
        status = (task.get("status") or "").lower()

        if "open" in status or "progress" in status:
            grouped["Open"].append(task)
        elif "stall" in status:
            grouped["Stalled"].append(task)
        else:
            grouped["Resolved / Closed"].append(task)

    return grouped


@app.route("/board", methods=["GET"])
def board():
    error = None
    grouped = {
        "Open": [],
        "Stalled": [],
        "Resolved / Closed": [],
    }

    try:
        tasks = fetch_project_tasks(PROJECT_PHID)
        grouped = group_tasks_by_status(tasks)
    except Exception as e:
        error = str(e)

    return render_template_string(
        HTML,
        grouped=grouped,
        project_phid=PROJECT_PHID,
        refreshed_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        error=error,
    )


@app.route("/health", methods=["GET"])
def health():
    return {
        "ok": True,
        "has_api_token": bool(API_TOKEN),
        "has_project_phid": bool(PROJECT_PHID),
        "env_path": str(ENV_PATH),
        "phabricator_base_url": PHABRICATOR_BASE_URL,
    }


if __name__ == "__main__":
    app.run(debug=True, port=5001)