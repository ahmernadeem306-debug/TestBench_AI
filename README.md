# ⚡ TestBench AI — Embedded Test Architecture Copilot

A deterministic, multi-agent LangGraph workflow for embedded/hardware
validation, wrapped in an interactive Streamlit control-room dashboard.

No step in the graph relies on an LLM to invent a voltage reading, a
threshold, or a pass/fail verdict — every routing decision and every
simulated measurement is explicit, programmatic control flow. The goal
is a framework where the *shape* of the workflow (multi-agent routing,
RAG-style grounding, remediation loops) is AI-native, but the safety-
critical numbers are never left to a model to hallucinate.

## Architecture

```
                ┌─────────────┐
        ┌──────>│ supervisor  │
        │       └──────┬──────┘
        │              │
        │              v
        │      ┌─────────────────┐
        │      │ analyzer_oracle │
        │      └────────┬────────┘
        │               │
        │        [oracle_routing_gateway]
        │         PASSED  │  FAILED / REMEDIATED
        │           │     └──────────┐
        │           v                v
        │          END        ┌─────────────┐
        └───────────────────── │ rca_healer  │
                                └─────────────┘
```

| File | Responsibility |
|---|---|
| `graph_state.py` | The strict `TestBenchState` TypedDict schema, plus the three node functions: `supervisor_router_node`, `signal_analyzer_oracle_node`, `root_cause_remediator_node`. |
| `graph_build.py` | Assembles the nodes into a compiled, cyclic `StateGraph` with a conditional routing gateway. |
| `app.py` | Streamlit dashboard: requirement input, live telemetry stream, termination banner, voltage chart, generated PyVISA script viewer. |

### Node summary

- **`supervisor_router_node`** — validates the incoming requirement is non-empty, logs the routing pass, and emits a placeholder PyVISA script.
- **`signal_analyzer_oracle_node`** — a deterministic lookup table keyed on `traceability_matrix_count`: `count == 0` forces a simulated 5.7V fault (breaches the 5.0V IPC-2221 ceiling), `count == 1` forces a simulated 3.3V compliant reading. Any other count fails closed rather than guessing.
- **`root_cause_remediator_node`** — simulates an automated remediation pass, increments `traceability_matrix_count`, and loops back to `supervisor`.

This means a full run genuinely traverses **fault → remediate → pass**
in one execution, which is what the dashboard's voltage chart plots —
it is reading real values recorded during the graph run, not
hardcoded numbers.

## Setup & Run (VS Code)

1. **Open the project folder**
   Unzip `TestBench_AI.zip` anywhere, then in VS Code: `File > Open Folder…` and select the unzipped `TestBench_AI` folder.

2. **Open a terminal inside VS Code**
   `Terminal > New Terminal` (or `` Ctrl+` ``). It will already be pointed at the project folder.

3. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   ```
   Activate it:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

   VS Code may prompt "Select Interpreter" — choose the one inside `venv`.

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the dashboard**
   ```bash
   streamlit run app.py
   ```
   Streamlit will print a local URL (usually `http://localhost:8501`) and should open it in your browser automatically. If not, open the link manually.

6. **Use it**
   Edit the requirement text if you like, click **🚀 Execute Verification Cycle**, and watch the right-hand panel stream telemetry live. Once it terminates you'll see the success banner, the voltage chart, and the generated PyVISA script below.

7. **Stop the server**
   Back in the terminal, press `Ctrl+C`.

## Testing individual components (no UI)

Each backend file can be sanity-checked directly without touching Streamlit:

```bash
python graph_state.py   # (add your own __main__ block, or use the snippets from earlier iterations)
python -c "from graph_build import testbench_graph; print(testbench_graph.invoke({'test_requirement': 'demo', 'generated_pyvisa_script': '', 'simulated_signal_voltage': 0.0, 'oracle_diagnostic_logs': '', 'traceability_matrix_count': 0, 'execution_status': 'PENDING', 'telemetry_stream': []}))"
```

## Known simplifications (by design, for this stage)

- All readings are simulated — no real GPIB/serial instrument is contacted.
- The oracle's lookup table only defines behavior for `count == 0` and `count == 1`; anything else fails closed with `ERROR_UNDEFINED_ORACLE_BOUNDARY` rather than being handled generically.
- No requirement-to-test traceability report compiler yet — the raw `telemetry_stream` is the only audit trail so far.

## Roadmap ideas

- LLM-backed test-case generation node (replace the placeholder PyVISA script with one tailored to the actual requirement text).
- Traceability report compiler exporting a requirement → test → result matrix (CSV/PDF).
- Real hardware bridge (pyserial/PyVISA) behind a feature flag, for when you're ready to point this at an actual bench.
