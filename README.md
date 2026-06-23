# Secure Multi-Tenant Semantic RAG Platform

An enterprise-grade, security-hardened Retrieval-Augmented Generation (RAG) platform. This system implements true semantic vector space mapping, robust multi-tenant data isolation, client-side caching state protections, and automated API resilience mechanisms.

## 🏗️ Architecture Overview

The system transitions from traditional keyword-matching to a high-density, multi-user semantic search grid. The diagram below details the structural data flow across the security and processing pipeline:

[ Vanilla Web Client ] ──(JWT Session Token)──> [ FastAPI Security Gateway ]
│

| 🛡️ 1. Auth Validation Gateway | 🧠 2. Semantic Vector Pipeline | ⚡ 3. Traffic Rate Limiter |
| :--- | :--- | :--- |
| **Action:** Handshakes directly with Supabase API (`/auth/v1/user`) to verify incoming session tokens. | **Action:** Converts dynamic user content strings into dense 3072-dimensional numerical vector coordinate arrays. | **Action:** Monitors incoming connection client IP addresses to enforce hard system request thresholds. |
| **Engine:** FastAPI Identity Middleware | **Engine:** `gemini-embedding-001` | **Engine:** SlowAPI Engine Framework |
| **Downstream Strategy:** Enforces database row protection via **Supabase RLS Isolation**. | **Downstream Strategy:** Executes strict spatial cosine math via **`pgvector` RPC Matrix Matches**. | **Downstream Strategy:** Mitigates API exhaustion blocks using an **Exponential Backoff Engine**. |

---

## 🛡️ Core Security Matrix & Defense Implementations

### 1. Cryptographic Identity Verification Gateway
Rather than trusting client-side claims or blindly forwarding unchecked Authorization headers, the FastAPI backend passes incoming tokens through a live identity verification handshake directly with the Supabase Auth verification cluster (`/auth/v1/user`). 
* **The Result:** Completely neutralizes JWT forging, identity impersonation, and account-crossing injection exploits. Every transaction is definitively bound to the verified database UUID.

### 2. Multi-Tenant Data Isolation (`pgvector` + RLS)
Data isolation is enforced at the database hardware layer by pairing Supabase Row Level Security (RLS) policies with a custom composite primary key constraint on `(id, user_id)` in the `documents` table.
* **The Result:** Multiple users can declare identical document storage IDs (e.g., `notes`, `d1`) simultaneously without causing database primary key collisions. Data profiles remain cleanly siloed.

### 3. Prompt Injection Structural Guardrails
To block indirect context attacks and prompt manipulation, raw text context chunks are strictly separated from system rules.
* **The Result:** The LLM runs under an un-overridable, low-creativity system directive (`temperature: 0.2`) explicitly instructed to catch, flag, and drop system takeover tokens with a uniform warning string: `Security Violation: Direct context retrieval blocked.`

### 4. DDoS Traffic & Quota Throttling (SlowAPI)
An open-source traffic throttling framework (`slowapi`) monitors incoming client IP coordinates to protect downstream endpoints from automated script abuse.
* **The Result:** Imposes a strict restriction of 5 requests per minute maximum on inference loops, absorbing traffic spikes before they exhaust upstream service quotas or trigger excessive API bills.

### 5. Automated Fault-Tolerant Cooldowns (Exponential Backoff)
To handle Google Cloud AI Studio Free Tier constraints (20 requests per minute), the vector compilation methods run inside an adaptive retry loop.
* **The Result:** Upon encountering a `429 Resource Exhausted` flag, the pipeline automatically halts, captures the exception, and applies a dynamic scaling delay (`time.sleep()`), doubling the wait window between sequential retries before declaring a failure state.

---

## 🛠️ Technical Stack Specifications

* **Frontend Environment:** HTML5, CSS3, Asynchronous ES6+ JavaScript.
* **Backend Framework:** FastAPI (Python 3.10+) running over an Asynchronous Uvicorn Web Server Cluster.
* **Database & Auth Gateway:** Supabase Cloud Infrastructure utilizing Postgres, Row Level Security, and the `pgvector` relational extension.
* **AI Model Engine Ecosystem:**
  * **Vector Embeddings Model:** `gemini-embedding-001` (Outputting 3072-Dimension Spatial Coordinate Matrices).
  * **Generative Language Model:** `gemini-2.5-flash` (Anchored with explicit structural System Instructions).

---

## ⚙️ Table Schema & Relational RPC Matching Strategy

The Postgres table schema maps both metadata boundaries and geometric vector structures uniformly:

```sql
-- Core Table Strategy
CREATE TABLE public.documents (
    id TEXT NOT NULL,
    user_id UUID NOT NULL,
    content TEXT,
    embedding extensions.vector(3072), -- 🟢 High-Density Vector Coordinates
    CONSTRAINT documents_pkey PRIMARY KEY (id, user_id) -- 🛡️ Composite Primary Key
);

-- Cosine Distance Multi-User Search Optimization Function
CREATE OR REPLACE FUNCTION match_user_documents (
  query_embedding extensions.vector(3072),
  match_threshold float,
  match_count int,
  target_user_id uuid
)
RETURNS TABLE (id text, content text, similarity float)
LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  RETURN QUERY
  SELECT
    documents.id, documents.content, 1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE documents.user_id = target_user_id
    AND 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY documents.embedding <=> query_embedding ASC
  LIMIT match_count;
END;
$$;
```

## 🧪 How to Live Test the Platform (Quick Walkthrough)

If you want to quickly see the secure semantic RAG pipeline in action without looking at the underlying code, download the file as a zip and run the .html file. Follow these 3 simple steps:

### 1️⃣ Account Registration
1. Open the web app interface link in your browser.
2. Head to the **Sign Up** panel, enter a test email and password, and click register. 
3. Log in. Your browser will securely store your unique encrypted JWT access session token behind the scenes.

### 2️⃣ Indexing Your Knowledge Context
1. In the **Document Management Panel**, create a test file ID (e.g., `company-policy`).
2. Paste a descriptive block of text inside the context block, for example: 
   > *"Employees can work remotely up to two days a week, but must coordinate with their team leads to ensure overlap on core collaborative hours."*
3. Click **Add Document**. The backend instantly converts this paragraph into a 3072-digit vector coordinate space array and anchors it safely inside your database rows.

### 3️⃣ Testing the Semantic AI Query
1. Now, navigate to the **AI Query Workspace**.
2. Type a question that completely avoids using the exact words from your document, such as: *"Can I do my work from home sometimes?"*
3. Click **Ask AI**. 

### 🔍 What to Look For Under the Hood:
* **The Magic:** Notice that even though you never used the words *"remote"*, *"team leads"*, or *"collaborative hours"* in your question, the engine mathematically matches the underlying meaning of *"work from home"* to your uploaded document.
* **The Verification:** Click on the collapsible **"View Retrieved Database Context"** tracker at the bottom of the answer block. You will see that the app cleanly isolated and extracted *only* that specific policy segment to feed Gemini, leaving the rest of the database completely untouched!

## 🚀 Quick Local Setup & Execution

### 1️⃣ Database Config (Supabase)
1. Create a Supabase project and run the script in the **Table Schema** section above inside the **SQL Editor**.
2. Go to **Authentication** ➡️ **Providers** ➡️ **Email** and toggle **Confirm email** to **OFF**.

### 2️⃣ Environment Variables
Create a `.env` file in the project root folder and paste your keys:
```env
SUPABASE_URL="[https://your-project-id.supabase.co](https://your-project-id.supabase.co)"
SUPABASE_KEY="your-supabase-anon-public-key"
GEMINI_API_KEY="AIzaSyYourActualGeminiAPIKeyHere"
```
3️⃣ Run the Backend Server
Open your terminal in the project root and execute:

Bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install dependencies & launch server
pip install -r requirements.txt
uvicorn main: app --reload
The API is now live at http://127.0.0.1:8000. Keep this terminal running.

4️⃣ Run the Frontend
Ensure your app.js API destination matches your local server endpoint (http://127.0.0.1:8000).

Open index.html using the VS Code Live Server extension, or spin up a quick server in a separate terminal:

Bash
python -m http.server 5500
Open http://localhost:5500 in your browser, sign up, and start testing!


Save your `README.md`, commit it in GitHub Desktop as `docs: condense setup instructions`, and push it to the origin! You are all set.



