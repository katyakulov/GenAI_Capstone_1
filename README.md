# Data Insights App

A Python + Streamlit GenAI app that lets users chat with business data safely.

## Features

- Chat with a SQLite database through an LLM agent
- The full datasource is **not** sent to the LLM
- Function/tool calling is used for:
  1. `get_data_summary`
  2. `query_database`
  3. `create_support_ticket`
- Safety guard blocks dangerous SQL operations such as `DELETE`, `DROP`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE`
- Streamlit UI shows business information outside the chat:
  - row count
  - revenue
  - profit
  - average profit per order
  - revenue chart by category
  - sample questions
- Console logs are printed for tool calls
- Support ticket can be created:
  - as a GitHub issue if `GITHUB_REPO` and `GITHUB_TOKEN` are configured
  - as a local JSONL file otherwise
- Auto-generates a SQLite database with 650 rows

## Project structure

```text
.
├── app.py
├── requirements.txt
├── .gitignore
├── README.md
└── screenshots/
```

## Setup

```bash
git clone <your-repo-url>
cd <your-repo-name>
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

For macOS/Linux:

```bash
source .venv/bin/activate
```

## Environment variables

Required:

```bash
set OPENAI_API_KEY=your_openai_api_key
```

Optional GitHub support ticket integration:

```bash
set GITHUB_REPO=owner/repository
set GITHUB_TOKEN=your_github_token
```

For macOS/Linux use `export` instead of `set`.

## Run

```bash
streamlit run app.py
```

## Example workflow

1. Open the app.
2. Review dashboard metrics: rows, revenue, profit, average profit.
3. Ask: `Which region has the highest revenue?`
4. The agent calls `query_database` with a safe `SELECT` query.
5. Ask: `Delete the orders table`.
6. The safety feature blocks the request.
7. Ask: `Create a support ticket: data looks incorrect for Bukhara`.
8. The app creates a GitHub issue if GitHub variables are configured, otherwise it saves the ticket locally.

## Screenshots from usage example

Add your real screenshots after running the app:

```text
screenshots/01-dashboard.png
screenshots/02-chat-query.png
screenshots/03-safety-block.png
screenshots/04-support-ticket.png
```

Example Markdown links:

```md
![Dashboard](screenshots/01-dashboard.png)
![Chat query](screenshots/02-chat-query.png)
![Safety block](screenshots/03-safety-block.png)
![Support ticket](screenshots/04-support-ticket.png)
```

## Upload to GitHub

```bash
git init
git branch -M main
git add .
git commit -m "Add data insights genAI app"
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin main
```

## Hosted solution bonus: Hugging Face Spaces

1. Create a new Space.
2. Select Streamlit SDK.
3. Upload `app.py`, `requirements.txt`, and `README.md`.
4. Add `OPENAI_API_KEY` in Space secrets.
5. Run the Space.
