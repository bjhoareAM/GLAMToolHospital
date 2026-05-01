import base64
from datetime import datetime, timezone

import requests
from werkzeug.utils import secure_filename

from config import (
    API_TOKEN,
    PHABRICATOR_BASE_URL,
    PHABRICATOR_MANIPHEST_EDIT_URL,
    HEADERS,
    PROJECT_PHID,
    FILE_VIEW_POLICY,
    ALLOWED_SCREENSHOT_EXTENSIONS,
    MAX_SCREENSHOTS,
)


def utc_now_string() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def unix_to_string(ts) -> str:
    if not ts:
        return ""

    return datetime.fromtimestamp(
        int(ts),
        tz=timezone.utc,
    ).strftime("%Y-%m-%d %H:%M UTC")


def phab_post(method: str, payload: dict) -> dict:
    if not API_TOKEN:
        raise RuntimeError("PHABRICATOR_API_TOKEN is not set")

    url = f"{PHABRICATOR_BASE_URL}/api/{method}"

    form_payload = {
        "api.token": API_TOKEN,
    }
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


def allowed_screenshot_filename(filename: str) -> bool:
    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_SCREENSHOT_EXTENSIONS


def upload_file_to_phabricator(file_storage) -> dict:
    if not API_TOKEN:
        raise RuntimeError("PHABRICATOR_API_TOKEN is not set")

    original_filename = file_storage.filename or "uploaded-file"
    safe_filename = secure_filename(original_filename)

    if not allowed_screenshot_filename(safe_filename):
        raise RuntimeError(
            f"Unsupported file type for '{original_filename}'. "
            "Supported formats: PNG, JPG, GIF, WEBP, and PDF."
        )

    file_bytes = file_storage.read()

    if not file_bytes:
        raise RuntimeError(f"Uploaded file '{original_filename}' is empty.")

    encoded_file = base64.b64encode(file_bytes).decode("ascii")

    payload = {
        "api.token": API_TOKEN,
        "name": safe_filename,
        "data_base64": encoded_file,
    }

    if FILE_VIEW_POLICY:
        payload["viewPolicy"] = FILE_VIEW_POLICY

    response = requests.post(
        f"{PHABRICATOR_BASE_URL}/api/file.upload",
        data=payload,
        headers=HEADERS,
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()

    if data.get("error_code"):
        raise RuntimeError(f"{data['error_code']}: {data.get('error_info')}")

    file_identifier = data["result"]

    uploaded = {
        "filename": safe_filename,
        "identifier": file_identifier,
        "file_id": None,
        "phabricator_markup": None,
    }

    if isinstance(file_identifier, str) and file_identifier.startswith("PHID-FILE-"):
        try:
            search_result = phab_post(
                "file.search",
                {
                    "constraints[phids][0]": file_identifier,
                    "limit": "1",
                },
            )

            data_items = search_result.get("data", [])

            if data_items:
                file_id = data_items[0].get("id")
                if file_id:
                    uploaded["file_id"] = file_id
                    uploaded["phabricator_markup"] = f"{{F{file_id}}}"

        except Exception:
            uploaded["phabricator_markup"] = None

    return uploaded


def upload_screenshots(files) -> list[dict]:
    selected_files = [
        file
        for file in files
        if file and file.filename
    ]

    if len(selected_files) > MAX_SCREENSHOTS:
        raise RuntimeError(f"You can upload a maximum of {MAX_SCREENSHOTS} files.")

    uploaded_files = []

    for file_storage in selected_files:
        uploaded_files.append(upload_file_to_phabricator(file_storage))

    return uploaded_files


def build_transactions(title: str, description: str, project_phids=None, priority=None):
    transactions = [
        {"type": "title", "value": title},
        {"type": "description", "value": description},
    ]

    if project_phids:
        transactions.append(
            {
                "type": "projects.set",
                "value": project_phids,
            }
        )

    if priority is not None:
        transactions.append(
            {
                "type": "priority",
                "value": priority,
            }
        )

    return transactions


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

    response = requests.post(
        PHABRICATOR_MANIPHEST_EDIT_URL,
        data=payload,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()

    if data.get("error_code"):
        raise RuntimeError(f"{data['error_code']}: {data.get('error_info')}")

    result = data["result"]

    object_info = result.get("object", {}) if isinstance(result, dict) else {}
    task_id = object_info.get("id")

    if task_id:
        result["task_url"] = f"{PHABRICATOR_BASE_URL}/T{task_id}"

    return result


def fetch_project_tasks() -> list[dict]:
    if not PROJECT_PHID:
        raise RuntimeError("PHABRICATOR_PROJECT_PHID is not set")

    payload = {
        "constraints[projects][0]": PROJECT_PHID,
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

        tasks.append(
            {
                "id": f"T{task_id}",
                "title": title,
                "status": status_info.get("name", "Unknown"),
                "priority": priority_info.get("name", "Unknown"),
                "updated": unix_to_string(fields.get("dateModified")),
                "url": f"{PHABRICATOR_BASE_URL}/T{task_id}",
            }
        )

    return tasks


def filter_tasks_by_tool(tasks: list[dict], tool_filter: str) -> list[dict]:
    if not tool_filter:
        return tasks

    needle = tool_filter.strip().lower()

    return [
        task
        for task in tasks
        if needle in task.get("title", "").lower()
    ]


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


def count_grouped_tasks(grouped: dict) -> int:
    return sum(len(tasks) for tasks in grouped.values())