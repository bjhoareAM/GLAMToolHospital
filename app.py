import os
from pathlib import Path
from pprint import pformat

import requests
from flask import Flask, request, render_template_string

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
PHABRICATOR_URL = f"{PHABRICATOR_BASE_URL}/api/maniphest.edit"
API_TOKEN = os.getenv("PHABRICATOR_API_TOKEN")
PROJECT_PHID = os.getenv("PHABRICATOR_PROJECT_PHID")

APP_NAME = os.getenv("APP_NAME", "GLAM-Tool-Hospital")
APP_VERSION = os.getenv("APP_VERSION", "0.1")
APP_URL = os.getenv(
    "APP_URL",
    "https://meta.wikimedia.org/wiki/User:Dactylantha/GLAM_Tool_Hospital"
)
CONTACT_EMAIL = os.getenv("PHABRICATOR_CONTACT_EMAIL", "")

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

HEADERS = {
    "User-Agent": (
        f"{APP_NAME}/{APP_VERSION} "
        f"({APP_URL}; contact: {CONTACT_EMAIL})"
    )
}

HTML_FORM = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>GLAM Tool Hospital</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 820px;
            margin: 40px auto;
            padding: 0 16px;
            line-height: 1.45;
        }
        label {
            display: block;
            margin-top: 14px;
            font-weight: bold;
        }
        input, select, textarea {
            width: 100%;
            padding: 8px;
            margin-top: 6px;
            box-sizing: border-box;
        }
        textarea {
            min-height: 110px;
        }
        button {
            margin-top: 18px;
            padding: 10px 14px;
            cursor: pointer;
        }
        .result {
            margin-top: 24px;
            padding: 14px;
            background: #f4f4f4;
            border: 1px solid #ccc;
            white-space: pre-wrap;
            overflow-x: auto;
        }
        .error {
            background: #fff0f0;
            border-color: #d99;
        }
        .note {
            margin-bottom: 20px;
            padding: 10px 12px;
            background: #f7f7f7;
            border-left: 4px solid #999;
        }
    </style>
</head>
<body>
    <h1>GLAM Tool Hospital</h1>

    <div class="note">
        <strong>Mode:</strong> {{ mode_label }}<br>
        <strong>API token loaded:</strong> {{ token_status }}<br>
        <strong>Project PHID loaded:</strong> {{ project_status }}
    </div>

    <p>Test form for creating Phabricator task payloads.</p>

    <form method="post" action="/submit">
        <label for="name">Your name *</label>
        <input type="text" id="name" name="name" required value="{{ form_data.get('name', '') }}">

        <label for="email">Your email *</label>
        <input type="email" id="email" name="email" required value="{{ form_data.get('email', '') }}">

        <label for="tool_name">Tool name *</label>
        <input type="text" id="tool_name" name="tool_name" required value="{{ form_data.get('tool_name', '') }}">

        <label for="tool_url">Tool URL</label>
        <input type="url" id="tool_url" name="tool_url" value="{{ form_data.get('tool_url', '') }}">

        <label for="issue_type">Issue type *</label>
        <select id="issue_type" name="issue_type" required>
            <option value="">Select one</option>
            <option value="Bug" {% if form_data.get('issue_type') == 'Bug' %}selected{% endif %}>Bug</option>
            <option value="Feature request" {% if form_data.get('issue_type') == 'Feature request' %}selected{% endif %}>Feature request</option>
            <option value="Documentation problem" {% if form_data.get('issue_type') == 'Documentation problem' %}selected{% endif %}>Documentation problem</option>
            <option value="Support request" {% if form_data.get('issue_type') == 'Support request' %}selected{% endif %}>Support request</option>
        </select>

        <label for="summary">Short summary *</label>
        <input type="text" id="summary" name="summary" required value="{{ form_data.get('summary', '') }}">

        <label for="description">Problem description *</label>
        <textarea id="description" name="description" required>{{ form_data.get('description', '') }}</textarea>

        <label for="steps_tried">Steps already tried</label>
        <textarea id="steps_tried" name="steps_tried">{{ form_data.get('steps_tried', '') }}</textarea>

        <label for="expected_result">Expected result</label>
        <textarea id="expected_result" name="expected_result">{{ form_data.get('expected_result', '') }}</textarea>

        <label for="actual_result">Actual result</label>
        <textarea id="actual_result" name="actual_result">{{ form_data.get('actual_result', '') }}</textarea>

        <button type="submit">Submit test</button>
    </form>

    {% if result %}
    <div class="result {% if is_error %}error{% endif %}">{{ result }}</div>
    {% endif %}
</body>
</html>
"""


def build_task_title(form_data: dict) -> str:
    return f"[TEST] {form_data['tool_name']} - {form_data['issue_type']} - {form_data['summary']}"


def build_task_description(form_data: dict) -> str:
    return f"""
This task was submitted via the GLAM Tool Hospital test form.

Reporter: {form_data['name']}
Contact: {form_data['email']}
Tool: {form_data['tool_name']}
Tool URL: {form_data.get('tool_url') or 'Not provided'}
Issue type: {form_data['issue_type']}

Problem description:
{form_data['description']}

Steps already tried:
{form_data.get('steps_tried') or 'Not provided'}

Expected result:
{form_data.get('expected_result') or 'Not provided'}

Actual result:
{form_data.get('actual_result') or 'Not provided'}
""".strip()


def build_transactions(title: str, description: str, project_phids=None, priority=None):
    transactions = [
        {"type": "title", "value": title},
        {"type": "description", "value": description},
    ]

    if project_phids:
        transactions.append({
            "type": "projects.set",
            "value": project_phids,
        })

    if priority is not None:
        transactions.append({
            "type": "priority",
            "value": priority,
        })

    return transactions


def build_payload_preview(title: str, description: str, project_phids=None, priority=None):
    return {
        "api.token": "[hidden]" if API_TOKEN else "[not set]",
        "transactions": build_transactions(
            title=title,
            description=description,
            project_phids=project_phids,
            priority=priority,
        ),
    }


def build_conduit_form_payload(title: str, description: str, project_phids=None, priority=None):
    transactions = build_transactions(
        title=title,
        description=description,
        project_phids=project_phids,
        priority=priority,
    )

    payload = {
        "api.token": API_TOKEN,
    }

    for i, txn in enumerate(transactions):
        payload[f"transactions[{i}][type]"] = txn["type"]

        value = txn["value"]

        if isinstance(value, list):
            for j, item in enumerate(value):
                payload[f"transactions[{i}][value][{j}]"] = item
        else:
            payload[f"transactions[{i}][value]"] = value

    return payload


def create_task(title: str, description: str, project_phids=None, priority=None):
    if not API_TOKEN:
        raise RuntimeError("PHABRICATOR_API_TOKEN is not set")

    payload = build_conduit_form_payload(
        title=title,
        description=description,
        project_phids=project_phids,
        priority=priority,
    )

    print("Live payload:", payload)

    response = requests.post(
        PHABRICATOR_URL,
        data=payload,
        headers=HEADERS,
        timeout=30
    )

    print("Status code:", response.status_code)
    print("Response text:", response.text)

    response.raise_for_status()

    data = response.json()

    if data.get("error_code"):
        raise RuntimeError(f"{data['error_code']}: {data.get('error_info')}")

    return data["result"]


def render_page(result=None, is_error=False, form_data=None):
    return render_template_string(
        HTML_FORM,
        result=result,
        is_error=is_error,
        form_data=form_data or {},
        mode_label="Dry run" if DRY_RUN else "Live submission",
        token_status="Yes" if API_TOKEN else "No",
        project_status="Yes" if PROJECT_PHID else "No",
    )


@app.route("/", methods=["GET"])
def home():
    return render_page()


@app.route("/health", methods=["GET"])
def health():
    return {
        "ok": True,
        "dry_run": DRY_RUN,
        "has_api_token": bool(API_TOKEN),
        "has_project_phid": bool(PROJECT_PHID),
        "env_path": str(ENV_PATH),
        "phabricator_base_url": PHABRICATOR_BASE_URL,
    }


@app.route("/submit", methods=["POST"])
def submit():
    try:
        form_data = request.form.to_dict()
        print("Received form data:", form_data)

        required_fields = [
            "name",
            "email",
            "tool_name",
            "issue_type",
            "summary",
            "description",
        ]
        missing = [
            field for field in required_fields
            if not form_data.get(field, "").strip()
        ]

        if missing:
            return render_page(
                result=f"Missing required fields: {', '.join(missing)}",
                is_error=True,
                form_data=form_data,
            ), 400

        title = build_task_title(form_data)
        description = build_task_description(form_data)

        project_phids = [PROJECT_PHID] if PROJECT_PHID else None
        priority = None

        payload_preview = build_payload_preview(
            title=title,
            description=description,
            project_phids=project_phids,
            priority=priority,
        )

        if DRY_RUN:
            dry_run_output = (
                "Dry run only. No task was created.\n\n"
                f"Title:\n{title}\n\n"
                f"Description:\n{description}\n\n"
                f"Payload preview:\n{pformat(payload_preview, width=100)}"
            )
            return render_page(
                result=dry_run_output,
                is_error=False,
                form_data=form_data,
            )

        result = create_task(
            title=title,
            description=description,
            project_phids=project_phids,
            priority=priority,
        )

        return render_page(
            result=f"Live task created successfully.\n\nResult:\n{pformat(result, width=100)}",
            is_error=False,
            form_data={},
        )

    except Exception as e:
        return render_page(
            result=f"Error: {str(e)}",
            is_error=True,
            form_data=request.form.to_dict(),
        ), 500


if __name__ == "__main__":
    app.run(debug=True)