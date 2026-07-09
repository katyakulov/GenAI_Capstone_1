import sqlite3
from pathlib import Path
import random
from datetime import datetime, timedelta
from faker import Faker

DB_PATH = Path(__file__).with_name('sales_support.db')
fake = Faker()
random.seed(42)

regions = ['North', 'South', 'East', 'West', 'Central']
segments = ['SMB', 'Mid-Market', 'Enterprise']
products = ['Analytics Suite', 'CRM Pro', 'Security Monitor', 'Cloud Backup', 'AI Assistant']
statuses = ['open', 'won', 'lost', 'renewal']
priorities = ['low', 'medium', 'high', 'urgent']

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.executescript('''
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS deals;
DROP TABLE IF EXISTS support_tickets;

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    company_name TEXT NOT NULL,
    region TEXT NOT NULL,
    segment TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE deals (
    deal_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    product TEXT NOT NULL,
    deal_value REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    close_date TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE support_tickets (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL,
    github_issue_url TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
);
''')

base_date = datetime.now() - timedelta(days=730)
for i in range(1, 601):
    created = base_date + timedelta(days=random.randint(0, 730))
    cur.execute(
        'INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?)',
        (i, fake.company(), random.choice(regions), random.choice(segments), fake.company_email(), created.date().isoformat())
    )

for i in range(1, 1601):
    created = base_date + timedelta(days=random.randint(0, 730))
    status = random.choices(statuses, weights=[0.18, 0.48, 0.20, 0.14])[0]
    close_date = (created + timedelta(days=random.randint(7, 120))).date().isoformat() if status in ['won', 'lost', 'renewal'] else None
    value = round(random.uniform(1200, 95000), 2)
    cur.execute(
        'INSERT INTO deals VALUES (?, ?, ?, ?, ?, ?, ?)',
        (i, random.randint(1, 600), random.choice(products), value, status, created.date().isoformat(), close_date)
    )

for _ in range(120):
    created = base_date + timedelta(days=random.randint(0, 730))
    cur.execute(
        '''INSERT INTO support_tickets (customer_id, title, description, priority, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (random.randint(1, 600), fake.sentence(nb_words=6), fake.paragraph(nb_sentences=3), random.choice(priorities), random.choice(['new','in_progress','resolved']), created.date().isoformat())
    )

conn.commit()
conn.close()
print(f'Created {DB_PATH}')
