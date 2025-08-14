# TechCockBar

Django project for cocktail recipes.

## Quickstart (Windows PowerShell)

```powershell
cd "E:\ShakeThat!\Website\techcockbar"

# Create & activate venv once
py -m venv .venv
.\.venv\Scripts\activate

# Install deps
pip install --upgrade pip
pip install -r requirements.txt

# Create your local .env based on .env.example and fill TiDB password
copy .env.example .env
notepad .env

# Run DB migrations & start
python manage.py migrate
python manage.py runserver


# (optional: if didn't already, before to start server): 
python manage.py createsuperuser



