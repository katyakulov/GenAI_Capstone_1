import os, json, sqlite3, random, logging, requests
from datetime import date, timedelta
import pandas as pd
import streamlit as st
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
DB = "sales.db"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY, order_date TEXT, region TEXT, category TEXT,
        customer_type TEXT, channel TEXT, revenue REAL, cost REAL, quantity INTEGER)""")
    if cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0] < 500:
        cur.execute("DELETE FROM orders")
        regions = ["Tashkent","Samarkand","Bukhara","Fergana","Andijan","Khiva"]
        cats = ["Chocolate boxes","Date bars","Halva candies","Corporate gifts"]
        types = ["Retail","Cafe","Corporate","Marketplace"]
        channels = ["Instagram","Telegram","Uzum","Direct","Partner"]
        rows = []
        for i in range(650):
            d = date.today() - timedelta(days=random.randint(0, 365))
            qty = random.randint(1, 40)
            price = random.uniform(18000, 145000)
            rev = qty * price
            cost = rev * random.uniform(0.42, 0.72)
            rows.append((d.isoformat(), random.choice(regions), random.choice(cats),
                         random.choice(types), random.choice(channels), rev, cost, qty))
        cur.executemany("""INSERT INTO orders(order_date,region,category,customer_type,
            channel,revenue,cost,quantity) VALUES (?,?,?,?,?,?,?,?)""", rows)
    con.commit(); con.close()

def safe_sql(sql: str) -> str:
    s = sql.strip().rstrip(";")
    banned = ["delete","drop","insert","update","alter","truncate","replace","attach","detach","pragma"]
    if not s.lower().startswith("select") or any(b in s.lower() for b in banned):
        raise ValueError("Blocked unsafe operation. Only read-only SELECT queries are allowed.")
    if "limit" not in s.lower():
        s += " LIMIT 20"
    return s

def query_database(sql: str) -> dict:
    logging.info("Tool call: query_database(%s)", sql)
    sql = safe_sql(sql)
    con = sqlite3.connect(DB)
    df = pd.read_sql_query(sql, con)
    con.close()
    return {"sql": sql, "rows": df.to_dict(orient="records")}

def get_data_summary() -> dict:
    logging.info("Tool call: get_data_summary")
    con = sqlite3.connect(DB)
    row = pd.read_sql_query("""SELECT COUNT(*) rows_count, ROUND(SUM(revenue),2) revenue,
        ROUND(SUM(revenue-cost),2) profit, ROUND(AVG(revenue-cost),2) avg_profit FROM orders""", con)
    by_cat = pd.read_sql_query("""SELECT category, ROUND(SUM(revenue),2) revenue
        FROM orders GROUP BY category ORDER BY revenue DESC""", con)
    con.close()
    return {"summary": row.to_dict(orient="records")[0], "revenue_by_category": by_cat.to_dict(orient="records")}

def create_support_ticket(title: str, body: str) -> dict:
    logging.info("Tool call: create_support_ticket(%s)", title)
    repo, token = os.getenv("GITHUB_REPO"), os.getenv("GITHUB_TOKEN")
    if repo and token:
        r = requests.post(f"https://api.github.com/repos/{repo}/issues",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"title": title, "body": body, "labels": ["support","data-insights-app"]}, timeout=20)
        if r.status_code >= 400:
            return {"status": "error", "message": r.text[:300]}
        return {"status": "created", "url": r.json().get("html_url")}
    with open("support_tickets.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"title": title, "body": body}) + "\n")
    return {"status": "saved_locally", "file": "support_tickets.jsonl"}

tools = [
 {"type":"function","function":{"name":"get_data_summary","description":"Return safe aggregated datasource statistics.","parameters":{"type":"object","properties":{},"additionalProperties":False}}},
 {"type":"function","function":{"name":"query_database","description":"Run a read-only SQLite SELECT query against the orders table. Never use dangerous operations.","parameters":{"type":"object","properties":{"sql":{"type":"string"}},"required":["sql"],"additionalProperties":False}}},
 {"type":"function","function":{"name":"create_support_ticket","description":"Create a support ticket when the user asks for human support or the agent cannot solve the request.","parameters":{"type":"object","properties":{"title":{"type":"string"},"body":{"type":"string"}},"required":["title","body"],"additionalProperties":False}}}
]
tool_map = {"get_data_summary": get_data_summary, "query_database": query_database, "create_support_ticket": create_support_ticket}

def ask_agent(user_text: str) -> str:
    messages = [{"role":"system","content":"""You are a safe data insights assistant.
Use function calls for database questions. Do not invent data.
Never ask to delete, modify, or expose the full database.
Only small aggregated results or limited query outputs may be returned.
Suggest a support ticket if the request is unclear, impossible, or needs a human.
Database table: orders(id, order_date, region, category, customer_type, channel, revenue, cost, quantity)."""}]
    messages += st.session_state.history[-8:]
    messages.append({"role":"user","content":user_text})
    for _ in range(4):
        resp = client.chat.completions.create(model=os.getenv("OPENAI_MODEL","gpt-4.1-mini"),
                                             messages=messages, tools=tools, tool_choice="auto")
        msg = resp.choices[0].message
        messages.append(msg)
        if not msg.tool_calls:
            return msg.content or ""
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            try:
                result = tool_map[call.function.name](**args)
            except Exception as e:
                result = {"error": str(e)}
            messages.append({"role":"tool","tool_call_id":call.id,"content":json.dumps(result)})
    return "I could not complete this safely. Would you like me to create a support ticket?"

init_db()
st.set_page_config(page_title="Data Insights App", layout="wide")
st.title("📊 Data Insights App")
st.caption("Chat with business data using safe function calling. Raw database is not sent to the LLM.")

summary = get_data_summary()
s = summary["summary"]
c1,c2,c3,c4 = st.columns(4)
c1.metric("Rows", f"{s['rows_count']:,}")
c2.metric("Revenue", f"{s['revenue']:,.0f}")
c3.metric("Profit", f"{s['profit']:,.0f}")
c4.metric("Avg profit/order", f"{s['avg_profit']:,.0f}")

left, right = st.columns([2,1])
with right:
    st.subheader("Revenue by category")
    st.bar_chart(pd.DataFrame(summary["revenue_by_category"]).set_index("category"))
    st.subheader("Sample queries")
    st.write("- Which region has highest revenue?")
    st.write("- Show monthly profit trend.")
    st.write("- Create a support ticket about wrong data.")
    if st.button("Create support ticket"):
        st.session_state.pending_ticket = True

if "history" not in st.session_state: st.session_state.history = []
with left:
    for m in st.session_state.history:
        with st.chat_message(m["role"]):
            st.write(m["content"])
    if prompt := st.chat_input("Ask about the data..."):
        st.session_state.history.append({"role":"user","content":prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            with st.status("Calling tools and analyzing data...", expanded=False):
                answer = ask_agent(prompt)
            st.write(answer)
        st.session_state.history.append({"role":"assistant","content":answer})
