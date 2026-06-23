# Secure Multi-Tenant Semantic RAG Platform

An enterprise-grade, security-hardened Retrieval-Augmented Generation (RAG) platform. This system implements true semantic vector space mapping, robust multi-tenant data isolation, client-side caching state protections, and automated API resilience mechanisms.

## 🏗️ Architecture Overview

The system transitions from traditional keyword-matching to a high-density, multi-user semantic search grid utilizing state-of-the-art vector embeddings and explicit security middleware verification thresholds.

[ Vanilla Web Client ] ──(JWT Session Token)──> [ FastAPI Security Gateway ]
│


┌─────────────────────────────────────────────┴─────────────────────────────────────────────┐
▼                                              ▼
🛡️ Defense 1: Auth Validation               🧠 Semantic Pipeline                          ⚡ Defense 3: Rate Limiter
Handshakes directly with Supabase           Converts inputs to 3072-dim vectors            Enforces Traffic Throttling
/auth/v1/user API to isolate IDs.         via gemini-embedding-001.                   via SlowAPI (5 req/min max).
│                                             │                                             │
▼                                             ▼                                             ▼
[ Supabase RLS Row Isolation ]             [ pgvector Similarity RPC Match ]             [ Exponential Backoff Engine ]


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
* **The Result:** The LLM runs under an un-overrideable, low-creativity system directive (`temperature: 0.2`) explicitly instructed to catch, flag, and drop system takeover tokens with a uniform warning string: `Security Violation: Direct context retrieval blocked.`

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
