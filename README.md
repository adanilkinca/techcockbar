# TechCockBar

Django project for cocktail recipes.

## Quickstart
```bash
python -m venv .venv
. .venv/Scripts/activate      # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env        # then edit .env with real values
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver


