# REACTIV-Application

*This repository contains all the source code for the Django REACTIV application*

## Requirements

- Python 3.11.5 must be installed on your machine.
- (Optional) [Pipenv](https://pipenv.pypa.io/en/latest/install/) for managing the virtual environment.

## Installation and Launch

- Download the project

```bash
git clone https://github.com/camm22/RH-Bot-Hackathon.git
```

- Create the virtual environment

```bash
python -m venv .venv
```

1) Activate venv on Windows

```bash
.\venv\Scripts\activate
```

2) Activate venv on MacOS or Linux

```bash
source venv/bin/activate
```

- Install libraries

```bash
pip install -r requirements.txt
```

- Launch the project

```bash
python manage.py runserver
```

- URL : <http://127.0.0.1:8000>

## To recreate the database

```bash
python manage.py makemigrations

python manage.py migrate

python manage.py createsuperuser
```

## Login to the admin section

- URL : <http://127.0.0.1:8000/admin>
- Username (default) : admin
- Email (default) : <admin@gmail.com>
- Password (default) : admin
