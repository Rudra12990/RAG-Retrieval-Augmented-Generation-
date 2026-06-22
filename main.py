import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from dotenv import load_dotenv
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions  # Core options constructor fix

# Securely load environment variables
load_dotenv()

app = FastAPI(title="Vibe Coder AI Knowledge Base with Cloud Persistence")

# Enable smooth frontend interaction across different domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 💾 Initialize Supabase Cloud Database Client with correct configuration routing
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ Supabase credentials missing from environment setup!")

# Initializing client by wrapping schema options to handle new scoped publishable tokens safely
supabase_client: Client = create_client(
    SUPABASE_URL, 
    SUPABASE_KEY,
    options=ClientOptions(schema="public")
)

# 🚀 Initialize Gemini AI Engine Client
try:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    print(f"⚠️ Gemini initialization warning: {e}")


@app.get("/")
def read_root():
    return {"status": "Online", "message": "Persistent cloud backend running successfully!"}


@app.post("/clear")
def clear_database():
    """Wipes the database table completely clean by deleting all matching records."""
    try:
        supabase_client.table("documents").delete().neq("id", "none").execute()
        return {"status": "success", "message": "Cloud database wiped completely clean."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database wipe failed: {str(e)}")


@app.post("/add")
def add_to_database(doc_id: str, text_content: str, mode: str = "check"):
    """
    Stores and manages documents inside Supabase Cloud Storage.
    Modes: 'check', 'overwrite', 'append'
    """
    if not doc_id or not text_content:
        raise HTTPException(status_code=400, detail="Missing required parameters")
    
    try:
        # Check if the document ID already exists in the cloud table
        existing_record = supabase_client.table("documents").select("*").eq("id", doc_id).execute()
        
        if existing_record.data and mode == "check":
            return {
                "status": "exists_warning", 
                "message": f"The ID '{doc_id}' already exists in the cloud table. What would you like to do?",
                "existing_text": existing_record.data[0]["content"]
            }
        
        if mode == "append" and existing_record.data:
            # Combine old text with new text using a newline break
            updated_text = existing_record.data[0]["content"] + "\n" + text_content
            supabase_client.table("documents").update({"content": updated_text}).eq("id", doc_id).execute()
            return {"status": "success", "message": f"Successfully appended data to record '{doc_id}'."}
        
        else:
            # Overwrite or create brand new entry using upsert
            supabase_client.table("documents").upsert({"id": doc_id, "content": text_content}).execute()
            return {"status": "success", "message": f"Document '{doc_id}' stored safely in cloud storage."}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cloud write failure: {str(e)}")


@app.post("/ask")
def ask_ai(question: str):
    """Retrieves all combined text context from Supabase and queries Gemini 2.5 Flash."""
    try:
        # Pull all documents from our cloud table
        records = supabase_client.table("documents").select("content").execute()
        
        if records.data:
            # Join all content fields together to build context
            context = " ".join([row["content"] for row in records.data])
        else:
            context = "No custom documents uploaded yet."

        prompt = f"Context: {context}\n\nQuestion: {question}"
        
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
        if "503" in error_msg or "UNAVAILABLE" in error_msg:
            friendly_answer = "⚠️ Google's AI servers are experiencing a temporary traffic spike. Please wait 10 seconds and click 'Query App' again!"
        else:
            friendly_answer = f"Gemini Query Failed: {error_msg}"

        return {
            "retrieved_context": "System Warning",
            "answer": friendly_answer
        }