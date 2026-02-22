# Portfolio App

Basic web application for displaying portfolio data utilising Django framework.

## Setup

1. Clone the repository
2. Create and activate virtual environment: `python -m venv venv` → `venv\Scripts\activate` (Windows) / `source venv/bin/activate` (Linux/Mac)
3. Install dependencies: check `requirements.txt` or use `pip install -r requirements.txt`
4. Create `.env` file based on `.env.example` and fill in your API keys & preferred LLM provider (OpenAI or Anthropic)
5. Migrate database: `python manage.py migrate`
6. Seed database: `python manage.py seed_catalog --flush` (the `--flush` flag clears existing data before seeding)
7. Run development server: `python manage.py runserver`