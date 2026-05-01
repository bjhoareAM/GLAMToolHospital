import os

from config import PROJECT_PHID, PROJECT_TAG_OPTIONS


def normalize_wiki_username(raw_username: str) -> str:
    username = (raw_username or "").strip()

    while username.lower().startswith("user:"):
        username = username[5:].strip()

    return username


def format_wiki_username(raw_username: str) -> str:
    username = normalize_wiki_username(raw_username)

    if not username:
        return "Not provided"

    return f"User:{username}"


def get_project_tag_label(project_tag_value: str) -> str:
    for option in PROJECT_TAG_OPTIONS:
        if option["value"] == project_tag_value:
            return option["label"]

    return project_tag_value or "Not provided"


def get_project_tag_phid(project_tag_value: str):
    for option in PROJECT_TAG_OPTIONS:
        if option["value"] == project_tag_value:
            phid_env = option.get("phid_env")
            if phid_env:
                return os.getenv(phid_env)

    return None


def get_project_phids_for_submission(form_data: dict):
    project_phids = []

    if PROJECT_PHID:
        project_phids.append(PROJECT_PHID)

    selected_project_phid = get_project_tag_phid(form_data.get("project_tag"))

    if selected_project_phid and selected_project_phid not in project_phids:
        project_phids.append(selected_project_phid)

    return project_phids or None


def build_task_title(form_data: dict) -> str:
    project_label = get_project_tag_label(form_data.get("project_tag"))

    return (
        f"{project_label} - "
        f"{form_data['issue_type']} - "
        f"{form_data['summary']}"
    )


def build_uploaded_files_text(uploaded_files: list[dict]) -> str:
    if not uploaded_files:
        return "Not provided"

    lines = []

    for uploaded in uploaded_files:
        filename = uploaded["filename"]

        if uploaded.get("phabricator_markup"):
            lines.append(f"* {filename}: {uploaded['phabricator_markup']}")
        else:
            lines.append(
                f"* {filename}: uploaded to Phabricator; identifier "
                f"{uploaded['identifier']}"
            )

    return "\n".join(lines)


def build_task_description(form_data: dict, uploaded_files=None) -> str:
    project_label = get_project_tag_label(form_data.get("project_tag"))
    email_value = form_data.get("email") or "Not provided"
    uploaded_files_text = build_uploaded_files_text(uploaded_files or [])

    return f"""
This task was submitted via the GLAM Tool Hospital reporting form.

Note: This task was created automatically by the GLAM Tool Hospital bot account. The submitter listed below is the person who provided the report, if supplied.

== Reporter ==

Wiki username: {format_wiki_username(form_data.get('wiki_username'))}
Email: {email_value}

== Tool or project area ==

Tool/project area: {project_label}
Tool name: {form_data.get('tool_name') or 'Not provided'}
Tool URL: {form_data.get('tool_url') or 'Not provided'}

== Request type ==

Issue type: {form_data['issue_type']}
Impact: {form_data.get('impact') or 'Not provided'}

== Summary ==

{form_data['summary']}

== What was the person trying to do? ==

{form_data.get('goal') or 'Not provided'}

== What happened? ==

{form_data.get('description') or 'Not provided'}

== What did they expect to happen? ==

{form_data.get('expected_result') or 'Not provided'}

== What actually happened? ==

{form_data.get('actual_result') or 'Not provided'}

== Steps already tried ==

{form_data.get('steps_tried') or 'Not provided'}

== Screenshots or supporting files ==

{uploaded_files_text}

== Links, examples, or extra context ==

{form_data.get('extra_context') or 'Not provided'}

== Internal routing metadata ==

Project tag: {form_data.get('project_tag') or 'Not provided'}
""".strip()