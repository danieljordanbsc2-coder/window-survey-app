import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
import json

# ==============================================================================
# 1. ENTERPRISE SYSTEM ARCHITECTURE
# ==============================================================================

class WindowCRMSystem:
    """Core System for managing relational project data and UI states."""
    
    @staticmethod
    def boot_sequence():
        """Initializes the mock database and application state."""
        if 'crm_db' not in st.session_state:
            st.session_state.crm_db = {
                "jobs": [],
                "settings": {"vat_rate": 0.135, "currency": "€"},
                "users": {"rep_01": "Sales", "fit_99": "Fitter"}
            }
        if 'auth' not in st.session_state:
            st.session_state.auth = {"user": None, "role": None}
        if 'current_view' not in st.session_state:
            st.session_state.current_view = "Dashboard"

    @staticmethod
    def set_theme():
        """Injects Corporate Blue / Construction Hub CSS."""
        st.markdown("""
            <style>
            .main { background-color: #f8f9fa; }
            .stTabs [data-baseweb="tab-list"] { gap: 10px; }
            .stTabs [data-baseweb="tab"] {
                background-color: #ffffff; border: 1px solid #dee2e6;
                padding: 10px 20px; border-radius: 5px 5px 0 0;
            }
            .stTabs [aria-selected="true"] { background-color: #004a99 !important; color: white !important; }
            .job-card { 
                background: white; padding: 20px; border-radius: 10px; 
                border-left: 8px solid #004a99; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .fitter-brief { background-color: #fff9db; border-left: 8px solid #fcc419; padding: 15px; }
            .metric-container { background: white; padding: 15px; border-radius: 8px; border: 1px solid #e9ecef; }
            </style>
        """, unsafe_allow_html=True)

# ==============================================================================
# 2. PRICING & LOGIC KERNEL
# ==============================================================================

class PricingEngine:
    """
    Implements 2026 Pricing Ladder & Multipliers.
    [cite: 2026-02-10, 2026-02-11]
    """
    TIERS = [(0.6, 698), (0.8, 652), (1.0, 501), (1.2, 440), (1.5, 400),
             (2.0, 380), (2.5, 344), (3.0, 330), (3.5, 316), (4.0, 304),
             (4.5, 291), (999.0, 277)]

    FITTING_FEES = {
        "Aluclad Standard": 325, "PVC Sliding Sash": 438,
        "Hardwood Sliding Sash": 480, "Aluclad Sliding Sash": 480, "Fireproof": 245
    }

    MATERIAL_FACTORS = {
        "PVC Standard": 0.55, "Aluclad Standard": 1.0, "PVC Sliding Sash": 1.2,
        "Hardwood Sliding Sash": 2.09, "Aluclad Sliding Sash": 2.5, "Fireproof": 0.55
    }

    @classmethod
    def calculate(cls, w, h, sashes, mat, job_type, vat_enabled):
        area = (w * h) / 1_000_000
        # Find Base Rate
        rate = next(r for a, r in cls.TIERS if area < a)
        
        # Base List Price
        base = (rate * area) + (sashes * 80)
        
        # Apply Multiplier & Minimum Charge (€300 Floor)
        cost = max(base * cls.MATERIAL_FACTORS.get(mat, 1.0), 300.0)
        
        # Add Installation Surcharges
        install = cls.FITTING_FEES.get(mat, 0) if job_type == "Replacement" else 0
        
        final = cost + install
        return round(final * (1.135 if vat_enabled else 1.0), 2)

# ==============================================================================
# 3. CAD SCHEMATIC RENDERER
# ==============================================================================

class CADEngine:
    """Programmatic technical drawing for factory specifications."""
    
    @staticmethod
    def generate_elevation(w, h, config, op_t, op_b):
        ratio = w / h
        draw_w = 260 if ratio > 1 else 260 * ratio
        draw_h = 260 if ratio < 1 else 260 / ratio
        x, y = (320 - draw_w)/2, (300 - draw_h)/2

        def arrow(ax, ay, aw, ah, mode):
            if "Left" in mode: return f'<polyline points="{ax+8},{ay+ah/2} {ax+aw-8},{ay+8} {ax+aw-8},{ay+ah-8} {ax+8},{ay+ah/2}" fill="none" stroke="red" stroke-width="3"/>'
            if "Right" in mode: return f'<polyline points="{ax+aw-8},{ay+ah/2} {ax+8},{ay+8} {ax+8},{ay+ah-8} {ax+aw-8},{ay+ah/2}" fill="none" stroke="red" stroke-width="3"/>'
            if "Top" in mode: return f'<polyline points="{ax+aw/2},{ay+8} {ax+8},{ay+ah-8} {ax+aw-8},{ay+ah-8} {ax+aw/2},{ay+8}" fill="none" stroke="red" stroke-width="3"/>'
            return ""

        svg = f'<rect x="{x}" y="{y}" width="{draw_w}" height="{draw_h}" fill="none" stroke="black" stroke-width="6"/>'
        
        if config == "Transom Split":
            th = draw_h * 0.3
            svg += f'<rect x="{x}" y="{y}" width="{draw_w}" height="{th}" fill="#f0f7ff" stroke="black" stroke-width="3"/>'
            svg += f'<rect x="{x}" y="{y+th}" width="{draw_w}" height="{draw_h-th}" fill="#f0f7ff" stroke="black" stroke-width="3"/>'
            svg += arrow(x, y, draw_w, th, op_t) + arrow(x, y+th, draw_w, draw_h-th, op_b)
        elif config == "Sliding Sash":
            svg += f'<rect x="{x+6}" y="{y+6}" width="{draw_w-12}" height="{draw_h/2}" fill="#f0f7ff" stroke="#666" stroke-width="2"/>'
            svg += f'<rect x="{x+2}" y="{y+draw_h/2}" width="{draw_w-4}" height="{draw_h/2-2}" fill="#f0f7ff" stroke="black" stroke-width="4"/>'
            svg += f'<path d="M{x-15} {y+draw_h*0.8} L{x-15} {y+draw_h*0.4}" stroke="blue" stroke-width="2" marker-end="url(#arrowhead)"/>'
        else:
            svg += f'<rect x="{x}" y="{y}" width="{draw_w}" height="{draw_h}" fill="#f0f7ff" stroke="black" stroke-width="6"/>'
            svg += arrow(x, y, draw_w, draw_h, op_t)

        return f'<div style="background:white; border-radius:12px; padding:15px; text-align:center;"><svg width="340" height="320">{svg}</svg></div>'

# ==============================================================================
# 4. SALES REP MODULE
# ==============================================================================

def sales_rep_view():
    st.title("🚀 Sales Opportunity Manager")
    
    with st.sidebar:
        st.subheader("New Project Intake")
        project_name = st.text_input("Project Name/Address")
        job_env = st.radio("Contract Type", ["Replacement", "New Build", "Supply Only"])
        vat_toggle = st.toggle("Include VAT in Pricing", value=True)
        if st.button("Initialize Folder"):
            st.session_state.crm_db['jobs'].append({
                "name": project_name, "status": "Pending Survey", 
                "env": job_env, "vat": vat_toggle, "units": [], "timestamp": str(datetime.now())
            })
            st.rerun()

    active_jobs = [j['name'] for j in st.session_state.crm_db['jobs']]
    if not active_jobs:
        st.info("No active projects. Use the sidebar to create a site folder.")
        return

    selected_job = st.selectbox("Active Project Folder", active_jobs)
    job_idx = next(i for i, j in enumerate(st.session_state.crm_db['jobs']) if j['name'] == selected_job)
    job = st.session_state.crm_db['jobs'][job_idx]

    t_add, t_quote = st.tabs(["🏗️ Survey Entry", "📜 Proposal & Quotes"])

    with t_add:
        c1, c2 = st.columns([2, 1])
        with c1:
            with st.container(border=True):
                st.subheader("1. Elevation Parameters")
                room = st.text_input("Room Identifier")
                mat = st.selectbox("Product System", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
                lay = st.selectbox("Configuration", ["Single Elevation", "Transom Split", "Sliding Sash"])
                
                gc1, gc2, gc3 = st.columns(3)
                w = gc1.number_input("Width (mm)", 100, 5000, 1200)
                h = gc2.number_input("Height (mm)", 100, 5000, 1000)
                col = gc3.selectbox("Finish", ["White", "Anthracite", "Black", "Oak"])

            with st.container(border=True):
                st.subheader("2. Opening Style")
                ot, ob = "Fixed", "Fixed"
                if lay == "Transom Split":
                    oc1, oc2 = st.columns(2)
                    ot = oc1.selectbox("Top Fanlight", ["Fixed", "Top Hung"])
                    ob = oc2.selectbox("Bottom Pane", ["Fixed", "Side Left", "Side Right"])
                else:
                    ot = st.selectbox("Operation Mode", ["Fixed", "Side Left", "Side Right", "Top Hung"])
                
                sas_qty = st.slider("Total Opening Sashes", 0, 6, 1 if ot != "Fixed" else 0)

            with st.container(border=True):
                st.subheader("3. Technical Specs")
                drip = st.selectbox("Head Drip Detail", ["Standard Drip", "28mm Drip", "No Drip"])
                cill = st.selectbox("Cill Required", ["None", "30mm Stub", "85mm", "150mm"])
                glass = st.selectbox("Glazing Spec", ["Double", "Triple", "Toughened", "Obscure"])

        with c2:
            st.subheader("Visual Preview")
            st.markdown(CADEngine.generate_elevation(w, h, lay, ot, ob), unsafe_allow_html=True)
            
            if st.button("✅ ADD UNIT TO CONTRACT", use_container_width=True, type="primary"):
                price = PricingEngine.calculate(w, h, sas_qty, mat, job['env'], job['vat'])
                job['units'].append({
                    "room": room, "size": f"{w}x{h}", "mat": mat, "price": price,
                    "drip": drip, "cill": cill, "glass": glass, "op": ot, "sas": sas_qty
                })
                st.toast("Unit Added Successfully")
                st.rerun()

    with t_quote:
        st.subheader("Financial Breakdown")
        if job['units']:
            df = pd.DataFrame(job['units'])
            st.table(df[['room', 'size', 'mat', 'price']])
            total = df['price'].sum()
            st.metric("Total Order Value", f"€{total:,.2f}")
            if st.button("📥 Generate PDF Proposal (Placeholder)"):
                st.success("PDF Compiled Successfully")

# ==============================================================================
# 5. FITTER MODULE
# ==============================================================================

def fitter_view():
    st.title("🔧 Field Technical Validation")
    
    auth_code = st.text_input("Enter Secure Fitter Code", type="password")
    if auth_code != "FIT99":
        st.warning("Unauthorized. Please enter your 5-digit verification code.")
        return

    pending_jobs = [j for j in st.session_state.crm_db['jobs'] if j['units']]
    if not pending_jobs:
        st.info("No projects awaiting technical validation.")
        return

    sel_j = st.selectbox("Assign Job to Validate", [j['name'] for j in pending_jobs])
    job = next(j for j in pending_jobs if j['name'] == sel_j)

    st.success(f"Site Context: {job['env']} Protocol")
    
    for i, u in enumerate(job['units']):
        with st.container(border=True):
            fc1, fc2, fc3 = st.columns([1, 2, 1])
            with fc1:
                st.markdown(f"**Unit {i+1}: {u['room']}**")
                st.caption(f"Sales Measurement: {u['size']}")
            with fc2:
                st.markdown("<div class='fitter-brief'><b>TECHNICAL AUDIT</b></div>", unsafe_allow_html=True)
                new_w = st.number_input(f"Final Width {i}", value=int(u['size'].split('x')[0]), key=f"fw_{i}")
                new_h = st.number_input(f"Final Height {i}", value=int(u['size'].split('x')[1]), key=f"fh_{i}")
            with fc3:
                if st.button(f"Update Unit {i}"):
                    u['size'] = f"{new_w}x{new_h}"
                    st.toast("Measurement Hardened")

# ==============================================================================
# 6. MAIN ORCHESTRATOR
# ==============================================================================

def main():
    WindowCRMSystem.boot_sequence()
    WindowCRMSystem.set_theme()

    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/1087/1087815.png", width=80)
        st.title("Pro-Window CRM")
        role = st.selectbox("System Access", ["Sales Rep", "Fitter Tech"])
        st.divider()
        st.caption("v8.0 Enterprise Build | 2026 Ready")

    if role == "Sales Rep":
        sales_rep_view()
    else:
        fitter_view()

if __name__ == "__main__":
    main()
