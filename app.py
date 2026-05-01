from flask import Flask, request, render_template

from config import (
    DRY_RUN,
    IMPACT_OPTIONS,
    ISSUE_TYPE_OPTIONS,
    MAX_SCREENSHOTS,
    MAX_UPLOAD_SIZE_BYTES,
    PROJECT_TAG_OPTIONS,
)

from forms import (
    build_task_description,
    build_task_title,
    get_project_phids_for_submission,
)

from phabricator import (
    count_grouped_tasks,
    create_task,
    fetch_project_tasks,
    filter_tasks_by_tool,
    group_tasks_by_status,
    upload_screenshots,
    utc_now_string,
)


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE_BYTES


def render_form(message=None, is_error=False, form_data=None):
    return render_template(
        "index.html",
        message=message,
        is_error=is_error,
        form_data=form_data or {},
        issue_type_options=ISSUE_TYPE_OPTIONS,
        project_tag_options=PROJECT_TAG_OPTIONS,
        impact_options=IMPACT_OPTIONS,
        max_screenshots=MAX_SCREENSHOTS,
    )


@app.route("/", methods=["GET"])
def home():
    return render_form()


@app.route("/submit", methods=["POST"])
def submit():
    try:
        form_data = request.form.to_dict()

        required_fields = [
            "wiki_username",
            "project_tag",
            "issue_type",
            "summary",
            "description",
        ]

        missing = [
            field
            for field in required_fields
            if not form_data.get(field, "").strip()
        ]

        if missing:
            return render_form(
                message=f"Missing required fields: {', '.join(missing)}",
                is_error=True,
                form_data=form_data,
            ), 400

        uploaded_files = []

        if not DRY_RUN:
            uploaded_files = upload_screenshots(
                request.files.getlist("screenshots")
            )

        title = build_task_title(form_data)
        description = build_task_description(
            form_data=form_data,
            uploaded_files=uploaded_files,
        )
        project_phids = get_project_phids_for_submission(form_data)

        if DRY_RUN:
            return render_form(
                message="Test submission received. No live ticket was created because dry-run mode is enabled.",
                is_error=False,
                form_data=form_data,
            )

        result = create_task(
            title=title,
            description=description,
            project_phids=project_phids,
        )

        task_url = result.get("task_url", "")

        if task_url:
            message = f"Ticket posted successfully: {task_url}"
        else:
            message = "Ticket posted successfully."

        return render_form(
            message=message,
            is_error=False,
            form_data={},
        )

    except Exception as e:
        return render_form(
            message=f"Something went wrong: {str(e)}",
            is_error=True,
            form_data=request.form.to_dict(),
        ), 500


@app.route("/board", methods=["GET"])
def board():
    error = None
    current_filter = request.args.get("tool", "").strip()

    quick_filters = [
        "OpenRefine",
        "Pattypan",
        "GLAMorgan",
        "ISA",
        "BHL",
        "Mix'n'match",
        "Wikidata",
        "Commons",
        "TemplateWizard",
    ]

    grouped = {
        "Open": [],
        "Stalled": [],
        "Resolved / Closed": [],
    }

    total_count = 0
    shown_count = 0

    try:
        tasks = fetch_project_tasks()
        total_count = len(tasks)

        filtered_tasks = filter_tasks_by_tool(tasks, current_filter)
        grouped = group_tasks_by_status(filtered_tasks)
        shown_count = count_grouped_tasks(grouped)

    except Exception as e:
        error = str(e)

    return render_template(
        "board.html",
        grouped=grouped,
        refreshed_at=utc_now_string(),
        error=error,
        current_filter=current_filter,
        quick_filters=quick_filters,
        total_count=total_count,
        shown_count=shown_count,
    )


if __name__ == "__main__":
    app.run(debug=True)