# GLAM Tool Hospital

GLAM Tool Hospital is a prototype Flask application for supporting issue reporting and issue tracking for Wikimedia and GLAM related tools.

The project currently includes:

- a form based interface for generating and submitting Phabricator tasks
- a live tracker view for tasks associated with a configured Phabricator project
- a small testing script for querying project information from Phabricator

## Current project structure

```text
glam-tool-hospital/
├── app.py
├── app_board.py
├── phabricator_test.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── docs/
├── static/
└── templates/ 
```
