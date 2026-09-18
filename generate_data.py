import sqlite3
import os
from dotenv import load_dotenv
import openai
from openai import OpenAI
import random
from datetime import datetime, timedelta

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.5-flash-lite"

# ----- Generate quantitative data -----
conn = sqlite3.connect("data/delight.db")
cur = conn.cursor()

print("Generating quantitative data...")

print("Creating regions table...")
cur.execute("""
CREATE TABLE regions (
    region_id INTEGER PRIMARY KEY,
    region_code TEXT UNIQUE,
    region_name TEXT
);
""")

REGIONS = [
    ("US-NE", "United States - Northeast"),
    ("US-W", "United States - West"),
    ("US-MW", "United States - Midwest"),
    ("US-S", "United States - South")
]

for region_id, (region_code, region_name) in enumerate(REGIONS, start=1):
    cur.execute("INSERT OR IGNORE INTO regions (region_id, region_code, region_name) VALUES (?, ?, ?)", (region_id, region_code, region_name))

START_YEAR = 2022
END_YEAR = 2025

# Revenue by region (monthly)
print("Creating revenues table...")
cur.execute("""
CREATE TABLE revenues (
    id INTEGER PRIMARY KEY,
    region_code TEXT REFERENCES regions(region_code),
    date TEXT,
    amount REAL
);
""")

start_revenue = {}

for region_code, _ in REGIONS:
    curr_amt = random.randint(20000, 500000)
    start_revenue[region_code] = curr_amt
    for year in range(START_YEAR, END_YEAR + 1):
        for month in range(1, 13):
            date = f"{year}-{month:02d}"
            cur.execute("INSERT INTO revenues (region_code, date, amount) VALUES (?, ?, ?)", (region_code, date, curr_amt))
            curr_amt = round(curr_amt * random.uniform(0.95, 1.08), 2)
        
# Costs by category by region (monthly)
print("Creating costs table...")
cur.execute("""
CREATE TABLE costs (
    id INTEGER PRIMARY KEY,
    region_code TEXT REFERENCES regions(region_code),
    date TEXT,
    amount REAL
);
""")

for region_code, _ in REGIONS:
    curr_amt = round(start_revenue.get(region_code) * random.uniform(0.8, 0.95), 2)
    for year in range(START_YEAR, END_YEAR + 1):
        for month in range(1, 13):
            date = f"{year}-{month:02d}"
            cur.execute("INSERT INTO costs (region_code, date, amount) VALUES (?, ?, ?)", (region_code, date, curr_amt))
            curr_amt = round(curr_amt * random.uniform(0.98, 1.10), 2)

# Sales records
print("Creating sales table...")
cur.execute("""
CREATE TABLE sales (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    date TEXT,
    region_code TEXT REFERENCES regions(region_code),
    amount REAL
);
""")

def generate_random_date(year, month):
    day = random.randint(1, 28) if (month == 2 and not year % 4 == 0) \
        else random.randint(1, 29) if month == 2 \
            else random.randint(1, 30) if month in [4, 6, 9, 11] \
                else random.randint(1, 31)
    return f"{year}-{month:02d}-{day:02d}"

customer_count = 1
for region_code, _ in REGIONS:
    for year in range(START_YEAR, END_YEAR + 1):
        for month in range(1, 13):
            sales_total = cur.execute("SELECT amount FROM revenues WHERE region_code = ? AND date = ?", 
                                    (region_code, f"{year}-{month:02d}")).fetchone()[0]
            sales_remaining = sales_total
            while sales_remaining > 0:
                sale_amt = random.randint(2000, 20000)
                if sale_amt > sales_remaining:
                    sale_amt = sales_remaining

                date = generate_random_date(year, month)
                if random.random() < 0.3:
                    customer_count += 1
                    cur.execute("INSERT INTO sales (customer_id, date, region_code, amount) VALUES (?, ?, ?, ?)", 
                                (customer_count, date, region_code, sale_amt))
                else:
                    cur.execute("INSERT INTO sales (customer_id, date, region_code, amount) VALUES (?, ?, ?, ?)", 
                                (random.randint(1, customer_count), date, region_code, sale_amt))

                sales_remaining -= sale_amt

# Employees
print("Creating employees table...")
cur.execute("""
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    cost_center TEXT,
    salary REAL,
    hire_date TEXT
)
""")

NUM_EMPLOYEES = 300
employees = [(random.choice(["finance", "engineering", "sales", "marketing", "hr"]), random.randint(50000, 150000), 
         generate_random_date(random.randint(2022, 2025), (random.randint(1, 12)))) for _ in range(NUM_EMPLOYEES)]

cur.executemany("INSERT INTO employees (cost_center, salary, hire_date) VALUES (?, ?, ?)", employees)

# Employee satisfaction polling
print("Creating employee satisfaction table...")
cur.execute("""
CREATE TABLE employee_satisfaction (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER REFERENCES employees(id),
    rating INTEGER
)
""")

SURVEY_LIKELIHOOD = 0.4
for employee_id in range(1, NUM_EMPLOYEES + 1):
    if random.random() < SURVEY_LIKELIHOOD:
        rating = random.randint(6, 10)
        cur.execute("INSERT INTO employee_satisfaction (employee_id, rating) VALUES (?, ?)", (employee_id, rating))

# Software ticketing
print("Creating tickets table...")
cur.execute("""
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY,
    category TEXT,
    open_date TEXT,
    close_date TEXT
)
""")

tickets = []
for _ in range(200):
    open_year = random.randint(2022, 2025)
    open_month = random.randint(1, 12)
    open_date = generate_random_date(open_year, open_month)

    open_duration = random.randint(1, 21)
    close_date = datetime.strftime(datetime.strptime(open_date, "%Y-%m-%d") + timedelta(days=open_duration), "%Y-%m-%d")
    tickets.append((random.choice(["bug", "feature request", "support"]), open_date, close_date))

cur.executemany("INSERT INTO tickets (category, open_date, close_date) VALUES (?, ?, ?)", tickets)

# Expense data - employee id, timestamp, expense amount, cost center
print("Creating expense tickets table...")
cur.execute("""
CREATE TABLE expense_tickets (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER REFERENCES employees(id),
    amount REAL
)
""")

expense_tickets = [(random.randint(1, NUM_EMPLOYEES), random.uniform(10, 250)) for _ in range(300)]
cur.executemany("INSERT INTO expense_tickets (employee_id, amount) VALUES (?, ?)", expense_tickets)

conn.commit()
conn.close()

# ----- Generate qualitative data -----

print("Generating qualitative data...")

if not os.path.exists("data/docs"):
    os.makedirs("data/docs")
else:
    print("data/docs already exists. Skipping creation.")

# title, filename, description of documents to generate for the qualitative dataset
DOCS_TO_GEN = [("Security Policy", "security_policy.txt", "This document outlines the security policies and procedures for the organization, including access control, data protection, and incident response."),
               ("Code Review Process", "code_review_process.txt", "This document describes the code review process, including guidelines for submitting code for review, reviewing code, and providing feedback."),
               ("Employee Benefits and Perks", "employee_benefits.txt", "This document outlines the employee benefits and perks offered by the organization, including health insurance, retirement plans, and other perks."),
               ("Customer Satisfaction Guarantee", "customer_satisfaction.txt", "This document describes the organization's customer satisfaction guarantee, including references to the customer complaints process and the company's customer-centric mission statement."),
               ("Customer Complaint Process", "customer_complaint_process.txt", "This] document outlines the process for handling customer complaints, including how to submit a complaint, how complaints are reviewed and resolved, and the expected response time."),
               ("Customer Success Strategies", "customer_success_strategies.txt", "This document outlines the strategies and best practices for ensuring customer success, including onboarding, training, and ongoing support."),
               ("Expense Approval Policy", "expense_approval_policy.txt", "This document outlines the expense approval policy, including when manager approval is needed based on receipt value and expense time.")]

BASE_PROMPT = "You are a technical writer working at a technology services company called Delight. " \
"Your task is to generate detailed corporate policy documents based on the descriptions provided. " \
"Each document should be comprehensive and well-structured."

client = OpenAI(
  api_key=GEMINI_API_KEY,
  base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

for title, filename, description in DOCS_TO_GEN:
    print(f"Generating document: {title}...")
    prompt = BASE_PROMPT + f"Generate a document titled '{title}' based on the following description: {description}."

    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes text."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )

    # Extract and print the summary
    document_content = response.choices[0].message.content
    
    with open(f"data/docs/{filename}", "w") as f:
        f.write(document_content)