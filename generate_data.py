import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
import openai
from openai import OpenAI
import pandas as pd
import math
import markdown
import json
from weasyprint import HTML


load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.5-flash-lite"
OUTPUT_DIR = "./data"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
else:
    print(f"{OUTPUT_DIR} already exists. Skipping creation.")

# ----- Generate quantitative data -----
print("Generating quantitative data...")

START_YEAR = 2022
END_YEAR = 2025

def generate_random_date(year=None, month=None):
    if not year and not month:
        year = random.randint(START_YEAR, END_YEAR)
        month = random.randint(1, 12)
    elif year and not month:
        month = random.randint(1, 12)

    day = random.randint(1, 29) if (month == 2 and (year % 4 == 0)) \
            else random.randint(1, 28) if month == 2 \
                else random.randint(1, 30) if month in [4, 6, 9, 11] \
                    else random.randint(1, 31)

    return f"{year}-{month:02d}-{day:02d}"

def generate_date_after(base_date_str, min_days, max_days):
    open_duration = timedelta(days=random.randint(min_days, max_days))
    close_date = datetime.strftime(datetime.strptime(base_date_str, "%Y-%m-%d") + open_duration, "%Y-%m-%d")

    return close_date

REGION_CODES = ["US-NE", "US-W", "US-MW", "US-S"]

regions_dict = {
    "regionCode": ["US-NE", "US-W", "US-MW", "US-S"],
    "regionName": ["United States - Northeast", "United States - West", 
                   "United States - Midwest", "United States - South"]
}

pd.DataFrame(regions_dict).to_csv(os.path.join(OUTPUT_DIR, "regions.csv"), index=False)

# Sales records
print("Generating sales data...")

sales_rows = []
customer_count = 1
sales_id = 1
new_customer_chance = 0.3
for year in range(START_YEAR, END_YEAR + 1):
    for month in range(1, 13):
        business = random.uniform(0.02, 0.05) # between 20 and 50 customers in a given month
        while True:
            if random.random() < business:
                break # move to next month

            customer_id = math.floor(random.betavariate(5, 2) * customer_count)
            date = generate_random_date(year=year, month=month)
            region = random.choice(REGION_CODES)
            amount = random.randint(1200, 10000)

            if random.random() < new_customer_chance:
                customer_count += 1 # move to the next customer

            sales_rows.append({
                "id": sales_id,
                "customer_id": customer_id,
                "date": date,
                "regionCode": region,
                "amount": amount
            })
            
            sales_id += 1

sales_df = pd.DataFrame(sales_rows)

sales_df.to_csv(os.path.join(OUTPUT_DIR, "sales.csv"), index=False)

# Revenue by region (monthly)
print("Generating revenues data...")

sales_df["month"] = sales_df["date"].str[:7]
revenues_df = (
    sales_df.groupby(["month", "regionCode"], as_index=False)["amount"]
    .sum()
    .rename(columns={"month": "date"})
)
revenues_df.insert(0, "id", range(1, len(revenues_df) + 1))
revenues_df = revenues_df.set_index(["date", "regionCode"])
revenues_df.to_csv(os.path.join(OUTPUT_DIR, "revenues.csv"))

# Costs by region (monthly), based on revenue from the same month.
print("Generating costs data...")

cost_rows = []
cost_id = 1

for regionCode in REGION_CODES:
    for year in range(START_YEAR, END_YEAR + 1):
        for month in range(1, 13):
            date = f"{year}-{month:02d}"
            try:
                monthly_revenue = revenues_df.loc[(date, regionCode), "amount"]

                cost_rows.append({
                                "id": cost_id,
                                "region_code": regionCode,
                                "date": date,
                                "amount": round(monthly_revenue * random.uniform(0.8, 0.95), 2),
                            })
                cost_id += 1
            except KeyError:
                pass

costs_df = pd.DataFrame(cost_rows)
costs_df.to_csv(os.path.join(OUTPUT_DIR, "costs.csv"), index=False)

# Employees
print("Generating employees data...")

NUM_EMPLOYEES = 300
employee_rows = []
for i in range(1, NUM_EMPLOYEES + 1):
    employee_rows.append({
        "id": i,
        "cost_center": random.choice(["finance", "engineering", "sales", "marketing", "hr"]),
        "salary": random.randint(50000, 150000),
        "hire_date": generate_random_date()
    })

pd.DataFrame(employee_rows).to_csv(os.path.join(OUTPUT_DIR, "employees.csv"), index=False)

# Employee satisfaction polling
print("Generating employee satisfaction data...")

satisfaction_rows = []
SURVEY_LIKELIHOOD = 0.4
survey_id = 1
for employee_id in range(1, NUM_EMPLOYEES + 1):
    if random.random() < SURVEY_LIKELIHOOD:
        rating = random.randint(6, 10)
        satisfaction_rows.append({
            "id": survey_id,
            "employee_id": employee_id,
            "rating": rating
        })

        survey_id += 1
        
pd.DataFrame(satisfaction_rows).to_csv(os.path.join(OUTPUT_DIR, "employee_satisfaction.csv"), index=False)

# Software ticketing
print("Generating software tickets data...")

tickets = []
for i in range(200):
    open_date = generate_random_date()
    close_date = generate_date_after(open_date, 1, 21)
    category = random.choice(["bug", "feature request", "support"])

    tickets.append({
        "id": i,
        "category": category,
        "open_date": open_date,
        "close_date": close_date
    })

pd.DataFrame(tickets).to_csv(os.path.join(OUTPUT_DIR, "software_tickets.csv"), index=False)

# Expense data - employee id, timestamp, expense amount, cost center
print("Generating expense data...")

expense_tickets = [{"id": i,
                    "employee_id": random.randint(1, NUM_EMPLOYEES), 
                    "amount": random.uniform(10, 250)
                    } for i in range(1, NUM_EMPLOYEES + 1)]

pd.DataFrame(expense_tickets).to_csv(os.path.join(OUTPUT_DIR, "expense_tickets.csv"), index=False)

# JSON customer support tickets
print("Generating customer support tickets data...")
support_tickets = []
NUM_SUPPORT_TICKETS = 250

for i in range(NUM_SUPPORT_TICKETS):
    open_date = generate_random_date()
    closed = random.choice([True, False])
    close_date = generate_date_after(open_date, 10, 130) if closed else "N/A"
    title = f"{random.choice(["Button", "Input", "Billing", "Functionality"])} is {random.choice(["broken", "slow", "outdated", "confusing"])}"
    messages = []

    # Generate random messages
    client = True
    while random.random() < 0.6:
        if client:
            if len(messages) == 0:
                messages.append(title)
            else:
                messages.append(random.choice([
                    "Help please",
                    "This is really important",
                    "This has been happening for months",
                    "It's no big deal",
                    "Other people have reported this problem",
                    "It's super disruptive to our business"
                ]))
        else:
            messages.append(random.choice([
                "Show me your screen",
                "Please give more detail",
                "Isn't this a duplicate issue",
                "No it's not broken",
                "This is not a priority to fix, sorry"
            ]))
        client = not client

    support_tickets.append({
        "id": i,
        "title": title,
        "open_date": open_date,
        "closed": closed,
        "close_date": close_date,
        "messages": messages
    })

with open(os.path.join(OUTPUT_DIR, "support_tickets.json"), "w") as out:
    json.dump(support_tickets, out)

# ----- Generate qualitative data -----

print("Generating qualitative data...")

# title, filename, description of documents to generate for the qualitative dataset
DOCS_TO_GEN = [("Security Policy", "security_policy.pdf", "This document outlines the security policies and procedures for the organization, including access control, data protection, and incident response."),
               ("Code Review Process", "code_review_process.pdf", "This document describes the code review process, including guidelines for submitting code for review, reviewing code, and providing feedback."),
               ("Employee Benefits and Perks", "employee_benefits.pdf", "This document outlines the employee benefits and perks offered by the organization, including health insurance, retirement plans, and other perks."),
               ("Customer Satisfaction Guarantee", "customer_satisfaction.pdf", "This document describes the organization's customer satisfaction guarantee, including references to the customer complaints process and the company's customer-centric mission statement."),
               ("Customer Complaint Process", "customer_complaint_process.pdf", "This] document outlines the process for handling customer complaints, including how to submit a complaint, how complaints are reviewed and resolved, and the expected response time."),
               ("Customer Success Strategies", "customer_success_strategies.pdf", "This document outlines the strategies and best practices for ensuring customer success, including onboarding, training, and ongoing support."),
               ("Expense Approval Policy", "expense_approval_policy.pdf", "This document outlines the expense approval policy, including when manager approval is needed based on receipt value and expense time."),
               ("Data Governance Policy", "data_governance_policy.pdf", "This document outlines the data governance policy, including retention, PII policy, requirements for contractors and tooling, as well as required columns for specific types of data.")
               ]

BASE_PROMPT = "You are a technical writer working at a technology services company called Delight. " \
"Your task is to generate detailed corporate policy documents based on the descriptions provided. " \
"Each document should be comprehensive and well-structured, using markdown conventions."

client = OpenAI(
  api_key=GEMINI_API_KEY,
  base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

for title, filename, description in DOCS_TO_GEN:
    print(f"Generating document: {title}...")
    prompt = f"Generate a document titled '{title}' based on the following description: {description}."

    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": BASE_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    document_content = response.choices[0].message.content
    html_content = markdown.markdown(document_content, extensions=["tables", "fenced_code"])
    HTML(string=html_content).write_pdf(os.path.join(OUTPUT_DIR, filename)) # save as pdf