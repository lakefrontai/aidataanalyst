# AI Data Analyst

Ask questions about your data in plain English. The app writes the SQL, runs it, and explains the results — powered by any model on **AWS Bedrock**, connected to **multiple databases simultaneously**.

![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)
![AWS Bedrock](https://img.shields.io/badge/AI-AWS%20Bedrock-orange)

---

## What it does

```
You type:   "How many open disputes were submitted this month?"
               ↓
Mistral / Nova / Claude generates SQL
               ↓
Your database runs the query
               ↓
AI summarises the results in plain English + auto chart
```

You can keep **multiple databases connected at once** and switch between them in a single dropdown — no need to disconnect and reconnect.

---

## Supported databases

| Database | Auth method |
|---|---|
| ❄️ Snowflake | Username + password + warehouse |
| 🐘 AWS RDS PostgreSQL | Password + SSL |
| 💻 Local PostgreSQL | Password |
| 🐬 MySQL / Aurora MySQL | Username + password |

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.9+ | `python3 --version` to check |
| AWS account | Free to create at aws.amazon.com |
| IAM user with `AmazonBedrockFullAccess` | See Step 2 |
| One of the supported databases | See above |

---

## Step 1 — Clone and install

```bash
git clone https://github.com/lakefrontai/aidataanalyst.git
cd aidataanalyst

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### MySQL driver (installed automatically via requirements.txt)

```bash
pip install mysql-connector-python
```

> If you see `ModuleNotFoundError: No module named 'mysql'`, run the above command manually.

---

## Step 2 — Get AWS Bedrock credentials

1. Sign in to **console.aws.amazon.com**
2. Go to **IAM → Users → Create user** (e.g. name it `bedrock-analyst`)
3. Click **Add permissions → Attach policies directly**
4. Search for and attach **`AmazonBedrockFullAccess`**
5. Go to the user → **Security credentials → Create access key**
6. Choose **"Local code"** → copy both values:
   - `Access Key ID` (starts with `AKIA…`)
   - `Secret Access Key` (40 characters)

> ⚠️ The Secret Access Key is shown **only once**. Copy it before closing the dialog.

---

## Step 3 — Run the app

```bash
source venv/bin/activate
streamlit run app.py
```

The app opens at **http://localhost:8501**

---

## Step 4 — Connect AWS Bedrock

1. Open the **🔌 Connections** tab
2. Expand **☁️ AWS Bedrock**
3. Enter your **Access Key ID** and **Secret Access Key**
4. Select your **region** (recommend `us-east-1`)
5. Click **🔍 Load available models** to see every model in your account
6. Select a model — recommendations:

| Model | Best for |
|---|---|
| `amazon.nova-pro-v1:0` | Best SQL quality, supports system messages |
| `mistral.mistral-large-3-675b-instruct` | Strong SQL, fast |
| `mistral.mistral-small-2402-v1:0` | Cheapest Mistral option |
| `anthropic.claude-3-5-haiku…` | Fast + accurate |

---

## Step 5 — Connect your database(s)

Still in the **🔌 Connections** tab:

1. Use the **"Select database type"** dropdown to pick your DB
2. Give the connection a friendly **name** (e.g. `Sales DB`, `Analytics PG`)
3. Fill in the credentials and click **Connect**
4. Repeat to add more databases — all connections stay active simultaneously
5. Switch between databases in the **Chat** tab dropdown or the sidebar

---

### Connection details by type

### ❄️ Snowflake
| Field | Example |
|---|---|
| Account identifier | `myorg-myaccount` |
| Username | `analyst` |
| Password | your password |
| Warehouse | `COMPUTE_WH` |
| Database | `SALES_DB` |
| Schema | `PUBLIC` |

### 🐘 AWS RDS PostgreSQL
| Field | Example |
|---|---|
| RDS Endpoint | `mydb.xxxx.us-east-1.rds.amazonaws.com` |
| Port | `5432` |
| Database | `postgres` |
| Username | `postgres` |
| SSL mode | `require` |

### 💻 Local PostgreSQL
| Field | Example |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `mydb` |
| Username | `postgres` |
| SSL mode | `disable` |

### 🐬 MySQL / Aurora MySQL
| Field | Example |
|---|---|
| Host | `localhost` or `mydb.xxxx.rds.amazonaws.com` |
| Port | `3306` |
| Database | `mydb` |
| Username | `root` |
| Password | your password |
| Disable SSL | check for local dev, leave unchecked for RDS |
| Display label | `Production MySQL` |

Click **🔌 Connect** — the app loads your schema. You can add more connections without disconnecting existing ones.

---

## Step 6 — Ask questions (with multiple databases)

Switch to the **💬 Chat** tab. If you have multiple connections:
- Use the **"Query database"** dropdown at the top of the chat to select which database to query
- Each database has its own independent chat history
- Switch at any time — no reconnection needed

Type any data question:

```
How many open disputes are there?
What are the top 10 customers by revenue this quarter?
Show me monthly sales trends for the last 6 months
Which products have the highest return rate?
Compare this month's orders to last month
```

The app shows:
- **Generated SQL** — expandable, so you can verify what ran
- **Results table** — with row count
- **Auto chart** — line, bar, scatter, or pie based on the data shape
- **AI summary** — plain English explanation of the findings

---

## Step 7 — (Optional) Enable pgvector for smarter queries

For databases with many tables, pgvector stores your schema as embeddings and retrieves only the relevant tables per question — improving accuracy and reducing cost.

### Install pgvector

**macOS — EnterpriseDB PostgreSQL**
```bash
cd /tmp && git clone --branch v0.8.3 https://github.com/pgvector/pgvector.git
cd /tmp/pgvector
sudo PG_CONFIG=/Library/PostgreSQL/18/bin/pg_config make install
/Library/PostgreSQL/18/bin/psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**macOS — Homebrew PostgreSQL**
```bash
brew install pgvector
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**AWS RDS / Aurora PostgreSQL**
```sql
-- Just run this in your database (pgvector is pre-installed on RDS):
CREATE EXTENSION IF NOT EXISTS vector;
```

**Linux (Ubuntu/Debian)**
```bash
sudo apt install postgresql-16-pgvector   # replace 16 with your version
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Connect pgvector in the app

1. Open the **🧠 Vector Store** tab
2. Fill in your PostgreSQL connection details (can be the same DB)
3. Choose an embedding model:
   - `amazon.titan-embed-text-v2:0` ← recommended
   - `cohere.embed-english-v3` ← high quality English
   - `cohere.embed-multilingual-v3` ← for non-English data
4. Click **🔌 Connect pgvector**
5. Click **⚡ Index schema now**

From this point, every question uses semantic search to find the right tables — you'll see a **🧠 vector retrieval** badge in chat.

---

## Sidebar features

| Feature | What it does |
|---|---|
| 🗂️ Tables | Browse and search all tables in your database |
| 👁 Preview | See 10 sample rows from any table |
| 💬 Ask | Pre-fill a question about a selected table |
| ⚡ Quick Queries | One-click common analysis patterns |
| 📈 Session Stats | Query count and rows retrieved this session |
| 🔄 Schema | Reload schema from the database |
| 🗑️ Clear | Clear chat history |

---

## Project structure

```
aidataanalyst/
├── app.py                # Streamlit UI — Chat, Connections, Vector Store tabs
├── analyst.py            # Orchestration — schema → SQL → execute → summarise
├── bedrock_client.py     # AWS Bedrock Converse API wrapper (any model)
├── model_discovery.py    # Live model listing from Bedrock
├── vector_store.py       # pgvector schema embeddings and retrieval
├── db_base.py            # Abstract base class for all DB connectors
├── snowflake_client.py   # Snowflake connector
├── postgres_client.py    # PostgreSQL connector (local + AWS RDS)
├── mysql_client.py       # MySQL / Aurora MySQL connector
├── config.py             # Environment variable loader
├── main.py               # Optional CLI interface
└── requirements.txt
```

---

## Cost

The app uses **AWS Bedrock on-demand pricing** — you pay per token, not per invocation.

| Model | Input / 1M tokens | Output / 1M tokens | Typical cost per question |
|---|---|---|---|
| Mistral Large 3 | ~$2.00 | ~$6.00 | ~$0.01 |
| Mistral Small | ~$0.90 | ~$2.70 | ~$0.003 |
| Mistral 7B | ~$0.15 | ~$0.20 | ~$0.001 |
| Amazon Nova Pro | ~$0.80 | ~$3.20 | ~$0.005 |

Set a billing alert: **AWS Console → Billing → Budgets → Create budget**

---

## Troubleshooting

**`UnrecognizedClientException: security token is invalid`**  
→ Wrong Access Key ID or Secret. Regenerate in IAM → Security credentials.

**`ValidationException: This model doesn't support system messages`**  
→ The app handles this automatically with a fallback. If you still see it, try a different model.

**`extension "vector" is not available`** (pgvector)  
→ Follow the install steps in Step 7 above or expand the install guide in the Vector Store tab.

**Schema loads but model says table doesn't exist**  
→ Click **🔄 Schema** in the sidebar to refresh. If using pgvector, re-index with **⚡ Index schema now**.

**`ModuleNotFoundError: No module named 'mysql'`**  
→ Run `pip install mysql-connector-python`

**MySQL connection refused**  
→ Make sure the MySQL server is running and the user has remote access: `GRANT ALL ON mydb.* TO 'user'@'%';`

**Switching databases in chat doesn't work**  
→ Use the **"Query database"** dropdown at the top of the chat tab, or the connection selector in the sidebar.

---

## Contributing

Pull requests welcome. Please open an issue first for large changes.

---

*Built with [Streamlit](https://streamlit.io) · [AWS Bedrock](https://aws.amazon.com/bedrock) · [pgvector](https://github.com/pgvector/pgvector)*
