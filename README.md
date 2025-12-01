📧 AI Mailer BOT – Automated Email Response System (Gmail + GPT + FAISS)

The AI Mailer BOT is an automated email-response system that reads unread Gmail emails, understands the query, searches for the most relevant answer from an FAQ Excel file using vector similarity, generates a clean email reply using GPT-3.5-turbo, and sends the response back to the user automatically.

This bot is ideal for:
✅ Customer service
✅ Internal support teams
✅ Automated FAQ-based responders
✅ Helpdesk automation

🚀 Features
✔ 1. Reads FAQs from Excel

You maintain a simple Excel sheet (faq.xlsx) with two columns:

Question	Answer

The BOT loads this file and embeds all questions using OpenAI embeddings.

✔ 2. Creates a FAISS Vector Store

Converts FAQ questions into embeddings

Stores them inside a FAISS index (faq.index)

Supports fast similarity search for incoming queries

✔ 3. Reads Unread Gmail Emails

The bot scans the Gmail inbox using Gmail API and fetches unread emails.

(Currently supports filtering by specific email sender.)

✔ 4. Extracts Email Body (Handles multipart emails)

Automatically extracts plain text email content—even from nested MIME structures.

✔ 5. Vector Similarity Search

When an email query arrives:

Convert query → embedding

Compare with FAISS index

Retrieve top-k closest FAQ answers

Apply a distance threshold to avoid irrelevant matches

✔ 6. GPT-Powered Email Response

Uses GPT-3.5-Turbo to generate a clean, professional, short email reply based ONLY on FAQ context.

Rules include:

Start with “Dear User,”

Use only provided FAQ answers

No hallucination

2–4 sentence replies

Close with “Thank you.”

✔ 7. Sends Reply via Gmail

Uses Gmail API to send the generated response back to the user.

✔ 8. Marks Original Email as Read

After replying, the bot marks the email as “READ”.

🧱 Project Architecture
AI Mailer Bot
│
├── faq.xlsx               # Your FAQ database
├── faq.index              # FAISS Vector Index (auto-created)
├── token.json             # Gmail API token (auto-generated)
├── credentials.json       # Gmail OAuth credentials (you provide)
├── main.py                # AI mailer bot script (your code)
└── README.md              # Documentation

🔧 Installation & Setup
1️⃣ Install Python Dependencies
pip install openai google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2 faiss-cpu pandas numpy

2️⃣ Setup Gmail API Credentials

Go to Google Cloud Console

Enable Gmail API

Create OAuth client ID → Desktop App

Download credentials.json into the project folder

3️⃣ Add your FAQ Excel file

Example structure:

Question	Answer
What is leave policy?	Employees get 12 casual leaves per year.

Save as faq.xlsx.

4️⃣ Add your OpenAI API Key

Set inside the script:

OPENAI_API_KEY = "your-key-here"


Or via environment variable:

export OPENAI_API_KEY="xxx"

▶️ Running the BOT

Run the script:

python main.py


The first time you run it:

A browser will open

You will log in to your Gmail account

token.json will be generated automatically

After that, the bot runs without login.

🔄 How the BOT Works (Workflow)
STEP 1 → Load FAQ Excel
STEP 2 → Build or load FAISS vector index
STEP 3 → Authenticate Gmail
STEP 4 → Fetch unread emails
STEP 5 → Extract user query
STEP 6 → Search similar FAQ (FAISS)
STEP 7 → Generate reply using GPT-3.5-turbo
STEP 8 → Send reply back to user
STEP 9 → Mark email as read

🧙 Configurable Parts
➤ Filter emails by sender

In get_unread_emails():

query = "is:unread from:rsachink02@gmail.com"


Change to:

is:unread

is:unread subject:HR

from:*@company.com

➤ Adjust FAISS match threshold
threshold=2


Lower → stricter
Higher → more lenient

➤ Change GPT model

Replace:

model="gpt-3.5-turbo"

🛡 Safety Notes

Gmail API requires secure storage of credentials.json

Do not commit API keys or tokens to GitHub

FAISS index refreshes automatically if you update FAQs
