import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai  # Modern up-to-date Google SDK
from dotenv import load_dotenv

# 🚀 Securely load your local .env file setup
load_dotenv()

app = FastAPI(title="Vibe Coder AI Knowledge Base")

# Enable smooth frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the modern client. It automatically finds GEMINI_API_KEY inside your .env file!
try:
    client = genai.Client()
except Exception as e:
    print(f"⚠️ Initialization warning: {e}")

# Secure local in-memory database dictionary
LOCAL_DATABASE = {}

@app.get("/")
def read_root():
    return {"status": "Online", "message": "Demo backend running successfully!"}

@app.post("/add")
def add_to_database(doc_id: str, text_content: str):
    if not doc_id or not text_content:
        raise HTTPException(status_code=400, detail="Missing data")
    
    LOCAL_DATABASE[doc_id] = text_content
    return {"status": "success", "message": f"Document '{doc_id}' stored safely."}
@app.post("/clear")
def clear_database():
    LOCAL_DATABASE.clear()
    return {"status": "success", "message": "Local database wiped completely clean."}

@app.post("/ask")
def ask_ai(question: str):
    try:
        # Build context from your local database items
        if LOCAL_DATABASE:
            context = " ".join(LOCAL_DATABASE.values())
        else:
            context = "No custom documents uploaded yet."

        prompt = f"Context: {context}\n\nQuestion: {question}"
        
        # Call the modern flash model endpoint securely
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        return {
            "retrieved_context": context,
            "answer": response.text
        }
    except Exception as e:
        return {
            "retrieved_context": "System Error",
            "answer": f"Gemini Query Failed: {str(e)}"
        }