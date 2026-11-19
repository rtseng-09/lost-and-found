# Campus Lost & Found

A Flask + SQLite site where anyone can browse items found on campus, and logged-in
users post items (what, where, when, photo URL) and mark their own posts as returned.
Features: search box, "only unclaimed" filter, per-user pages, registration/login,
input validation with clear error messages. The database is seeded with fictitious
data on first run (demo logins: `maya`, `jordan`, `sam`, password `password123`).

## Run on a laptop
    python -m venv .venv
    source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python app.py                    # open http://127.0.0.1:5000

## Deploy to Cloud Run
    gcloud run deploy lost-and-found --source . --region us-central1 --allow-unauthenticated \
      --set-env-vars SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(16))"),DB_PATH=/tmp/lostfound.db
    gcloud run services delete lost-and-found --region us-central1   # after grading

Note: Cloud Run's disk is ephemeral, so SQLite data resets when the instance restarts
(the seed data reappears). Locally the data persists in `lostfound.db`.

## Tests
    pip install -r requirements-dev.txt
    pytest

## CI/CD (GitHub Actions)
`.github/workflows/ci-cd.yml` runs the test suite on every pull request to `main`.
On every push/merge to `main` it runs the tests again and, only if they pass,
deploys to Cloud Run (`lost-and-found`, region `us-west1`).

Required repository secrets (Settings → Secrets and variables → Actions):
- `GCP_SA_KEY` – JSON key of the `github-deployer` service account
- `FLASK_SECRET_KEY` – random string used as Flask's `SECRET_KEY`
