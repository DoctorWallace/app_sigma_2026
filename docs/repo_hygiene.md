# Repo hygiene

## Why db.sqlite3 and media/ should not be versioned

- db.sqlite3 is a local development database that changes frequently. Committing it causes noisy diffs and risks leaking local data or credentials.
- media/ contains user uploads and generated files. These are environment-specific, can be large, and should be handled by storage/backups, not git.

## How to recreate the database locally

1) Run migrations:

```bash
python manage.py migrate
```

2) Create a superuser:

```bash
python manage.py createsuperuser
```

## If these files are already tracked

Run these commands once to stop tracking them (the files remain on disk):

```bash
git rm --cached db.sqlite3
git rm -r --cached media
```
