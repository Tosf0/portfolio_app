# Portfolio App

Basic web application for displaying applications in a portfolio and their integrations utilising Django framework. It also features an AI assistant that can answer questions about the applications, create analysis and generate Mermaid diagrams for them.

## Setup

1. Clone the repository
2. Create and activate virtual environment: `python -m venv venv` → `venv\Scripts\activate` (Windows) / `source venv/bin/activate` (Linux/Mac)
3. Install dependencies: check `requirements.txt` or use `pip install -r requirements.txt`
4. Create `.env` file based on `.env.example` and fill in your API keys & preferred LLM provider (OpenAI or Anthropic)
5. Migrate database: `python manage.py migrate`
6. Seed database: `python manage.py seed_catalog --flush` (the `--flush` flag clears existing data before seeding)
7. Run development server: `python manage.py runserver`

## Usage

- **Dashboard** (`/`) — overview of the portfolio: KPIs, charts by type/criticality/status, tech debt summary
- **Applications** (`/apps/`) — filterable list of all applications (by type, criticality, status, domain, search)
- **Application Detail** (`/apps/<id>/`) — full detail of an application: ownership, tech stack, environments, integrations
  - **Generate Diagram** — button on detail page generates a Mermaid integration diagram via LLM
- **AI Analysis** (`/analysis/`) — runs a predefined portfolio analysis prompt via LLM (streaming response)
- **Q&A** (`/qa/`) — conversational chat about portfolio data, answers based on relevant data subset from DB
