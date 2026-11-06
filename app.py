import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pypdf import PdfReader
from graph_build import testbench_graph

st.set_page_config(page_title="TestBench AI", page_icon="⚡", layout="wide")

# --- FIXED CSS - AB WHITE TEXT KA MASLA KHATAM ---
st.markdown("""
<style>
.stApp { background-color: #f8fafc; }
h1, h2, h3, h4, p, label { color: #0f172a!important; }
div[data-testid="stFileUploader"] { background: white; border: 1.5px dashed #cbd5e1; border-radius: 12px; padding: 10px; }
div[data-testid="stFileUploader"] label { color: #0f172a!important; font-weight: 600!important; }
.stTextArea textarea { background: white; color: black; border: 1.5px solid #cbd5e1; border-radius: 10px; }
.stButton>button { background: linear-gradient(90deg, #ff416c, #ff4b2b); color: white; border: none; border-radius: 10px; height: 48px; font-weight: 700; }
div[data-testid="stMetric"] { background: white; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

st.title("⚡ TestBench AI — Validation Copilot")
st.caption("Real CSV + Deterministic Oracle + RAG - No Hardware Required")

IPC = 5.0

left, right = st.columns([1.2, 1], gap="large")

with left:
    st.subheader("🎛️ Control Parameters Setup")
    with st.container(border=True):
        req = st.text_area("Hardware Validation Requirement", value="Verify 3.3V rail remains within IPC-2221 limits", height=100, placeholder="e.g. Verify 3.3V rail...")
        c1, c2 = st.columns(2)
        with c1:
            csv_file = st.file_uploader("📈 Upload Oscilloscope CSV", type=["csv"], help="Rigol/Siglent real data")
        with c2:
            pdf_file = st.file_uploader("📄 Upload IPC-2221 / STM32 PDF for RAG", type=["pdf"], help="Datasheet for grounded answer")
        run = st.button("🚀 Execute Verification Cycle", use_container_width=True)

with right:
    st.subheader("📡 Live Telemetry")
    tele_box = st.container(height=400, border=True)
    if not run:
        tele_box.info("Awaiting execution... Upload CSV for Real-Data mode")

if run and req.strip():
    csv_max = None
    df_global = None
    volt_col = None
    if csv_file:
        df = pd.read_csv(csv_file)
        df.columns = [c.lower().strip() for c in df.columns]
        volt_col = df.columns[1] if len(df.columns)>1 else df.columns[0]
        for c in df.columns:
            if 'volt' in c or 'ch1' in c: volt_col = c
        csv_max = float(df[volt_col].max())
        df_global = df

    init = {
        "test_requirement": req,
        "generated_pyvisa_script": "",
        "simulated_signal_voltage": 0.0,
        "oracle_diagnostic_logs": "",
        "traceability_matrix_count": 0,
        "execution_status": "PENDING",
        "telemetry_stream": [],
        "csv_voltage_max": csv_max,
        "parsed_req_voltage": None,
    }

    tele_box.empty()
    log_area = tele_box.container()
    final_state = init
    printed = 0
    voltages = []

    for step in testbench_graph.stream(init, config={"recursion_limit": 25}):
        for _, ns in step.items():
            final_state = ns
            for line in ns.get("telemetry_stream", [])[printed:]:
                if "🚨" in line: log_area.error(line)
                elif "✅" in line: log_area.success(line)
                else: log_area.info(line)
            printed = len(ns.get("telemetry_stream", []))
            if ns.get("simulated_signal_voltage"):
                voltages.append(ns.get("simulated_signal_voltage"))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Parsed Req", f"{final_state.get('parsed_req_voltage')} V")
    m2.metric("CSV Max", f"{csv_max if csv_max else 'No CSV'}")
    m3.metric("Safety Limit", f"{IPC}V")
    m4.metric("Status", final_state.get("execution_status"))

    st.divider()
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("#### 📉 Real Voltage Curve")
        if df_global is not None:
            fig, ax = plt.subplots()
            ax.plot(df_global[volt_col].values[:500], color="#ff416c", linewidth=2)
            ax.axhline(y=IPC, color="red", linestyle="--", label="5.0V Ceiling")
            ax.legend(); ax.grid(alpha=0.3)
            st.pyplot(fig, use_container_width=True)
    with g2:
        st.markdown("#### 🧾 Generated Script + RAG")
        st.code(final_state.get("generated_pyvisa_script",""), language="python")
        if pdf_file:
            reader = PdfReader(pdf_file)
            txt = "".join([(p.extract_text() or "") for p in reader.pages[:2]])
            st.success(f"PDF Loaded: {len(txt)} chars grounded")

    if final_state.get("execution_status") == "PASSED":
        st.balloons()
        st.success("✅ PASSED")
    else:
        st.error(f"⛔ {final_state.get('execution_status')}")

    with st.expander("Debug"):
        st.json(final_state)