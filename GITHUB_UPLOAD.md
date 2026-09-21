# GitHub upload checklist

1. Confirm the repository is private.
2. Confirm `.env`, `data/`, `.venv/`, and database files are absent from `git status`.
3. Initialize and commit this folder if it is not already a Git repository.
4. Add the exact GitHub repository URL as `origin`.
5. Push the `main` branch.
6. Open the GitHub repository and confirm no API keys or database files appear.
7. Connect the private repository to Render.

Do not upload the entire folder through the browser if hidden files are selected. Using Git respects `.gitignore` and is safer for this project.
