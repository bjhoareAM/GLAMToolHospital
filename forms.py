import os

from config import PROJECT_PHID, PROJECT_TAG_OPTIONS, PRIORITY_OPTIONS


def normalize_wiki_username(raw_username: str) -> str:
    username = (raw_username or "").strip()

    while username.lower().startswith("user:"):
        username = username[5:].strip()

    return username


def format_wiki_username(raw_username: str) -> str:
    username = normalize_wiki_username(raw_username)

    if not username:
        return ""

    return f"User:{username}"


def clean_value(value) -> str:
    return (value or "").strip()


def add_field(lines: list[str], label: str, value):
    value = clean_value(value)

    if value:
        lines.append(f"**{label}:** {value}")


def add_block(lines: list[str], heading: str, value):
    value = clean_value(value)

    if value:
        lines.extend([
            "",
            f"**{heading}**",
            "",
            value,
        ])


def get_project_tag_label(project_tag_value: str) -> str:
    for option in PROJECT_TAG_OPTIONS:
        if option["value"] == project_tag_value:
            return option["label"]

    return project_tag_value or ""


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


def get_phabricator_priority(priority_value: str):
    for option in PRIORITY_OPTIONS:
        if option["value"] == priority_value:
            return option.get("phabricator_priority")

    return None


def get_priority_label(priority_value: str) -> str:
    for option in PRIORITY_OPTIONS:
        if option["value"] == priority_value:
            return option["label"]

    return ""


def build_task_title(form_data: dict) -> str:
    project_label = get_project_tag_label(form_data.get("project_tag"))

    return (
        f"{project_label} - "
        f"{form_data['issue_type']} - "
        f"{form_data['summary']}"
    )


def build_uploaded_files_text(uploaded_files: list[dict]) -> str:
    if not uploaded_files:
        return ""

    blocks = []

    for uploaded in uploaded_files:
        filename = uploaded["filename"]

        if uploaded.get("phabricator_markup"):
            file_markup = uploaded["phabricator_markup"]

            # Put the file reference on its own line so Phabricator is more
            # likely to render image uploads as an embedded preview.
            # Example: {F123456, size=full}
            if file_markup.startswith("{F") and file_markup.endswith("}"):
                file_markup = file_markup[:-1] + ", size=full}"

            blocks.append(
                f"**{filename}**\n\n{file_markup}"
            )
        else:
            blocks.append(
                f"**{filename}**\n\nUploaded to Phabricator; identifier: {uploaded['identifier']}"
            )

    return "\n\n".join(blocks)


def build_task_description(form_data: dict, uploaded_files=None) -> str:
    project_label = get_project_tag_label(form_data.get("project_tag"))
    uploaded_files_text = build_uploaded_files_text(uploaded_files or [])

    lines = [
        "This task was submitted via the GLAM Tool Hospital reporting form.",
        "",
        "Note: This task was created automatically by the GLAM Tool Hospital bot account. The submitter listed below is the person who provided the report, if supplied.",
        "",
        "**Reporter**",
    ]

    add_field(lines, "Wiki username", format_wiki_username(form_data.get("wiki_username")))
    add_field(lines, "Email", form_data.get("email"))

    lines.extend([
        "",
        "**Tool or project area**",
    ])

    add_field(lines, "Tool/project area", project_label)
    add_field(lines, "Tool name", form_data.get("tool_name"))
    add_field(lines, "Tool URL", form_data.get("tool_url"))

    lines.extend([
        "",
        "**Request type**",
    ])

    add_field(lines, "Issue type", form_data.get("issue_type"))
    add_field(lines, "Priority", get_priority_label(form_data.get("priority")))
    add_field(lines, "Impact", form_data.get("impact"))

    add_block(lines, "Summary", form_data.get("summary"))
    add_block(lines, "What was the person trying to do?", form_data.get("goal"))
    add_block(lines, "What happened?", form_data.get("description"))
    add_block(lines, "What did they expect to happen?", form_data.get("expected_result"))
    add_block(lines, "What actually happened?", form_data.get("actual_result"))
    add_block(lines, "Steps already tried", form_data.get("steps_tried"))

    if uploaded_files_text:
        lines.extend([
            "",
            "**Screenshots or supporting files**",
            "",
            uploaded_files_text,
        ])

    add_block(lines, "Links, examples, or extra context", form_data.get("extra_context"))

    lines.extend([
        "",
        "**Internal routing metadata**",
    ])

    add_field(lines, "Project tag", form_data.get("project_tag"))
    add_field(lines, "Priority value", form_data.get("priority"))

    return "\n".join(lines).strip()