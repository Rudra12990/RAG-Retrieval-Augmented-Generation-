import os
import httpx  
import jwt  
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

load_dotenv()

app = FastAPI(title="Vibe Coder AI Workspace - Vector Edition")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.environ.get("SUPABASE_URL").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"⚠️ Gemini initialization error: {e}")


def verify_and_get_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid credentials.")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SUPABASE_KEY, algorithms=["HS256"], options={"verify_aud": False})
        return {
            "user_id": payload.get("sub"),
            "headers": {
                "apikey": SUPABASE_KEY,
                "Authorization": authorization,
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
        }
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Authentication failed.")


def get_embedding(text: str) -> list:
    """Generates a standard 1536-dimension text embedding vector via Gemini."""
    try:
        response = client.models.embed_content(
            model="text-embedding-004",  # Native, super-fast embedding model
            contents=text
        )
        # Extract the vector coordinate floating point array
        return response.embeddings[0].values
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding compilation failed: {str(e)}")


@app.get("/documents")
def list_user_documents(user_data: dict = Depends(verify_and_get_user)):
    target_url = f"{SUPABASE_URL}/rest/v1/documents?select=id"
    with httpx.Client() as http_client:
        res = http_client.get(target_url, headers=user_data["headers"])
    return {"status": "success", "documents": [row["id"] for row in res.json()]}


@app.post("/add")
def add_to_database(doc_id: str, text_content: str, mode: str = "check", user_data: dict = Depends(verify_and_get_user)):
    import urllib.parse
    sanitized_id = "".join(c for c in doc_id if c.isalnum() or c in "-_").strip()
    encoded_id = urllib.parse.quote(sanitized_id)
    
    select_url = f"{SUPABASE_URL}/rest/v1/documents?id=eq.{encoded_id}"
    upsert_url = f"{SUPABASE_URL}/rest/v1/documents"
    
    # Generate the vector coordinate representation for the incoming content block
    vector_values = get_embedding(text_content)
    
    with httpx.Client() as http_client:
        get_res = http_client.get(select_url, headers=user_data["headers"])
        existing_data = get_res.json() if get_res.status_code == 200 else []
        
        if existing_data and mode == "check":
            return {"status": "exists_warning", "message": "ID Collision found."}
        
        if mode == "append" and existing_data:
            updated_text = existing_data[0]["content"] + "\n" + text_content
            updated_vector = get_embedding(updated_text) # Re-embed the combined text content block
            patch_url = f"{SUPABASE_URL}/rest/v1/documents?id=eq.{encoded_id}"
            http_client.patch(patch_url, json={"content": updated_text, "embedding": updated_vector}, headers=user_data["headers"])
            return {"status": "success", "message": "Appended and re-embedded successfully."}
        else:
            upsert_headers = user_data["headers"].copy()
            upsert_headers["Prefer"] = "return=representation,resolution=merge-duplicates"
            payload = {
                "id": sanitized_id, 
                "content": text_content, 
                "user_id": user_data["user_id"],
                "embedding": vector_values # Saves coordinate data alongside text
            }
            http_client.post(upsert_url, json=payload, headers=upsert_headers)
            return {"status": "success", "message": "Document vector saved successfully."}


@app.post("/ask")
@limiter.limit("5/minute")
def ask_ai(request: Request, question: str, user_data: dict = Depends(verify_and_get_user)):
    """Queries Gemini utilizando a semantic similarity vector lookup match matrix."""
    # 1. Turn user query into a vector coordinate
    query_vector = get_embedding(question)
    
    # 2. Query our custom matching function inside Supabase
    rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/match_user_documents"
    rpc_payload = {
        "query_embedding": query_vector,
        "match_threshold": 0.3, # Adjust to filter relevance strictness
        "match_count": 3,       # Gather only top 3 context documents
        "target_user_id": user_data["user_id"]
    }
    
    try:
        with httpx.Client() as http_client:
            rpc_res = http_client.post(rpc_url, json=rpc_payload, headers=user_data["headers"])
            records = rpc_res.json() if rpc_res.status_code == 200 else []
        
        # 3. Piece together only context chunks that matter
        context_chunks = [row["content"] for row in records] if isinstance(records, list) else []
        context = " \n---\n ".join(context_chunks) if context_chunks else "No relevant matching documents found."
        
        system_instruction = (
            "You are a secure data analyzer. Your task is to answer queries using exclusively "
            "the provided relevant context vector segments. Keep responses tight and accurate."
        )
        user_content = f"Retrieved Context Snippets:\n{context}\n\nUser Question Statement: {question}"
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2
            )
        )
        return {"retrieved_context": context, "answer": response.text}
    except Exception as e:
        return {"retrieved_context": "Error matching context layers", "answer": str(e)}


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str, user_data: dict = Depends(verify_and_get_user)):
    import urllib.parse
    target_url = f"{SUPABASE_URL}/rest/v1/documents?id=eq.{urllib.parse.quote(doc_id)}"
    with httpx.Client() as http_client:
        http_client.delete(target_url, headers=user_data["headers"])
    return {"status": "success", "message": "Document removed successfully."}


@app.post("/clear")
def clear_database(user_data: dict = Depends(verify_and_get_user)):
    target_url = f"{SUPABASE_URL}/rest/v1/documents?id=neq.none"
    with httpx.Client() as http_client:
        http_client.delete(target_url, headers=user_data["headers"])
    return {"status": "success", "message": "Your personal database workspace has been cleared."}