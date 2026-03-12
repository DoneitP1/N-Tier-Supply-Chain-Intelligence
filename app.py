import streamlit as st
import requests
from streamlit_agraph import agraph, Node, Edge, Config

# Configuration
API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="N-Tier Supply Chain Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Sidebar ---
st.sidebar.title("N-Tier Platform")
st.sidebar.info("Supply Chain Intelligence & Risk Propagation Engine")
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Core Features:**\n"
    "- 📄 Automated Contract Parsing (LLM)\n"
    "- 🧠 Knowledge Graph Ingestion\n"
    "- ⚠️ Multi-Tier Risk Simulation\n"
)

# --- Main Header ---
st.title("🛡️ N-Tier Supply Chain Intelligence")
st.subheader("Bursa Automotive Pilot - MVP Dashboard")

# --- Tabs ---
tab_dashboard, tab_ingestion, tab_risk = st.tabs([
    "📊 Dashboard", 
    "📄 Contract Ingestion", 
    "⚠️ Risk Simulation"
])

# ---------------------------------------------------------
# 1. Dashboard Tab
# ---------------------------------------------------------
with tab_dashboard:
    st.header("Network Visualization")
    st.markdown("Interactive Knowledge Graph map of the N-Tier Supply Chain.")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/graph-data")
        if response.status_code == 200:
            graph_data = response.json()
            raw_nodes = graph_data.get("nodes", [])
            raw_edges = graph_data.get("edges", [])
            
            if not raw_nodes:
                st.info("Knowledge Graph is currently empty. Please ingest contracts, news, or ERP data first.")
            else:
                nodes = []
                edges = []
                
                # Visual Coding Constraints
                color_map = {
                    "Factory": "#2196F3",     # Blue
                    "Part": "#9E9E9E",        # Gray
                    "Supplier": "#4CAF50",    # Green
                    "RiskEvent": "#F44336"    # Red
                }
                
                for n in raw_nodes:
                    node_id = str(n.get("id"))
                    label = n.get("label", "Unknown")
                    name = n.get("name", "Unknown")
                    
                    color = color_map.get(label, "#333333")  # Fallback to dark gray
                    
                    nodes.append(Node(
                        id=node_id,
                        label=name,
                        size=25,
                        color=color,
                        title=f"{label}: {name}"
                    ))
                    
                for e in raw_edges:
                    edges.append(Edge(
                        source=str(e.get("source")),
                        target=str(e.get("target")),
                        label=e.get("type", "RELATED")
                    ))
                    
                config = Config(
                    width="1000px",
                    height="600px",
                    directed=True,
                    physics=True,
                    hierarchical=False,
                )
                
                agraph(nodes=nodes, edges=edges, config=config)
        else:
            st.error(f"Failed to load graph data. Status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("Error connecting to the backend API. Please ensure the FastAPI server is running: `uvicorn main:app --reload`")

# ---------------------------------------------------------
# 2. Contract Ingestion Tab
# ---------------------------------------------------------
with tab_ingestion:
    st.header("Ingest Supplier Contract")
    st.markdown("Upload a supplier contract (PDF) to parse, extract entities, and ingest into the Knowledge Graph.")
    
    uploaded_file = st.file_uploader("Upload PDF Contract", type=["pdf"])
    
    if st.button("Analyze Contract", type="primary"):
        if uploaded_file is not None:
            with st.spinner("Processing document via Language Model..."):
                try:
                    # Prepare the file for upload
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    response = requests.post(f"{API_BASE_URL}/upload-pdf/", files=files)
                    
                    if response.status_code == 201 or response.status_code == 200:
                        st.success("Contract successfully analyzed and ingested into the Knowledge Graph!")
                        st.json(response.json())
                    else:
                        st.error(f"Failed to process contract. API returned status code: {response.status_code}")
                        st.json(response.json() if response.content else {"error": "Unknown error"})
                except requests.exceptions.ConnectionError:
                    st.error("Error connecting to the backend API. Please ensure the FastAPI server is running: `uvicorn main:app --reload`")
        else:
            st.warning("Please upload a PDF file first.")

# ---------------------------------------------------------
# 3. Risk Simulation Tab
# ---------------------------------------------------------
with tab_risk:
    st.header("Simulate Risk Propagation")
    st.markdown("Evaluate how a disruption at a lower-tier supplier cascades through the supply chain.")
    
    col1, col2 = st.columns(2)
    with col1:
        supplier_name = st.text_input("Impacted Supplier Name", placeholder="e.g. Katman-1 Bursa Auto Parts Ltd.")
    with col2:
        crisis_duration = st.number_input("Crisis Duration (Days)", min_value=1, value=30, step=1)
        
    if st.button("Run Simulation", type="primary"):
        if supplier_name.strip() == "":
            st.warning("Please enter a supplier name.")
        else:
            with st.spinner(f"Simulating risk propagation for '{supplier_name}'..."):
                try:
                    payload = {
                        "impacted_supplier_name": supplier_name,
                        "crisis_duration_days": crisis_duration
                    }
                    response = requests.post(f"{API_BASE_URL}/simulate-risk/", json=payload)
                    
                    if response.status_code == 200:
                        results = response.json()
                        if not results:
                            st.info("No risk paths found for this supplier.")
                        else:
                            st.success(f"Simulation complete. Found {len(results)} affected path(s).")
                            
                            for idx, result in enumerate(results):
                                st.markdown(f"### Path {idx + 1}")
                                
                                # Show paths visually
                                path_str = " ➔ ".join(result.get("impacted_paths", []))
                                st.markdown(f"**Impact Path:** `{path_str}`")
                                
                                # Metrics
                                m_col1, m_col2 = st.columns(2)
                                
                                risk_score = result.get("risk_score", "Unknown")
                                days_stoppage = result.get("days_to_line_stoppage", "Unknown")
                                
                                with m_col1:
                                    st.metric("Days to Line Stoppage", f"{days_stoppage} Days")
                                with m_col2:
                                    # Provide visual cues for risk score via st.metric delta parameter
                                    if risk_score == "High":
                                        st.metric("Risk Score", risk_score, delta="Critical Risk", delta_color="inverse")
                                    elif risk_score == "Medium":
                                        st.metric("Risk Score", risk_score, delta="Moderate Risk", delta_color="off")
                                    else:
                                        st.metric("Risk Score", risk_score, delta="Low Risk", delta_color="normal")
                                    
                                # Recommendations
                                recs = result.get("recommendations", "")
                                if risk_score == "High":
                                    st.error(f"**Recommendations:** {recs}")
                                elif risk_score == "Medium":
                                    st.warning(f"**Recommendations:** {recs}")
                                else:
                                    st.success(f"**Recommendations:** {recs}")
                                    
                                st.markdown("---")
                                
                    elif response.status_code == 404:
                            st.error(f"Supplier '{supplier_name}' not found in the Knowledge Graph.")
                    else:
                        st.error(f"API Error ({response.status_code}): {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Error connecting to the backend API. Please ensure the FastAPI server is running: `uvicorn main:app --reload`")
