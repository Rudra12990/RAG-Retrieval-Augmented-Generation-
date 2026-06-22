import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai  # Modern up-to-date Google SDK
from dotenv import load_dotenv

# 🚀 Securely load your local .env file setup
load_dotenv()

app = FastAPI(title="Vibe Coder AI Knowledge Base")

# Enable smooth frontend interaction across different domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the modern client by pulling the key from the loaded environment setup
try:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    print(f"⚠️ Initialization warning: {e}")

# Secure local in-memory database dictionary
LOCAL_DATABASE = {}

@app.get("/")
def read_root():
    return {"status": "Online", "message": "Demo backend running successfully!"}

@app.post("/clear")
def clear_database():
    """Wipes the local in-memory database completely clean."""
    LOCAL_DATABASE.clear()
    return {"status": "success", "message": "Local database wiped completely clean."}

@app.post("/add")
def add_to_database(doc_id: str, text_content: str, mode: str = "check"):
    """
    Stores text documents inside our local memory database.
    Modes: 
      - 'check': Warns if the ID exists.
      - 'overwrite': Replaces the old data.
      - 'append': Combines old and new data together.
    """
    if not doc_id or not text_content:
        raise HTTPException(status_code=400, detail="Missing data")
    
    # Check if ID already exists and user hasn't made a decision yet
    if doc_id in LOCAL_DATABASE and mode == "check":
        return {
            "status": "exists_warning", 
            "message": f"The ID '{doc_id}' already exists. What would you like to do?",
            "existing_text": LOCAL_DATABASE[doc_id]
        }
    
    # Handle user choices
    if mode == "append":
        # Combines the old text with the new text using a newline break
        LOCAL_DATABASE[doc_id] = LOCAL_DATABASE[doc_id] + "\n" + text_content
        return {"status": "success", "message": f"Successfully added new information to '{doc_id}'."}
    
    else:
        # Default behavior: overwrite or standard brand new entry
        LOCAL_DATABASE[doc_id] = text_content
        return {"status": "success", "message": f"Document '{doc_id}' stored safely."}

@app.post("/ask")
def ask_ai(question: str):
    """Retrieves text context from memory and queries Gemini 2.5 Flash."""
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
        error_msg = str(e)
        # Catch Google's 503 high-demand traffic spikes gracefully
        if "503" in error_msg or "UNAVAILABLE" in error_msg:
            friendly_answer = "⚠️ Google's AI servers are currently experiencing a temporary high-demand traffic spike. Please wait 10 seconds and click 'Query App' again!"
        else:
            friendly_answer = f"Gemini Query Failed: {error_msg}"

        return {
            "retrieved_context": "System Warning",
            "answer": friendly_answer
        }