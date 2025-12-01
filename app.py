import os

import base64

import pandas as pd

import faiss

import numpy as np

from openai import OpenAI

from email.mime.text import MIMEText

 

from google.auth.transport.requests import Request

from google.oauth2.credentials import Credentials

from google_auth_oauthlib.flow import InstalledAppFlow

from googleapiclient.discovery import build

 

# ================================

# CONFIGURATION

# ================================

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

 

FAQ_EXCEL = "faq.xlsx"

VECTOR_STORE = "faq.index"

OPENAI_API_KEY = "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"

client = OpenAI(api_key=OPENAI_API_KEY)

 

# ================================

# 1. AUTHENTICATE GMAIL CLIENT

# ================================




 

def get_gmail_service():
    creds = None

    # Try to load existing token.json
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception as e:
            print("⚠️ token.json is corrupted or invalid — deleting it.")
            os.remove("token.json")
            creds = None

    # If no valid credentials, re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )

            # FORCE Google to issue a refresh token
            creds = flow.run_local_server(
                port=0,
                prompt='consent',
                access_type='offline'
            )

        # Store the refresh token in token.json
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)






 

# ================================

# 2. CREATE / LOAD FAQ VECTOR DB

# ================================

def build_or_load_vector_db():

    if os.path.exists(VECTOR_STORE):

        index = faiss.read_index(VECTOR_STORE)

        df = pd.read_excel(FAQ_EXCEL)

        return df, index

 

    df = pd.read_excel(FAQ_EXCEL)

    questions = df["Question"].tolist()

 

    embeddings = client.embeddings.create(

        model="text-embedding-3-small",

        input=questions

    ).data

 

    vectors = np.array([e.embedding for e in embeddings]).astype("float32")

 

    index = faiss.IndexFlatL2(vectors.shape[1])

    index.add(vectors)

 

    faiss.write_index(index, VECTOR_STORE)

    return df, index

 

 

# ================================

# 3. GET UNREAD EMAILS

# ================================

def get_email_body(payload):
    """
    Extract the plain text body from a Gmail payload.
    Handles multipart emails.
    """
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part["body"]:
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
            # Sometimes parts are nested
            elif "parts" in part:
                nested_body = get_email_body(part)
                if nested_body:
                    return nested_body
    elif "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    return ""










def get_unread_emails(service):

    """
    Fetch unread emails sent only by rsachink02@gmail.com
    """
    query = "is:unread from:rsachink02@gmail.com"  # Gmail search query

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=1
    ).execute()


 
    print(results)
    messages = results.get("messages", [])
    print(messages)
    if not messages:

        return []

 

    unread = []

    for msg in messages:

        msg_data = service.users().messages().get(

            userId="me", id=msg["id"]

        ).execute()

 

        payload = msg_data["payload"]

        headers = payload["headers"]

 

        sender = None

        subject = None

        for h in headers:

            if h["name"] == "From":

                sender = h["value"]

            if h["name"] == "Subject":

                subject = h["value"]

 

        

        body = get_email_body(payload)

        print(body)

        unread.append({

            "id": msg["id"],

            "sender": sender,

            "subject": subject,

            "body": body.strip()

        })

 

    return unread

 

 

# ================================

# 4. FIND SIMILAR FAQ ANSWERS

# ================================

# def get_similar_faq(query, df, index):

#     embedded = client.embeddings.create(

#         model="text-embedding-3-small",

#         input=query

#     ).data[0].embedding

 

#     vector = np.array([embedded]).astype("float32")

 

#     distances, faq_indexes = index.search(vector, 3)

#     faq_indexes = faq_indexes[0]
#     print("Query:", query)
#     print("FAISS returned indexes:", faq_indexes)
#     print("FAISS returned distances:", distances)

 

#     retrieved = []

#     for i in faq_indexes:
#         if i == -1 or i<0:
#             continue
        
#         question = df.loc[i, "Question"]

#         answer = df.loc[i, "Answer"]

#         retrieved.append((question, answer))

 

#     return retrieved

def get_similar_faq(query, df, index, threshold=2,top_k=3):
    """
    Returns top-k FAQ entries most similar to the query.
    Only returns FAQs whose similarity distance is below `threshold`.
    """
    # 1. Get embedding for user query
    embedded = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    ).data[0].embedding

    vector = np.array([embedded]).astype("float32")

    # 2. Search top_k closest vectors in FAISS
    distances, faq_indexes = index.search(vector, top_k)

    faq_indexes = faq_indexes[0]
    distances = distances[0]

    print("Query:", query)
    print("FAISS returned indexes:", faq_indexes)
    print("FAISS returned distances:", distances)

    # 3. Filter based on distance threshold
    retrieved = []
    for idx, dist in zip(faq_indexes, distances):
        if idx < 0:
            continue
        # FAISS IndexFlatL2 returns Euclidean distance; smaller = more similar
        if dist > threshold:
            continue
        question = df.loc[idx, "Question"]
        answer = df.loc[idx, "Answer"]
        retrieved.append((question, answer))

    return retrieved


 

# ================================

# 5. CALL GPT TO GENERATE REPLY

# ================================

# def generate_llm_reply(user_query, faq_data):


#         # If no FAQ answer found → return fallback message
#     if not faq_data or (len(faq_data) == 1 and faq_data[0][0] == "No matching FAQ found."):
#         return (
#             "Dear User,\n\n"
#             "Currently I am not able to answer your query.\n"
#             "Someone from our customer support team will respond shortly.\n\n"
#             "Thank you."
#         )

#     context = ""

#     for q, a in faq_data:

#         context += f"Q: {q}\nA: {a}\n\n"

 

#     prompt = f"""

# You are an automated email reply bot.

 

# User query:

# {user_query}

 

# Use ONLY the FAQ information below to answer:

# {context}

 

# Write a short, clear email response.

# """

 

#     completion = client.responses.create(

#         model="gpt-3.5-turbo",

#         input=prompt,

#     )

 

#     return completion.output_text

 
def generate_llm_reply(user_query, faq_data):

    if not faq_data or (len(faq_data) == 1 and faq_data[0][0] == "No matching FAQ found."):
        return (
            "Dear User,\n\n"
            "Currently I am not able to answer your query.\n"
            "Someone from our customer support team will respond shortly.\n\n"
            "Thank you."
        )

    context = ""
    for q, a in faq_data:
        context += f"Q: {q}\nA: {a}\n\n"

    prompt = f"""
You are an automated email reply bot.

User query:
{user_query}

Use ONLY the FAQ information below to answer.
If the answer is not in the FAQ, reply:
"I am unable to answer this question at the moment. Someone from our support team will get back to you."

FAQ information:
{context}

Rules:
- Do NOT make up any information.
- Do NOT add personal opinions.
- Always start the email with: "Dear User,"
- Keep the answer short (2-4 sentences)
- Close with: "Thank you."

Write the email reply below:
"""

    completion = client.responses.create(
        model="gpt-3.5-turbo",
        input=prompt,
        temperature=0,
    )

    return completion.output_text.strip()













 

# ================================

# 6. SEND EMAIL REPLY

# ================================

def send_email(service, to, subject, body):

    message = MIMEText(body)

    message["to"] = to

    message["subject"] = subject

 

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    send = service.users().messages().send(

        userId="me",

        body={"raw": raw}

    ).execute()

 

    return send

 

 

# ================================

# 7. MARK EMAIL AS READ

# ================================

def mark_as_read(service, msg_id):

    service.users().messages().modify(

        userId="me",

        id=msg_id,

        body={"removeLabelIds": ["UNREAD"]}

    ).execute()

 

 

# ================================

# MAIN BOT LOGIC

# ================================

def auto_mailer_bot():

    print("🔐 Authenticating Gmail...")

    service = get_gmail_service()

 

    print("📚 Loading FAQ & Vector DB...")

    df, index = build_or_load_vector_db()
    print(df)
 

    print("📥 Fetching unread emails...")

    unread = get_unread_emails(service)

    print(unread)

    if not unread:

        print("No unread emails found.")

        return

 

    for mail in unread:

        print("\n📧 Processing email from:", mail["sender"])

 

        user_query = mail["body"]
        print(user_query)
 

        print("🔍 Finding similar FAQ answers...")

        retrieved_faq = get_similar_faq(user_query, df, index)

        print(retrieved_faq)

        print("🤖 Generating AI reply...")

        # if not retrieved_faq:
        #     re 

        ai_reply = generate_llm_reply(user_query, retrieved_faq)

     

        print("📤 Sending reply...")

        send_email(

            service,

            mail["sender"],

            "Re: " + mail["subject"],

            ai_reply

        )

 

        print("✔ Marking as read...")

        mark_as_read(service, mail["id"])

 

        print("✔ Completed!")

 

 

if __name__ == "__main__":

    auto_mailer_bot()

 