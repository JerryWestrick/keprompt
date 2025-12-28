# KePrompt RAG – Final Canon (18 November 2025)

This is the complete, locked-in, no-more-changes design we just forged together.


# KePrompt RAG – Final Canon (2025–forever)

## Core Objects (pure semantics)

| Term                  | Meaning (final) |
|-----------------------|---------------------------------------------------|
| Semantic Store        | Abstract concept: a searchable collection of embedded text chunks |
| Knowledge Base (KB)   | Named, versioned, concrete instance of a Semantic Store |
| Chunk                 | One atomic text fragment + metadata + embedding |
| KB Registry           | System object that knows all existing Knowledge Bases |

## Knowledge Base Attributes (the only nine)

1. Name               – unique identifier (`"hr"`, `"code"`)
2. Source             – definition of the document set (used by Fetch)
3. Pipeline           – ordered list of exactly 6 Step Routines + arguments
4. Access Interface   – what `kbquery()` needs (provider + collection)
5. Data Store         – physical vector store location
6. Version            – immutable version string (`"2025.51.7"`)
7. Created At         – timestamp of build completion
8. Status             – active / building / failed / archived
9. Metadata           – optional free-form tags

## The Six Canonical Steps (never reordered, never skipped)

1. Fetch   → 2. Extract → 3. Clean → 4. Chunk → 5. Embed → 6. Upsert

## Step Executables

- Step Provider   = any executable dropped by the user
- Step Routine     = one named function inside a Step Provider that does exactly one canonical step

## Directory Layout (the single source of truth)

```
<KB-storage-directory>/
└── <kb-name>/
    └── <version>/
        ├── 10_raw/           # original files (bit-for-bit)
        ├── 20_extracted/     # .md with mandatory YAML front-matter
        ├── 30_cleaned/       # refined .md (still with front-matter)
        ├── 40_chunked/       # .jsonl or .json files
        └── meta.json         # tiny manifest
```

## Mandatory YAML Front-Matter (in every .md file)

```yaml
---
kb_name: hr
version: 2025.51.7
file_id: hr/2025.51.7/10_raw/vacation-policy-2025.docx
filename: vacation-policy-2025.docx
source_ref: sharepoint://HR-Policies
fetched_at: 2025-11-18T14:22:17Z
extracted_at: 2025-11-18T14:25:41Z
title: Vacation Policy 2025
authors:
  - Jane Doe
# …any additional fields allowed
---
```

This front-matter + the directory tree is sufficient to **fully rebuild the entire database** from scratch.

## Golden Rules (non-negotiable)

- The directory tree is the primary source of truth
- The database (SQLite or PostgreSQL) is a derived cache
- Extract must output clean, git-friendly Markdown with front-matter — no exceptions
- `kbquery(name="hr", …)` is the only way users search a Knowledge Base
- A complete backup = one gzipped version directory

## Commands (final)

```
keprompt kb run <pipeline-or-kb>      # build or update
keprompt kb restore backup.tar.gz     # rebuild DB from files
keprompt kb compress <kb>/<version>   # delete intermediate dirs you no longer need
```

That’s it.

Everything else is implementation detail.

# New External Function
```json
{
  "name": "kbsearch",
  "description": "Search a company Knowledge Base (hr, code, pricing, etc.) for up-to-date factual information",
  "parameters": {
    "type": "object",
    "properties": {
      "name": {"type": "string", "description": "Knowledge Base name"},
      "query": {"type": "string"},
      "top_k": {"type": "integer", "default": 12}
    },
    "required": ["name", "query"]
  }
}
```

# New Syntax to .cmd
In general the external functions return a json, with a response field...

The .cmd inserts the response into a variable.  the name of the variable is given with the "as var-name" clause at end

# Terms
Here is your model, written back to you exactly as you said it – only lightly formatted for permanence:

| Term                  | Exact meaning (pure semantics, 2025-11-18 final) |
|-----------------------|---------------------------------------------------|
| **Semantic Store**    | Abstract concept: “a thing that can answer semantic queries over a set of embedded text chunks”. |
| **Knowledge Base**    | Concrete, named instance of a Semantic Store with exactly these five attributes: |
| → **Name**            | Unique identifier you use in `kb_search(name="…")` (e.g. `"hr"`, `"code"`). |
| → **Source**          | Parameters that tell the **fetch** step where to get raw documents from (folders, URLs, APIs, repos, etc.). |
| → **Pipeline**        | Ordered list of exactly six executable routines, one for each canonical step: <br>1. fetch <br>2. extract <br>3. clean <br>4. chunk <br>5. embed <br>6. upsert |
| → **Access Interface**| The identifier(s) that `kb_search()` needs to talk to this KB (e.g. provider + collection name, endpoint, index name, etc.). |
| → **Data Store**      | The physical location where the final embedded chunks actually live (Qdrant collection, Pinecone index, local folder, etc.). |

**Perfect. Now we name the objects that actually do the work.**

We have six canonical steps (fetch → extract → clean → chunk → embed → upsert).  
Each step is performed by **one step routine**.

| Term                  | What it **actually** is (pure object, no implementation-agnostic) | Where it physically lives in KePrompt (for reference only – we are still only naming) |
|-----------------------|---------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| **Step Provider**     | An **executable** (script, binary, Python file, whatever) that contains **one or more** Step Routines. | Dropped by the user anywhere the system looks – most natural place is a directory called `kb_steps/` or `rag_steps/` |
| **Step Routine**      | A **single named function/routine** inside a Step Provider that implements **exactly one** canonical step (fetch / extract / clean / chunk / embed / upsert). | Inside the Step Provider executable |
| **Pipeline**          | The **ordered list of six Step Routines** (one for each canonical step) plus the concrete arguments that will be passed to them. | Defined inside the Knowledge Base (or in a separate pipeline definition – TBD) |
| 
| **Knowledge Base**    | The only first-class, named object the user ever talks about. It owns:<br>• Name<br>• Source description<br>• Pipeline<br>• Access Interface<br>• Data Store | The thing you refer to with `kb_search(name="hr")` |

# **KePrompt RAG – Final `kb.db` schema (2025 canon)**  
(SQLite + PostgreSQL compatible – this is what ships)

```sql
-- Main table: all Knowledge Bases and their versions
CREATE TABLE kb_versions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    kb_name       TEXT    NOT NULL,                  -- "hr", "code", "pricing"
    version       TEXT    NOT NULL,                  -- "2025.51.7"
    status        TEXT    NOT NULL DEFAULT 'building', -- building | active | failed | archived
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at   TIMESTAMP,
    source        TEXT    NOT NULL,                  -- raw Source definition
    pipeline      TEXT,                             -- JSON or string representation of pipeline
    access_interface TEXT NOT NULL,                 -- e.g. '{"provider":"qdrant","collection":"hr_2025"}'
    data_store    TEXT    NOT NULL,                  -- e.g. same as collection, or full connection info
    metadata      JSON    DEFAULT '{}',             -- free-form tags
    stats         JSON    DEFAULT '{}',             -- docs_processed, chunks_created, etc.
    UNIQUE(kb_name, version)
);

-- Index for fast "current active version" lookup
CREATE INDEX idx_kb_active ON kb_versions(kb_name, status) WHERE status = 'active';

-- Per-version file manifest (one row per original file)
CREATE TABLE kb_files (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    kb_name       TEXT    NOT NULL,
    version       TEXT    NOT NULL,
    filename      TEXT    NOT NULL,                  -- "vacation-policy-2025.docx"
    file_id       TEXT    NOT NULL UNIQUE,            -- full versioned path: "hr/2025.51.7/10_raw/..."
    source_ref    TEXT,
    fetched_at    TIMESTAMP,
    extracted_at  TIMESTAMP,
    title         TEXT,
    authors       JSON,
    file_type     TEXT,
    size_bytes    INTEGER,
    metadata      JSON    DEFAULT '{}',
    FOREIGN KEY(kb_name, version) REFERENCES kb_versions(kb_name, version) ON DELETE CASCADE
);

-- Optional: chunk → vector ID mapping (only needed for hybrid search or debugging)
CREATE TABLE kb_chunks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    kb_name       TEXT    NOT NULL,
    version       TEXT    NOT NULL,
    chunk_id      TEXT    NOT NULL,                  -- stable chunk identifier
    file_id       TEXT    NOT NULL,                  -- links back to kb_files.file_id
    vector_id     TEXT,                             -- ID in the vector DB (if provider exposes it)
    text_hash     TEXT,                             -- SHA256 of chunk text (for dedup)
    metadata      JSON    DEFAULT '{}',
    FOREIGN KEY(kb_name, version) REFERENCES kb_versions(kb_name, version) ON DELETE CASCADE,
    UNIQUE(kb_name, version, chunk_id)
);

-- Tiny helper: current active version per KB (materialised for speed)
CREATE TABLE kb_current (
    kb_name       TEXT PRIMARY KEY,
    version       TEXT NOT NULL,
    FOREIGN KEY(kb_name, version) REFERENCES kb_versions(kb_name, version)
);
```

### Why this schema is perfect

| Table        | Reason it exists |
|--------------|------------------|
| `kb_versions`| One row per built version – full history & rollback |
| `kb_files`   | Lets you answer “what files are in version X?” without touching filesystem |
| `kb_chunks`  | Optional – only needed if you want chunk-level tracing or hybrid search |
| `kb_current` | O(1) lookup for “what is the active hr KB right now?” |

### Restoration guarantee

Run this on any backed-up version directory and the entire DB is **100 % reconstructed**:

```bash
keprompt kb restore hr/2025.51.7/ --db kb.db
```

→ scans `10_raw/`, `20_extracted/`, `30_cleaned/`, reads every YAML front-matter → rebuilds all tables perfectly.

This schema + the directory tree = **bulletproof, enterprise-grade, future-proof RAG**.

# **FINAL, LOCKED-IN KePrompt Knowledge Base directory structure (2025–forever canon)**

```
<KB-storage-directory>/          ← configurable, e.g. /var/keprompt/kb/ or ./kb/
└── <kb-name>/                   ← e.g. hr, code, pricing, legal
    └── <version>/               ← e.g. 2025.51.7, 2025.52.1, v17
        ├── 10_raw/              ← Fetch output – original files, bit-for-bit
        │   ├── vacation-policy-2025.docx
        │   ├── remote-work-guidelines.pdf
        │   └── …
        │
        ├── 20_extracted/        ← Extract output – clean Markdown with mandatory YAML front-matter
        │   ├── vacation-policy-2025.md
        │   ├── remote-work-guidelines.md
        │   └── …
        │
        ├── 30_cleaned/          ← Clean output – refined Markdown (still .md, still has front-matter)
        │   ├── vacation-policy-2025.md
        │   ├── remote-work-guidelines.md
        │   └── …
        │
        ├── 40_chunked/          ← Chunk output – one .jsonl file per original document
        │   ├── vacation-policy-2025.jsonl
        │   ├── remote-work-guidelines.jsonl
        │   └── …
        │
        ├── 50_embedded/         ← (optional – cached embeddings if you want them on disk)
        │   └── vacation-policy-2025.vectors
        │
        └── meta.json            ← tiny manifest (auto-generated)
            {
              "kb_name": "hr",
              "version": "2025.51.7",
              "created_at": "2025-11-18T14:22:17Z",
              "status": "active",
              "source": "sharepoint://HR-Policies",
              "pipeline": "...",
              "stats": { "files": 47, "chunks": 2841 }
            }
```

### Absolute rules (never broken)

- Every step gets its **own numbered directory** → perfect debugging & selective `--compress`
- **Only** `10_raw/` and `30_cleaned/` are **mandatory** to keep forever
- `20_extracted/` can be deleted after Clean passes QA
- `40_chunked/` can be regenerated from `30_cleaned/` → safe to delete
- A single `tar.gz` of `<kb-name>/<version>/` = **complete, legal, restorable backup**
- `keprompt kb restore backup.tar.gz` rebuilds the entire database from these files alone

# ** command for Step Provider discovery (KePrompt 2025 canon)**

Every Step Provider executable **must** respond to this exact argument:

```bash
./my_step_provider --kb-step-list
```

**Output format (stdout, must be valid JSON):**

```json
{
  "provider_name": "unstructured_extractor",
  "steps": [
    {
      "step": "extract",
      "description": "Extract clean Markdown from PDFs, DOCX, PPTX using Unstructured.io",
      "version": "2025.11",
      "supports": ["pdf", "docx", "pptx", "html", "txt"]
    }
  ]
}
```

### Real examples

```bash
$ ./extract_unstructured --kb-step-list
{"provider_name":"unstructured_extractor","steps":[{"step":"extract", ...}]}

$ ./chunk_hierarchical --kb-step-list
{"provider_name":"hierarchical_chunker","steps":[{"step":"chunk", ...}]}

$ ./fetch_sharepoint --kb-step-list
{"provider_name":"sharepoint_fetcher","steps":[{"step":"fetch", ...}]}

$ ./my_pipe_line --kb-step-list
{"provider_name":"pine_pipe_line","steps":[
  {"step":"extract", ...},
  {"step":"chunk", ...},
  {"step":"fetch", ...}
]}

```

### Optional: also support the short form (both work)

```bash
./my_step_provider --list-steps
```

→ same JSON output

### Why this wins forever

| Property              | This design |
|-----------------------|-----------|
| Instantly discoverable | `find kb_steps/ -type f -executable -exec {} --kb-step-list \;` works perfectly |
| LLM-friendly          | Tools can auto-generate schema |
| Zero config files     | Pure KePrompt style |
| Works on any language | Python, Bash, Go, Rust — all can print JSON |

### Final rule (never broken)

> **Any executable that wants to be a Step Provider must print valid JSON on `--kb-step-list` describing routines it implements.**

