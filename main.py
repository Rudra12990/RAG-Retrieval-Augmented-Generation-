import os
import httpx  
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from dotenv import load_dotenv

# Securely load environment variables
load_dotenv()

app = FastAPI(title="Vibe Coder AI Knowledge Base with Direct Cloud REST Sync")

# Enable smooth frontend interaction across different domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔑 Fetch environment variables cleanly
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Trim accidental spaces or trailing slashes automatically
if SUPABASE_URL:
    SUPABASE_URL = SUPABASE_URL.strip().rstrip("/")

# 🚀 Initialize Gemini Client
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"⚠️ Gemini initialization warning: {e}")


def get_auth_headers():
    """Generates explicit headers for standard Supabase REST operations."""
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",  # 👈 Fixed: Turned into an explicit string token literal
        "Prefer": "return=representation"    # 👈 Tells Supabase to return and verify the row payload data
    }


@app.get("/")
def read_root():
    return {"status": "Online", "message": "Direct REST persistent cloud backend running successfully!"}


@app.post("/clear")
def clear_database():
    """Wipes the database table completely clean via a direct REST DELETE path request."""
    target_url = f"{SUPABASE_URL}/rest/v1/documents?id=neq.none"
    
    try:
        with httpx.Client() as http_client:
            res = http_client.delete(target_url, headers=get_auth_headers())
            
        if res.status_code not in [200, 204]:
            raise Exception(res.text)
            
        return {"status": "success", "message": "Cloud database wiped completely clean."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database wipe failed: {str(e)}")


@app.post("/add")
def add_to_database(doc_id: str, text_content: str, mode: str = "check"):
    """
    Stores and manages documents inside Supabase via explicit HTTP REST commands.
    """
    if not doc_id or not text_content:
        raise HTTPException(status_code=400, detail="Missing required parameters")
    
    # Correctly build absolute URLs for standard table targeting
    select_url = f"{SUPABASE_URL}/rest/v1/documents?id=eq.{encode_query_param(doc_id)}"
    upsert_url = f"{SUPABASE_URL}/rest/v1/documents"
    
    try:
        headers = get_auth_headers()
        
        with httpx.Client() as http_client:
            # 1. Fetch record if it exists
            get_res = http_client.get(select_url, headers=headers)
            existing_data = get_res.json() if get_res.status_code == 200 else []
            
            # 2. Check duplicate trigger validation
            if existing_data and mode == "check":
                return {
                    "status": "exists_warning", 
                    "message": f"The ID '{doc_id}' already exists in the cloud table. What would you like to do?",
                    "existing_text": existing_data[0]["content"]
                }
            
            # 3. Handle data mutation paths
            if mode == "append" and existing_data:
                updated_text = existing_data[0]["content"] + "\n" + text_content
                patch_url = f"{SUPABASE_URL}/rest/v1/documents?id=eq.{encode_query_param(doc_id)}"
                
                res = http_client.patch(patch_url, json={"content": updated_text}, headers=headers)
                if res.status_code not in [200, 201, 204]:
                    raise Exception(f"Append failure: {res.text}")
                    
                return {"status": "success", "message": f"Successfully appended data to record '{doc_id}'."}
            
            else:
                # 4. Standard Upsert / Insert Path
                # Use explicit PostgREST Upsert header configuration rules
                upsert_headers = headers.copy()
                upsert_headers["Prefer"] = "return=representation,resolution=merge-duplicates"
                
                payload = {"id": doc_id, "content": text_content}
                res = http_client.post(upsert_url, json=payload, headers=upsert_headers)
                
                # Check if the database rejected the write operation
                if res.status_code not in [200, 201, 204]:
                    raise Exception(f"Database write rejected with status {res.status_code}: {res.text}")
                
                return {"status": "success", "message": f"Document '{doc_id}' stored safely in cloud storage."}
                
    except Exception as e:
        # Pass the real database error code back to your frontend screen to see exactly what is blocking it
        raise HTTPException(status_code=500, detail=f"Cloud write failure: {str(e)}")
    

@app.get("/documents")
def list_all_document_ids():
    """Fetches a clean list of all unique document IDs currently inside the database."""
    target_url = f"{SUPABASE_URL}/rest/v1/documents?select=id"
    
    try:
        with httpx.Client() as http_client:
            res = http_client.get(target_url, headers=get_auth_headers())
            records = res.json() if res.status_code == 200 else []
            
        # Extract just the raw string IDs into a clean array list
        ids_list = [row["id"] for row in records]
        return {"status": "success", "documents": ids_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve index list: {str(e)}")


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    """Deletes a specific document from the database by its ID key."""
    target_url = f"{SUPABASE_URL}/rest/v1/documents?id=eq.{encode_query_param(doc_id)}"
    
    try:
        with httpx.Client() as http_client:
            res = http_client.delete(target_url, headers=get_auth_headers())
            
        if res.status_code not in [200, 204]:
            raise Exception(res.text)
            
        return {"status": "success", "message": f"Document '{doc_id}' successfully deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion sequence failed: {str(e)}")


@app.post("/ask")
def ask_ai(question: str):
    """Retrieves all combined text context from Supabase and queries Gemini 2.5 Flash."""
    target_url = f"{SUPABASE_URL}/rest/v1/documents?select=content"
    
    try:
        with httpx.Client() as http_client:
            res = http_client.get(target_url, headers=get_auth_headers())
            records = res.json() if res.status_code == 200 else []
        
        if records:
            context = " ".join([row["content"] for row in records])
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


def encode_query_param(val: str) -> str:
    """Helper method to format request query text values safely."""
    import urllib.parse
    return urllib.parse.quote(val)