import os
import httpx  
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from dotenv import load_dotenv

# Securely load environment variables
load_dotenv()

app = FastAPI(title="Vibe Coder AI Workspace - Multi-User Secure Edition")

# Enable smooth frontend interaction across different domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fetch system configurations cleanly
SUPABASE_URL = os.environ.get("SUPABASE_URL").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Gemini Client
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"⚠️ Gemini initialization warning: {e}")


def get_user_headers(authorization: str = Header(None)):
    """
    Extracts the incoming User JWT Token from the Frontend 
    and packages it for secure RLS delegation to Supabase.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header credentials.")
    
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": authorization,  # Forwards the User's personal identity token
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


@app.get("/documents")
def list_user_documents(headers: dict = Depends(get_user_headers)):
    """Fetches a list of document IDs belonging ONLY to the authenticated user via RLS."""
    target_url = f"{SUPABASE_URL}/rest/v1/documents?select=id"
    try:
        with httpx.Client() as http_client:
            res = http_client.get(target_url, headers=headers)
        
        if res.status_code != 200:
            raise Exception(res.text)
            
        return {"status": "success", "documents": [row["id"] for row in res.json()]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve index list: {str(e)}")


@app.post("/add")
def add_to_database(doc_id: str, text_content: str, mode: str = "check", headers: dict = Depends(get_user_headers)):
    """Stores and modifies user documents securely under their specific profile identity."""
    import urllib.parse
    encoded_id = urllib.parse.quote(doc_id)
    
    select_url = f"{SUPABASE_URL}/rest/v1/documents?id=eq.{encoded_id}"
    upsert_url = f"{SUPABASE_URL}/rest/v1/documents"
    
    try:
        with httpx.Client() as http_client:
            # 1. Fetch record if it exists for this authenticated user
            get_res = http_client.get(select_url, headers=headers)
            existing_data = get_res.json() if get_res.status_code == 200 else []
            
            # 2. Check duplicate trigger validation
            if existing_data and mode == "check":
                return {
                    "status": "exists_warning", 
                    "message": "ID Collision found.",
                    "existing_text": existing_data[0]["content"]
                }
            
            # 3. Handle data mutation paths
            if mode == "append" and existing_data:
                updated_text = existing_data[0]["content"] + "\n" + text_content
                patch_url = f"{SUPABASE_URL}/rest/v1/documents?id=eq.{encoded_id}"
                res = http_client.patch(patch_url, json={"content": updated_text}, headers=headers)
                if res.status_code not in [200, 201, 204]:
                    raise Exception(res.text)
                return {"status": "success", "message": "Successfully appended data securely."}
            
            else:
                # Default behaviour: Standard Upsert insertion path matching the active user session
                upsert_headers = headers.copy()
                upsert_headers["Prefer"] = "return=representation,resolution=merge-duplicates"
                
                payload = {"id": doc_id, "content": text_content}
                res = http_client.post(upsert_url, json=payload, headers=upsert_headers)
                if res.status_code not in [200, 201, 204]:
                    raise Exception(res.text)
                return {"status": "success", "message": f"Document '{doc_id}' stored safely in cloud storage."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cloud write failure: {str(e)}")


@app.post("/ask")
def ask_ai(question: str, headers: dict = Depends(get_user_headers)):
    """Queries Gemini utilizing exclusively the authenticated user's context dataset allocation."""
    target_url = f"{SUPABASE_URL}/rest/v1/documents?select=content"
    try:
        with httpx.Client() as http_client:
            res = http_client.get(target_url, headers=headers)
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


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str, headers: dict = Depends(get_user_headers)):
    """Deletes a specific document from the database by its ID key, scoped to the user session."""
    import urllib.parse
    target_url = f"{SUPABASE_URL}/rest/v1/documents?id=eq.{urllib.parse.quote(doc_id)}"
    try:
        with httpx.Client() as http_client:
            res = http_client.delete(target_url, headers=headers)
            
        if res.status_code not in [200, 204]:
            raise Exception(res.text)
            
        return {"status": "success", "message": f"Document '{doc_id}' successfully deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion sequence failed: {str(e)}")


@app.post("/clear")
def clear_database(headers: dict = Depends(get_user_headers)):
    """Wipes exclusively the logged-in user's items via RLS safety scoping boundaries."""
    target_url = f"{SUPABASE_URL}/rest/v1/documents?id=neq.none"
    try:
        with httpx.Client() as http_client:
            res = http_client.delete(target_url, headers=headers)
            
        if res.status_code not in [200, 204]:
            raise Exception(res.text)
            
        return {"status": "success", "message": "Your personal database workspace has been cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database wipe failed: {str(e)}")