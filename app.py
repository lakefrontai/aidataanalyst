"""
AI Data Analyst — Streamlit UI
AWS Bedrock (any model) + multi-source DB + pgvector schema store
Supports multiple simultaneous database connections.
"""

import traceback
from typing import Optional, List, Dict
import pandas as pd
import plotly.express as px
import streamlit as st
import boto3

from bedrock_client import BedrockMistralClient
from fabric_client import FabricClient
from snowflake_client import SnowflakeClient
from postgres_client import PostgresClient
from mysql_client import MySQLClient
from analyst import AnalystSession
from model_discovery import list_bedrock_models, group_by_provider
from vector_store import SchemaVectorStore

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Data Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#f5f7fa; }
[data-testid="stSidebar"] { background:#ffffff; border-right:1px solid #e0e4ec; }

.banner {
    background:linear-gradient(135deg,#e8f0fe 0%,#f0f4ff 100%);
    border:1px solid #c5d3f0; border-radius:12px;
    padding:18px 24px; margin-bottom:20px;
    display:flex; align-items:center; gap:16px;
}
.banner-title {
    font-size:1.6rem; font-weight:700; margin:0;
    background:linear-gradient(90deg,#1a73e8,#7c4dff);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
.banner-sub { color:#5f6b7a; font-size:0.85rem; margin:4px 0 0 0; }

.conn-card {
    background:#ffffff; border:2px solid #e0e4ec;
    border-radius:14px; padding:16px 20px; margin-bottom:10px;
    display:flex; align-items:center; justify-content:space-between;
}
.conn-card.active { border-color:#1a73e8; background:#f0f7ff; }
.conn-card-left { display:flex; align-items:center; gap:12px; }
.conn-icon  { font-size:1.6rem; }
.conn-name  { font-size:1rem; font-weight:700; color:#1a1a2e; }
.conn-desc  { font-size:0.78rem; color:#5f6b7a; margin:0; }
.conn-badge { display:inline-block; padding:2px 10px; border-radius:20px;
              font-size:0.7rem; font-weight:700; margin-top:4px; }
.badge-connected    { background:#e6f4ea; color:#1e7e34; border:1px solid #a8d5b5; }
.badge-disconnected { background:#f5f5f5; color:#757575; border:1px solid #e0e0e0; }
.badge-vector       { background:#ede7f6; color:#5e35b1; border:1px solid #c5b3e6; }

.chat-user {
    background:#e8f0fe; border:1px solid #c5d3f0;
    border-radius:16px 16px 4px 16px; padding:12px 16px;
    margin:8px 0 8px 60px; color:#1a1a2e; font-size:0.95rem;
}
.chat-assistant {
    background:#ffffff; border:1px solid #e0e4ec;
    border-radius:16px 16px 16px 4px; padding:12px 16px;
    margin:8px 60px 8px 0; color:#1a1a2e; font-size:0.95rem;
    box-shadow:0 1px 4px rgba(0,0,0,0.06);
}
.chat-label-user { font-size:0.72rem; color:#1a73e8; font-weight:600;
                   text-align:right; margin-bottom:2px; }
.chat-label-ai   { font-size:0.72rem; color:#7c4dff; font-weight:600; margin-bottom:2px; }

.sidebar-section { font-size:0.7rem; font-weight:700; color:#1a73e8;
                   text-transform:uppercase; letter-spacing:1px; margin:18px 0 6px 0; }

.metric-card { background:#ffffff; border:1px solid #e0e4ec;
               border-radius:10px; padding:16px; text-align:center;
               box-shadow:0 1px 4px rgba(0,0,0,0.05); }
.metric-value { font-size:1.8rem; font-weight:700; color:#1a73e8; }
.metric-label { font-size:0.78rem; color:#5f6b7a; margin-top:4px; }

.vs-info { background:#f3f0ff; border:1px solid #c5b3e6; border-radius:8px;
           padding:10px 14px; font-size:0.82rem; color:#3d1f8a; margin:8px 0; }

.active-conn-row { background:#f0f7ff; border:1px solid #c5d3f0; border-radius:10px;
                   padding:10px 14px; margin-bottom:8px;
                   display:flex; align-items:center; justify-content:space-between; }

.stButton>button {
    background:linear-gradient(135deg,#1a73e8,#7c4dff) !important;
    color:white !important; border:none !important;
    border-radius:8px !important; font-weight:600 !important;
}
#MainMenu, footer, header { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


# ── Chart helper ──────────────────────────────────────────────────────────────
def _auto_chart(df: pd.DataFrame):
    if df.empty or len(df.columns) < 2:
        st.info("Not enough columns for a chart.")
        return
    num_cols  = df.select_dtypes(include="number").columns.tolist()
    cat_cols  = df.select_dtypes(include=["object", "category"]).columns.tolist()
    date_cols = [c for c in df.columns
                 if any(k in c.lower() for k in ("date","month","year","time","week"))]
    try:
        if date_cols and num_cols:
            fig = px.line(df, x=date_cols[0], y=num_cols[0], template="plotly_white",
                          title=f"{num_cols[0]} over {date_cols[0]}")
        elif cat_cols and num_cols:
            fig = px.bar(df[[cat_cols[0], num_cols[0]]].head(20),
                         x=cat_cols[0], y=num_cols[0], template="plotly_white",
                         title=f"{num_cols[0]} by {cat_cols[0]}",
                         color=num_cols[0], color_continuous_scale="Blues")
        elif len(num_cols) >= 2:
            fig = px.scatter(df, x=num_cols[0], y=num_cols[1], template="plotly_white",
                             title=f"{num_cols[1]} vs {num_cols[0]}")
        elif num_cols and cat_cols:
            fig = px.pie(df.head(10), names=cat_cols[0], values=num_cols[0],
                         template="plotly_white", title=f"{num_cols[0]} distribution")
        else:
            st.info("Could not determine a suitable chart type.")
            return
        fig.update_layout(plot_bgcolor="#ffffff", paper_bgcolor="#f5f7fa",
                          font_color="#1a1a2e",
                          margin={"l": 20, "r": 20, "t": 40, "b": 20})
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info(f"Auto-chart unavailable: {e}")


# ── Bedrock helpers ───────────────────────────────────────────────────────────
def _make_bedrock(model_id: str = "") -> BedrockMistralClient:
    key    = st.session_state.get("bk_key", "")
    secret = st.session_state.get("bk_secret", "")
    region = st.session_state.get("bk_region", "us-east-1")
    model  = model_id or st.session_state.get("bk_model", "")
    if not key or not secret:
        raise ValueError("AWS Access Key ID and Secret Access Key are required.")
    b = BedrockMistralClient.__new__(BedrockMistralClient)
    b._client = boto3.client(
        "bedrock-runtime",
        region_name=region,
        aws_access_key_id=key,
        aws_secret_access_key=secret,
    )
    b.model_id = model
    return b


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_models(aws_key: str, aws_secret: str, aws_region: str) -> List[Dict]:
    if not aws_key or not aws_secret:
        return []
    try:
        return list_bedrock_models(aws_key, aws_secret, aws_region)
    except Exception:
        return []


# ── Multi-connection helpers ──────────────────────────────────────────────────
def _add_connection(name: str, db_client, db_type: str) -> None:
    """Connect a DB client, create an analyst session, store in connections dict."""
    db_client.connect()
    vs      = st.session_state.get("vs")
    bedrock = _make_bedrock()
    analyst = AnalystSession(db_client, bedrock, vector_store=vs)
    schema  = analyst.load_schema()
    tables  = db_client.list_tables()
    st.session_state.connections[name] = {
        "client":   db_client,
        "session":  analyst,
        "bedrock":  bedrock,
        "type":     db_type,
        "label":    db_client.label,
        "schema":   schema,
        "tables":   tables,
        "messages": [],
        "total_queries": 0,
        "total_rows":    0,
    }
    st.session_state.active_conn = name


def _remove_connection(name: str) -> None:
    """Disconnect and remove a connection from the registry."""
    conn = st.session_state.connections.pop(name, None)
    if conn:
        try:
            conn["client"].disconnect()
        except Exception:
            pass
    # If removed conn was active, switch to another
    if st.session_state.active_conn == name:
        remaining = list(st.session_state.connections.keys())
        st.session_state.active_conn = remaining[0] if remaining else None


def _active_conn() -> Optional[Dict]:
    name = st.session_state.active_conn
    return st.session_state.connections.get(name) if name else None


# ── Session state ─────────────────────────────────────────────────────────────
_DEFAULTS: Dict = {
    # Multi-connection registry
    "connections":   {},     # {name: {client, session, bedrock, type, label, schema, tables, messages, ...}}
    "active_conn":   None,   # name of connection used in chat
    # Saved form values per connector type
    "sf_saved":    {}, "fab_saved":  {}, "pgaws_saved": {},
    "pgloc_saved": {}, "mysql_saved": {},
    # Bedrock
    "bk_key": "", "bk_secret": "", "bk_region": "us-east-1", "bk_model": "",
    "bk_models_list": [],
    # Vector store
    "vs": None,
    "vs_connected": False,
    "vs_saved": {},
    "vs_indexed_count": 0,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:10px 0 18px 0;'>
        <div style='font-size:2rem;'>📊</div>
        <div style='font-weight:700;color:#1a1a2e;font-size:1.05rem;'>AI Data Analyst</div>
        <div style='color:#5f6b7a;font-size:0.75rem;'>Bedrock · Any Model · Multi-DB</div>
    </div>
    """, unsafe_allow_html=True)

    connections = st.session_state.connections
    active_name = st.session_state.active_conn
    conn_names  = list(connections.keys())

    if conn_names:
        # Active connection switcher
        st.markdown('<div class="sidebar-section">🔌 Active Connections</div>',
                    unsafe_allow_html=True)
        if len(conn_names) > 1:
            chosen = st.selectbox(
                "Query database",
                conn_names,
                index=conn_names.index(active_name) if active_name in conn_names else 0,
                key="sidebar_conn_select",
                label_visibility="collapsed",
            )
            if chosen != active_name:
                st.session_state.active_conn = chosen
                st.rerun()
        else:
            st.success(f"● {conn_names[0]}", icon="✅")

        if st.session_state.vs_connected:
            st.markdown('<span class="conn-badge badge-vector">🧠 pgvector active</span>',
                        unsafe_allow_html=True)
        st.caption(f"🤖 `{st.session_state.get('bk_model','')}`")

        conn_data = _active_conn()
        if conn_data:
            table_list = conn_data.get("tables", [])

            st.markdown('<div class="sidebar-section">🗂️ Tables</div>',
                        unsafe_allow_html=True)
            search = st.text_input("Filter tables", placeholder="search…",
                                   label_visibility="collapsed", key="tbl_search")
            tables = ([t for t in table_list if search.lower() in t.lower()]
                      if search else table_list)
            selected = st.selectbox(
                "Table", tables, index=None, placeholder="Choose a table…",
                label_visibility="collapsed", key="sel_table",
            )
            if selected:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("👁 Preview", use_container_width=True, key="btn_prev"):
                        st.session_state["preview_table"] = selected
                with c2:
                    if st.button("💬 Ask", use_container_width=True, key="btn_ask"):
                        conn_data["messages"].append({
                            "role": "user",
                            "content": f"Describe the {selected} table and show me a summary",
                            "_prefill": True,
                        })
            st.caption(f"{len(table_list)} tables")

            st.markdown('<div class="sidebar-section">⚡ Quick Queries</div>',
                        unsafe_allow_html=True)
            for q in [
                "What are the top 10 records by most recent date?",
                "Show row counts for all tables",
                "Show me data trends over the last 30 days",
                "What are the top 5 values in the most common column?",
            ]:
                if st.button(q[:44]+("…" if len(q)>44 else ""),
                             use_container_width=True, key=f"qq_{hash(q)}"):
                    st.session_state["prefill"] = q

            st.markdown('<div class="sidebar-section">📈 Session Stats</div>',
                        unsafe_allow_html=True)
            m1, m2 = st.columns(2)
            m1.metric("Queries", conn_data.get("total_queries", 0))
            m2.metric("Rows",    conn_data.get("total_rows", 0))

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                if st.button("🗑️ Clear chat", use_container_width=True):
                    conn_data["messages"] = []
                    if conn_data.get("session"):
                        conn_data["session"].reset_history()
                    st.rerun()
            with cb:
                if st.button("🔄 Schema", use_container_width=True):
                    with st.spinner("Reloading…"):
                        conn_data["schema"] = conn_data["session"].load_schema(force=True)
                        conn_data["tables"] = conn_data["client"].list_tables()
                    st.success("Refreshed!")
    else:
        st.info("No database connected.\nGo to **Connections** to add one.")


# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="banner">
  <div style="font-size:2.4rem;">📊</div>
  <div>
    <p class="banner-title">AI Data Analyst</p>
    <p class="banner-sub">Plain English → SQL → Results. Any Bedrock model. Multiple databases.</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Top-level tabs ────────────────────────────────────────────────────────────
tab_chat, tab_conn, tab_vs = st.tabs(["💬  Chat", "🔌  Connections", "🧠  Vector Store"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB: CONNECTIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab_conn:
    st.markdown("### Configure data sources")

    # ── AWS Bedrock ───────────────────────────────────────────────────────────
    with st.expander("☁️ **AWS Bedrock** *(required — choose any available model)*",
                     expanded=not conn_names):
        bc1, bc2 = st.columns(2)
        with bc1:
            bk_key = st.text_input("Access Key ID", type="password", key="bk_key_in",
                                   value=st.session_state.bk_key)
            bk_region = st.selectbox("Region",
                ["us-east-1","us-west-2","eu-west-1","eu-central-1",
                 "ap-southeast-1","ap-northeast-1"],
                index=["us-east-1","us-west-2","eu-west-1","eu-central-1",
                       "ap-southeast-1","ap-northeast-1"].index(
                    st.session_state.bk_region
                    if st.session_state.bk_region in
                    ["us-east-1","us-west-2","eu-west-1","eu-central-1","ap-southeast-1","ap-northeast-1"]
                    else "us-east-1"),
                key="bk_region_in")
        with bc2:
            bk_secret = st.text_input("Secret Access Key", type="password", key="bk_secret_in",
                                      value=st.session_state.bk_secret)

        st.session_state.bk_key    = bk_key
        st.session_state.bk_secret = bk_secret
        st.session_state.bk_region = bk_region

        col_load, _ = st.columns([2, 3])
        with col_load:
            if st.button("🔍 Load available models", key="load_models"):
                with st.spinner("Fetching model list from Bedrock…"):
                    try:
                        models = list_bedrock_models(bk_key, bk_secret, bk_region)
                        st.session_state.bk_models_list = models
                        st.success(f"{len(models)} models found.")
                    except Exception as e:
                        st.error(f"Failed: {e}")

        models_list = st.session_state.bk_models_list
        if models_list:
            grouped = group_by_provider(models_list)
            options = [m["model_id"] for prov in sorted(grouped) for m in grouped[prov]]
            current = st.session_state.bk_model
            default_idx = options.index(current) if current in options else 0

            st.caption(f"**{len(options)} models** available across {len(grouped)} providers")
            provider_cols = st.columns(min(len(grouped), 4))
            for i, (prov, ms) in enumerate(sorted(grouped.items())):
                if i < len(provider_cols):
                    provider_cols[i].metric(prov, f"{len(ms)} models")

            chosen = st.selectbox("Select model", options, index=default_idx,
                                  key="bk_model_select")
            st.session_state.bk_model = chosen
            chosen_info = next((m for m in models_list if m["model_id"] == chosen), None)
            if chosen_info:
                st.info(f"**Provider:** {chosen_info['provider']} · "
                        f"**Input:** {chosen_info['input']} · "
                        f"**Output:** {chosen_info['output']}")
        else:
            manual_model = st.text_input(
                "Model ID (paste manually or click Load above)",
                value=st.session_state.bk_model,
                placeholder="e.g. amazon.nova-pro-v1:0",
                key="bk_model_manual",
            )
            st.session_state.bk_model = manual_model

    st.divider()

    # ── Active connections ────────────────────────────────────────────────────
    st.markdown("#### Active connections")
    if not connections:
        st.info("No connections yet. Add one below.")
    else:
        for cname, cdata in list(connections.items()):
            is_active = cname == st.session_state.active_conn
            icon_map = {
                "snowflake": "❄️", "fabric": "🏭",
                "pgaws": "🐘", "pglocal": "💻", "mysql": "🐬",
            }
            icon = icon_map.get(cdata["type"], "🗄️")
            col_info, col_switch, col_disc = st.columns([4, 2, 1])
            with col_info:
                badge = ("🟢 **Active**" if is_active else "⚪ Standby")
                st.markdown(
                    f"{icon} **{cname}** · `{cdata['label']}` · "
                    f"{len(cdata.get('tables', []))} tables · {badge}"
                )
            with col_switch:
                if not is_active:
                    if st.button("Set active", key=f"activate_{cname}",
                                 use_container_width=True):
                        st.session_state.active_conn = cname
                        st.rerun()
            with col_disc:
                if st.button("✕", key=f"disc_{cname}", use_container_width=True,
                             help=f"Disconnect {cname}"):
                    _remove_connection(cname)
                    st.rerun()

    st.divider()

    # ── Add new connection ────────────────────────────────────────────────────
    st.markdown("#### Add a new connection")

    DB_TYPES = {
        "❄️  Snowflake":             "snowflake",
        "🏭  Microsoft Fabric":      "fabric",
        "🐘  AWS RDS PostgreSQL":    "pgaws",
        "💻  Local PostgreSQL":      "pglocal",
        "🐬  MySQL / Aurora MySQL":  "mysql",
    }

    chosen_label = st.selectbox(
        "Select database type",
        list(DB_TYPES.keys()),
        key="new_db_type",
    )
    db_type_key = DB_TYPES[chosen_label]

    # Key includes db_type so the widget resets automatically when the type changes.
    # After a successful connect we delete this key so the next render gets a fresh default.
    _name_key = f"new_conn_name_{db_type_key}"
    conn_name_default = f"{chosen_label.split()[-1]} {len(connections)+1}"
    # Only write the default into session state when the key is absent or stale
    # (i.e. the stored name already exists as a connection — auto-increment it)
    if _name_key not in st.session_state or st.session_state[_name_key] in connections:
        st.session_state[_name_key] = conn_name_default
    conn_name = st.text_input(
        "Connection name",
        key=_name_key,
        help="A friendly name to identify this connection (e.g. 'Sales DB', 'Analytics PG')",
    )

    # ── Snowflake ─────────────────────────────────────────────────────────────
    if db_type_key == "snowflake":
        s = st.session_state.sf_saved
        sf1, sf2 = st.columns(2)
        with sf1:
            sf_account  = st.text_input("Account identifier",
                placeholder="myorg-myaccount", key="sf_account", value=s.get("account",""))
            sf_user     = st.text_input("Username", key="sf_user", value=s.get("user",""))
            sf_password = st.text_input("Password", type="password", key="sf_pass",
                value=s.get("password",""))
        with sf2:
            sf_warehouse = st.text_input("Warehouse", key="sf_wh", value=s.get("warehouse",""))
            sf_database  = st.text_input("Database",  key="sf_db", value=s.get("database",""))
            sf_schema    = st.text_input("Schema", value=s.get("schema","PUBLIC"), key="sf_schema")
            sf_role      = st.text_input("Role (optional)", key="sf_role", value=s.get("role",""))
        sf_maxrows = st.slider("Max rows", 10, 500, s.get("max_rows",50), key="sf_maxrows")
        if st.button("🔌 Connect to Snowflake", key="conn_sf", use_container_width=True):
            if not conn_name.strip():
                st.error("Enter a connection name.")
            elif conn_name in connections:
                st.error(f"A connection named '{conn_name}' already exists.")
            else:
                st.session_state.sf_saved = {
                    "account": sf_account, "user": sf_user, "password": sf_password,
                    "warehouse": sf_warehouse, "database": sf_database,
                    "schema": sf_schema, "role": sf_role, "max_rows": sf_maxrows,
                }
                with st.spinner("Connecting…"):
                    try:
                        _add_connection(conn_name, SnowflakeClient(
                            account=sf_account, user=sf_user, password=sf_password,
                            warehouse=sf_warehouse, database=sf_database,
                            schema=sf_schema, role=sf_role, max_rows=sf_maxrows),
                            "snowflake")
                        st.success(f"Connected: {conn_name}")
                        st.session_state.pop(_name_key, None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"{e}")

    # ── Microsoft Fabric ──────────────────────────────────────────────────────
    elif db_type_key == "fabric":
        s = st.session_state.fab_saved
        import config as cfg_module
        fab1, fab2 = st.columns(2)
        with fab1:
            fab_server = st.text_input("SQL Endpoint",
                placeholder="workspace.datawarehouse.fabric.microsoft.com",
                key="fab_server", value=s.get("server",""))
            fab_db = st.text_input("Database", key="fab_db", value=s.get("database",""))
        with fab2:
            fab_auth = st.radio("Authentication",
                ["Service Principal","Username / Password"],
                index=0 if s.get("auth","sp")=="sp" else 1, key="fab_auth")
        if fab_auth == "Service Principal":
            fa1, fa2 = st.columns(2)
            with fa1:
                fab_tenant = st.text_input("Tenant ID", type="password",
                    key="fab_tenant", value=s.get("tenant",""))
                fab_cid    = st.text_input("Client ID", type="password",
                    key="fab_cid", value=s.get("client_id",""))
            with fa2:
                fab_csec = st.text_input("Client Secret", type="password",
                    key="fab_csec", value=s.get("client_secret",""))
            fab_user = fab_pass = ""
        else:
            fa1, fa2 = st.columns(2)
            with fa1:
                fab_user = st.text_input("Username", key="fab_user", value=s.get("username",""))
            with fa2:
                fab_pass = st.text_input("Password", type="password",
                    key="fab_pass", value=s.get("password_up",""))
            fab_tenant = fab_cid = fab_csec = ""
        fab_maxrows = st.slider("Max rows", 10, 500, s.get("max_rows",50), key="fab_maxrows")
        if st.button("🔌 Connect to Fabric", key="conn_fab", use_container_width=True):
            if not conn_name.strip():
                st.error("Enter a connection name.")
            elif conn_name in connections:
                st.error(f"A connection named '{conn_name}' already exists.")
            else:
                st.session_state.fab_saved = {
                    "server": fab_server, "database": fab_db,
                    "auth": "sp" if fab_auth == "Service Principal" else "up",
                    "tenant": fab_tenant, "client_id": fab_cid, "client_secret": fab_csec,
                    "username": fab_user, "password_up": fab_pass, "max_rows": fab_maxrows,
                }
                cfg_module.config.FABRIC_SERVER        = fab_server
                cfg_module.config.FABRIC_DATABASE      = fab_db
                cfg_module.config.FABRIC_TENANT_ID     = fab_tenant
                cfg_module.config.FABRIC_CLIENT_ID     = fab_cid
                cfg_module.config.FABRIC_CLIENT_SECRET = fab_csec
                cfg_module.config.FABRIC_USERNAME      = fab_user
                cfg_module.config.FABRIC_PASSWORD      = fab_pass
                cfg_module.config.MAX_ROWS_DISPLAY     = fab_maxrows
                with st.spinner("Connecting…"):
                    try:
                        _add_connection(conn_name, FabricClient(), "fabric")
                        st.success(f"Connected: {conn_name}")
                        st.session_state.pop(_name_key, None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"{e}")

    # ── AWS RDS PostgreSQL ────────────────────────────────────────────────────
    elif db_type_key == "pgaws":
        s = st.session_state.pgaws_saved
        pg1, pg2 = st.columns(2)
        with pg1:
            pgaws_host = st.text_input("RDS Endpoint",
                placeholder="mydb.xxxx.us-east-1.rds.amazonaws.com",
                key="pgaws_host", value=s.get("host",""))
            pgaws_db   = st.text_input("Database", key="pgaws_db",
                value=s.get("database","postgres"))
            pgaws_user = st.text_input("Username", key="pgaws_user", value=s.get("user",""))
        with pg2:
            pgaws_port = st.number_input("Port", value=s.get("port",5432),
                min_value=1, max_value=65535, key="pgaws_port")
            pgaws_pass = st.text_input("Password", type="password",
                key="pgaws_pass", value=s.get("password",""))
            pgaws_ssl  = st.selectbox("SSL mode",
                ["require","verify-full","prefer","disable"],
                index=["require","verify-full","prefer","disable"].index(
                    s.get("sslmode","require")), key="pgaws_ssl")
        pgaws_maxrows = st.slider("Max rows", 10, 500, s.get("max_rows",50), key="pgaws_maxrows")
        if st.button("🔌 Connect to AWS RDS", key="conn_pgaws", use_container_width=True):
            if not conn_name.strip():
                st.error("Enter a connection name.")
            elif conn_name in connections:
                st.error(f"A connection named '{conn_name}' already exists.")
            else:
                st.session_state.pgaws_saved = {
                    "host": pgaws_host, "port": int(pgaws_port), "database": pgaws_db,
                    "user": pgaws_user, "password": pgaws_pass, "sslmode": pgaws_ssl,
                    "max_rows": pgaws_maxrows,
                }
                with st.spinner("Connecting…"):
                    try:
                        _add_connection(conn_name, PostgresClient(
                            host=pgaws_host, port=int(pgaws_port), database=pgaws_db,
                            user=pgaws_user, password=pgaws_pass, sslmode=pgaws_ssl,
                            max_rows=pgaws_maxrows, label="AWS RDS PostgreSQL"),
                            "pgaws")
                        st.success(f"Connected: {conn_name}")
                        st.session_state.pop(_name_key, None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"{e}")

    # ── Local PostgreSQL ──────────────────────────────────────────────────────
    elif db_type_key == "pglocal":
        s = st.session_state.pgloc_saved
        pg1, pg2 = st.columns(2)
        with pg1:
            pgl_host = st.text_input("Host", value=s.get("host","localhost"), key="pgl_host")
            pgl_db   = st.text_input("Database", key="pgl_db", value=s.get("database","postgres"))
            pgl_user = st.text_input("Username", key="pgl_user", value=s.get("user","postgres"))
        with pg2:
            pgl_port = st.number_input("Port", value=s.get("port",5432),
                min_value=1, max_value=65535, key="pgl_port")
            pgl_pass = st.text_input("Password", type="password",
                key="pgl_pass", value=s.get("password",""))
            pgl_ssl  = st.selectbox("SSL mode", ["disable","prefer","require"],
                index=["disable","prefer","require"].index(s.get("sslmode","disable")),
                key="pgl_ssl")
        pgl_maxrows = st.slider("Max rows", 10, 500, s.get("max_rows",50), key="pgl_maxrows")
        if st.button("🔌 Connect to Local PostgreSQL", key="conn_pgl",
                     use_container_width=True):
            if not conn_name.strip():
                st.error("Enter a connection name.")
            elif conn_name in connections:
                st.error(f"A connection named '{conn_name}' already exists.")
            else:
                st.session_state.pgloc_saved = {
                    "host": pgl_host, "port": int(pgl_port), "database": pgl_db,
                    "user": pgl_user, "password": pgl_pass, "sslmode": pgl_ssl,
                    "max_rows": pgl_maxrows,
                }
                with st.spinner("Connecting…"):
                    try:
                        _add_connection(conn_name, PostgresClient(
                            host=pgl_host, port=int(pgl_port), database=pgl_db,
                            user=pgl_user, password=pgl_pass, sslmode=pgl_ssl,
                            max_rows=pgl_maxrows, label="Local PostgreSQL"),
                            "pglocal")
                        st.success(f"Connected: {conn_name}")
                        st.session_state.pop(_name_key, None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"{e}")

    # ── MySQL ─────────────────────────────────────────────────────────────────
    elif db_type_key == "mysql":
        s = st.session_state.mysql_saved
        my1, my2 = st.columns(2)
        with my1:
            my_host = st.text_input("Host",
                placeholder="localhost or mydb.xxxx.rds.amazonaws.com",
                key="my_host", value=s.get("host","localhost"))
            my_db   = st.text_input("Database", key="my_db", value=s.get("database",""))
            my_user = st.text_input("Username", key="my_user", value=s.get("user","root"))
        with my2:
            my_port = st.number_input("Port", value=s.get("port",3306),
                min_value=1, max_value=65535, key="my_port")
            my_pass = st.text_input("Password", type="password",
                key="my_pass", value=s.get("password",""))
            my_ssl  = st.checkbox("Disable SSL", value=s.get("ssl_disabled", False),
                key="my_ssl", help="Check to disable SSL (local/dev only)")
        my_maxrows = st.slider("Max rows", 10, 500, s.get("max_rows",50), key="my_maxrows")
        my_label   = st.text_input("Display label", value=s.get("label","MySQL"),
            key="my_label", help="E.g. 'Production MySQL' or 'Aurora Analytics'")
        if st.button("🔌 Connect to MySQL", key="conn_my", use_container_width=True):
            if not conn_name.strip():
                st.error("Enter a connection name.")
            elif conn_name in connections:
                st.error(f"A connection named '{conn_name}' already exists.")
            else:
                st.session_state.mysql_saved = {
                    "host": my_host, "port": int(my_port), "database": my_db,
                    "user": my_user, "password": my_pass, "ssl_disabled": my_ssl,
                    "max_rows": my_maxrows, "label": my_label,
                }
                with st.spinner("Connecting…"):
                    try:
                        _add_connection(conn_name, MySQLClient(
                            host=my_host, port=int(my_port), database=my_db,
                            user=my_user, password=my_pass, ssl_disabled=my_ssl,
                            max_rows=my_maxrows, label=my_label),
                            "mysql")
                        st.success(f"Connected: {conn_name}")
                        st.session_state.pop(_name_key, None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"{e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB: VECTOR STORE
# ══════════════════════════════════════════════════════════════════════════════
with tab_vs:
    st.markdown("### 🧠 Schema Vector Store (pgvector)")
    st.markdown(
        "Store your database schema as embeddings in pgvector. "
        "The analyst will then retrieve only the **relevant tables** for each "
        "question instead of sending the full schema — reducing tokens and "
        "improving SQL accuracy for large databases."
    )

    vs_connected = st.session_state.vs_connected
    vs = st.session_state.vs

    if vs_connected and vs:
        count = st.session_state.vs_indexed_count
        st.markdown(
            f'<div class="vs-info">🧠 <strong>pgvector active</strong> — '
            f'{count} table(s) indexed. Schema retrieval is semantic.</div>',
            unsafe_allow_html=True,
        )

    with st.expander("📋 **How to install pgvector** *(expand if you see an extension error)*",
                     expanded=False):
        st.markdown("""
**macOS — EnterpriseDB PostgreSQL**
```bash
cd /tmp && git clone --branch v0.8.3 https://github.com/pgvector/pgvector.git
cd /tmp/pgvector
sudo PG_CONFIG=/Library/PostgreSQL/18/bin/pg_config make install
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**macOS — Homebrew PostgreSQL**
```bash
brew install pgvector
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**AWS RDS / Aurora PostgreSQL**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**Linux (Ubuntu/Debian)**
```bash
sudo apt install postgresql-16-pgvector
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Docker**
```bash
docker run -e POSTGRES_PASSWORD=pass -p 5432:5432 pgvector/pgvector:pg17
```
        """)

    with st.expander("🐘 pgvector PostgreSQL connection", expanded=not vs_connected):
        s = st.session_state.vs_saved
        st.caption("Can be the same Postgres as your data DB, or a dedicated one.")
        v1, v2 = st.columns(2)
        with v1:
            vs_host = st.text_input("Host", value=s.get("host","localhost"), key="vs_host")
            vs_db   = st.text_input("Database", value=s.get("database","postgres"), key="vs_db")
            vs_user = st.text_input("Username", value=s.get("user","postgres"), key="vs_user")
        with v2:
            vs_port = st.number_input("Port", value=s.get("port",5432),
                min_value=1, max_value=65535, key="vs_port")
            vs_pass = st.text_input("Password", type="password",
                value=s.get("password",""), key="vs_pass")
            _ssl_opts = ["disable", "prefer", "require"]
            vs_ssl = st.selectbox("SSL mode", _ssl_opts,
                index=_ssl_opts.index(s.get("sslmode", "disable")),
                key="vs_ssl")

        EMBED_MODELS = {
            "amazon.titan-embed-text-v2:0": ("Amazon", "Titan Text Embeddings v2", 1024,
                                             "Best balance. Recommended."),
            "amazon.titan-embed-text-v1":   ("Amazon", "Titan Text Embeddings v1", 1536,
                                             "Older Titan, higher dim."),
            "amazon.titan-embed-image-v1":  ("Amazon", "Titan Multimodal Embeddings", 1024,
                                             "Text + image inputs."),
            "cohere.embed-english-v3":      ("Cohere", "Embed English v3", 1024,
                                             "High quality English."),
            "cohere.embed-multilingual-v3": ("Cohere", "Embed Multilingual v3", 1024,
                                             "100+ languages."),
            "amazon.nova-embed-text-v1:0":  ("Amazon", "Nova Embed Text v1", 1024,
                                             "Latest Amazon Nova model."),
        }
        embed_options = list(EMBED_MODELS.keys())
        default_embed = s.get("embed_model", "amazon.titan-embed-text-v2:0")
        if default_embed not in embed_options:
            default_embed = embed_options[0]

        vs_embed = st.selectbox(
            "Embedding model (via AWS Bedrock)",
            embed_options,
            index=embed_options.index(default_embed),
            format_func=lambda mid: f"{EMBED_MODELS[mid][0]} — {EMBED_MODELS[mid][1]} ({EMBED_MODELS[mid][2]}d)",
            key="vs_embed_model",
        )
        if vs_embed in EMBED_MODELS:
            info = EMBED_MODELS[vs_embed]
            st.caption(f"📐 **{info[2]} dimensions** · {info[3]}")

        ca, cb = st.columns([3,1])
        with ca:
            if st.button("🔌 Connect pgvector", key="conn_vs", use_container_width=True):
                st.session_state.vs_saved = {
                    "host": vs_host, "port": int(vs_port), "database": vs_db,
                    "user": vs_user, "password": vs_pass, "sslmode": vs_ssl,
                    "embed_model": vs_embed,
                }
                with st.spinner("Connecting to pgvector…"):
                    try:
                        new_vs = SchemaVectorStore(
                            host=vs_host, port=int(vs_port), database=vs_db,
                            user=vs_user, password=vs_pass, sslmode=vs_ssl,
                            aws_key=st.session_state.bk_key,
                            aws_secret=st.session_state.bk_secret,
                            aws_region=st.session_state.bk_region,
                            embed_model=vs_embed,
                        )
                        new_vs.connect()
                        st.session_state.vs = new_vs
                        st.session_state.vs_connected = True
                        # Wire into all existing analyst sessions
                        for cdata in st.session_state.connections.values():
                            if cdata.get("session"):
                                cdata["session"].set_vector_store(new_vs)
                        st.success("pgvector connected!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"pgvector connection failed: {e}")
        with cb:
            if vs_connected and st.button("Disconnect", key="disc_vs", use_container_width=True):
                if vs:
                    try:
                        vs.disconnect()
                    except Exception:  # pylint: disable=broad-exception-caught
                        pass
                st.session_state.vs = None
                st.session_state.vs_connected = False
                st.session_state.vs_indexed_count = 0
                for cdata in st.session_state.connections.values():
                    if cdata.get("session"):
                        cdata["session"].set_vector_store(None)
                st.rerun()

    if vs_connected and vs:
        st.divider()
        st.markdown("#### Index your database schema")

        active_c = _active_conn()
        if not active_c:
            st.warning("Connect to a database first (Connections tab), then index its schema here.")
        else:
            # Let user pick which connection to index if multiple exist
            if len(connections) > 1:
                idx_conn_name = st.selectbox(
                    "Index schema for connection",
                    list(connections.keys()),
                    index=list(connections.keys()).index(st.session_state.active_conn)
                        if st.session_state.active_conn in connections else 0,
                    key="vs_idx_conn",
                )
            else:
                idx_conn_name = list(connections.keys())[0]

            idx_conn = connections[idx_conn_name]
            db_label = idx_conn["client"].label
            current_count = vs.count(db_label)

            col1, col2 = st.columns([2,1])
            with col1:
                st.info(f"**{current_count}** table(s) indexed for **{db_label}** ({idx_conn_name}).")
            with col2:
                if st.button("🗑️ Clear index", key="clear_vs", use_container_width=True):
                    vs.clear(db_label)
                    st.session_state.vs_indexed_count = 0
                    st.success("Index cleared.")
                    st.rerun()

            if st.button("⚡ Index schema now", key="index_vs",
                         use_container_width=True, type="primary"):
                schema = idx_conn.get("schema", "")
                if not schema:
                    st.error("No schema loaded. Refresh schema from the sidebar first.")
                else:
                    progress = st.progress(0, text="Embedding tables…")
                    try:
                        count = vs.index_schema(db_label, schema)
                        progress.progress(1.0, text=f"Indexed {count} tables ✓")
                        st.session_state.vs_indexed_count = count
                        st.success(f"✅ {count} table(s) embedded and stored in pgvector.")
                        st.rerun()
                    except Exception as e:
                        progress.empty()
                        st.error(f"Indexing failed: {e}")

        st.divider()
        st.markdown("#### Indexed tables")
        if active_c:
            db_label = active_c["client"].label
            indexed = vs.list_indexed_tables(db_label)
            if indexed:
                df_idx = pd.DataFrame(indexed)
                df_idx.columns = ["Table", "Indexed at", "Schema size (chars)"]
                st.dataframe(df_idx, use_container_width=True, height=300)
            else:
                st.info("No tables indexed yet.")

        st.divider()
        st.markdown("#### Test semantic search")
        test_q = st.text_input("Test question", placeholder="e.g. show me open disputes",
                               key="vs_test_q")
        if st.button("🔍 Search", key="vs_search") and test_q and active_c:
            db_label = active_c["client"].label
            with st.spinner("Searching…"):
                try:
                    result = vs.search(db_label, test_q, top_k=5)
                    if result:
                        st.code(result, language="sql")
                    else:
                        st.info("No results — index the schema first.")
                except Exception as e:
                    st.error(f"{e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB: CHAT
# ══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    conn_data = _active_conn()

    if not conn_data:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#5f6b7a;">
            <div style="font-size:4rem;margin-bottom:16px;">🔌</div>
            <h2 style="color:#1a1a2e;font-weight:600;">No active connection</h2>
            <p>Go to <strong>Connections</strong> to connect a database, then come back to chat.</p>
        </div>
        """, unsafe_allow_html=True)
        icon_cols = st.columns(5)
        for col, (icon, name) in zip(icon_cols, [
            ("❄️","Snowflake"),("🏭","Microsoft Fabric"),
            ("🐘","AWS RDS PG"),("💻","Local PG"),("🐬","MySQL"),
        ]):
            col.markdown(f"""<div class="metric-card">
                <div style="font-size:1.8rem;">{icon}</div>
                <div style="color:#1a1a2e;font-weight:600;margin:6px 0;font-size:0.9rem;">{name}</div>
            </div>""", unsafe_allow_html=True)
    else:
        # Connection switcher at top of chat (when multiple connections exist)
        if len(connections) > 1:
            chat_names = list(connections.keys())
            cur_idx = chat_names.index(st.session_state.active_conn) \
                if st.session_state.active_conn in chat_names else 0
            col_label, col_pick = st.columns([1, 3])
            with col_label:
                st.markdown("**Query database:**")
            with col_pick:
                new_active = st.selectbox(
                    "Active DB",
                    chat_names,
                    index=cur_idx,
                    key="chat_conn_select",
                    label_visibility="collapsed",
                )
                if new_active != st.session_state.active_conn:
                    st.session_state.active_conn = new_active
                    st.rerun()
            conn_data = _active_conn()

        db = conn_data["client"]

        # Status pills
        icon_map2 = {"snowflake":"❄️","fabric":"🏭","pgaws":"🐘","pglocal":"💻","mysql":"🐬"}
        db_icon = icon_map2.get(conn_data["type"], "🗄️")
        pills = [
            f'<span style="background:#e6f4ea;border:1px solid #a8d5b5;border-radius:20px;'
            f'padding:4px 12px;font-size:0.8rem;color:#1e7e34;font-weight:600;">'
            f'{db_icon} {st.session_state.active_conn} · {db.label}</span>'
        ]
        if st.session_state.vs_connected:
            pills.append(
                '<span style="background:#ede7f6;border:1px solid #c5b3e6;border-radius:20px;'
                'padding:4px 12px;font-size:0.8rem;color:#5e35b1;font-weight:600;">'
                '🧠 pgvector</span>')
        if st.session_state.bk_model:
            pills.append(
                f'<span style="background:#e8f0fe;border:1px solid #c5d3f0;border-radius:20px;'
                f'padding:4px 12px;font-size:0.8rem;color:#1a73e8;font-weight:600;">'
                f'🤖 {st.session_state.bk_model.split(".")[-1][:30]}</span>')
        st.markdown("&nbsp;".join(pills) + "<br>", unsafe_allow_html=True)

        # Table preview
        if st.session_state.get("preview_table"):
            table = st.session_state.preview_table
            with st.expander(f"👁️ Preview: {table}", expanded=True):
                try:
                    st.dataframe(db.get_sample(table, n=10), use_container_width=True)
                except Exception as e:
                    st.error(f"Preview failed: {e}")
            if st.button("✕ Close preview"):
                del st.session_state["preview_table"]
                st.rerun()

        with st.expander("🗄️ Database Schema", expanded=False):
            st.code(conn_data.get("schema","Schema not loaded."), language="sql")

        # Chat history for this connection
        messages = conn_data.setdefault("messages", [])
        if not messages:
            st.markdown("""
            <div style="text-align:center;padding:40px;color:#5f6b7a;">
                <div style="font-size:3rem;">💬</div>
                <p style="margin:8px 0;color:#1a1a2e;font-weight:600;">Ask your first data question</p>
                <p style="font-size:0.85rem;">
                    Try: <em>"What are the top 10 customers by sales?"</em><br>
                    or: <em>"How many open disputes are there?"</em>
                </p>
            </div>""", unsafe_allow_html=True)

        for msg in messages:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="chat-label-user">You</div>'
                    f'<div class="chat-user">{msg["content"]}</div>',
                    unsafe_allow_html=True)
            else:
                st.markdown('<div class="chat-label-ai">🤖 AI Analyst</div>',
                            unsafe_allow_html=True)
                src = msg.get("schema_source", "full")
                if src == "vector":
                    st.markdown(
                        '<span style="font-size:0.7rem;background:#ede7f6;color:#5e35b1;'
                        'border-radius:10px;padding:2px 8px;">🧠 vector retrieval</span>',
                        unsafe_allow_html=True)
                if msg.get("error"):
                    st.error(msg["error"], icon="🚫")
                if msg.get("sql"):
                    with st.expander("🔍 Generated SQL", expanded=False):
                        st.code(msg["sql"], language="sql")
                df_msg = msg.get("df")
                if df_msg is not None and not df_msg.empty:
                    t1, t2 = st.tabs(["📋 Table", "📊 Chart"])
                    with t1:
                        st.dataframe(df_msg, use_container_width=True, height=260)
                        st.caption(f"{len(df_msg)} row(s)" +
                                   (" · truncated" if df_msg.attrs.get("truncated") else ""))
                    with t2:
                        _auto_chart(df_msg)
                if msg.get("content"):
                    st.markdown(
                        f'<div class="chat-assistant">{msg["content"]}</div>',
                        unsafe_allow_html=True)
                st.markdown("<hr style='border-color:#e0e4ec;margin:14px 0;'>",
                            unsafe_allow_html=True)

        # Input
        prefill = st.session_state.pop("prefill", "")
        with st.form("chat_form", clear_on_submit=True):
            cols = st.columns([8,1])
            with cols[0]:
                user_input = st.text_input(
                    "question", value=prefill,
                    placeholder="e.g. How many open disputes are there?",
                    label_visibility="collapsed")
            with cols[1]:
                submitted = st.form_submit_button("Send ➤", use_container_width=True)

        if submitted and user_input.strip():
            question = user_input.strip()
            messages.append({"role":"user","content":question})
            with st.spinner("🤖 Thinking…"):
                try:
                    result = conn_data["session"].ask(question)
                    df_res = result.get("data")
                    conn_data["total_queries"] = conn_data.get("total_queries", 0) + 1
                    if df_res is not None:
                        conn_data["total_rows"] = conn_data.get("total_rows", 0) + len(df_res)
                    messages.append({
                        "role":          "assistant",
                        "content":       result["answer"],
                        "sql":           result.get("sql",""),
                        "df":            df_res,
                        "error":         result.get("error"),
                        "schema_source": result.get("schema_source","full"),
                    })
                except Exception as e:
                    messages.append({
                        "role":"assistant","content":"","sql":"","df":None,
                        "error": f"Unexpected error: {e}\n\n{traceback.format_exc()}",
                        "schema_source": "full",
                    })
            st.rerun()
