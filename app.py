import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
from datetime import datetime
from PIL import Image, ImageDraw

# ==========================================
# 1. CORE ENTERPRISE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Windows Pro Enterprise | Site Survey Hub",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS Injection for High-Density UI
st.markdown("""
    <style>
    .main { background-color: #f1f3f6; }
    [data-testid="stMetricValue"] { font-size: 24px; color: #1f4e79; }
    .stTable { font-size: 12px; }
    .fitter-brief { background-color: #ffffff; border-left: 5px solid #28a745; padding: 15px; border-radius: 5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .rep-view { background-color: #ffffff; border-left: 5px solid #007bff; padding: 15px; border-radius: 5px; }
    .status-badge { padding: 4px 8px; border-radius: 12px; font-size: 10px; font-weight: bold; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. GLOBAL CONSTANTS & PRICING MATRICES
# ==========================================
PRICING_TIERS = [
    (0.6, 698), (0.8, 652), (1.0, 501), (1.2, 440), (1.5, 400),
    (2.0, 380), (2.5, 344), (3.0, 330), (3.5, 316), (4.0, 304),
    (4.5, 291), (99.0, 277)
]

REPLACEMENT_FEES = {
    "Aluclad Standard": 325,
    "PVC Sliding Sash": 438,
    "Hardwood Sliding Sash": 480,
    "Aluclad Sliding Sash": 480,
    "Fireproof": 245
}

# ==========================================
# 3. CORE LOGIC: THE CALCULATION ENGINE
# ==========================================
class PricingEngine:
    @staticmethod
    def get_base_rate(area):
        for limit, rate in PRICING_TIERS:
            if area < limit:
                return rate
        return 277

    @classmethod
    def calculate_unit(cls, w, h, sashes, mat, job_type, vat_enabled):
        area = (w * h) / 1_000_000
        base_rate = cls.get_base_rate(area)
        
        # Calculate Base (Rate * Area) + Opener Surcharges
        # [cite: 2026-02-10]
        list_price = (base_rate * area) + (sashes * 80)
        net_price = 0
        fitting_fee = REPLACEMENT_FEES.get(mat, 0) if job_type == "Replacement" else 0
        
        # Material Multipliers [cite: 2026-02-11]
        if mat == "PVC Standard":
            net_price = list_price * 0.55
        elif mat == "Aluclad Standard":
            net_price = list_price
        elif mat == "PVC Sliding Sash":
            net_price = (list_price * 0.60) * 2
        elif mat == "Hardwood Sliding Sash":
            net_price = (list_price * 0.95) * 2.2
        elif mat == "Aluclad Sliding Sash":
            net_price = list_price * 2.5
        elif mat == "Fireproof":
            net_price = list_price * 0.55
            
        # Apply €300 floor [cite: 2026-02-11]
        final_ex_vat = max(net_price, 300.0) + fitting_fee
        return round(final_ex_vat * (1.135 if vat_enabled else 1.0), 2)

# ==========================================
# 4. VISUAL ENGINE: CAD-STYLE SVG DRAWING
# ==========================================
class ElevationDrawer:
    @staticmethod
    def generate_svg(w, h, layout, op_t, op_b, op_s):
        ratio = w / h
        view_w = 280 if ratio > 1 else 280 * ratio
        view_h = 280 if ratio < 1 else 280 / ratio
        off_x, off_y = (320 - view_w)/2, (300 - view_h)/2
        
        def get_symbols(px, py, pw, ph, style):
            if "Left" in style: 
                return f'<polyline points="{px+10},{py+ph/2} {px+pw-10},{py+10} {px+pw-10},{py+ph-10} {px+10},{py+ph/2}" fill="none" stroke="#e74c3c" stroke-width="3"/>'
            if "Right" in style:
                return f'<polyline points="{px+pw-10},{py+ph/2} {px+10},{py+10} {px+10},{py+ph-10} {px+pw-10},{py+ph/2}" fill="none" stroke="#e74c3c" stroke-width="3"/>'
            if "Top" in style:
                return f'<polyline points="{px+pw/2},{py+10} {px+10},{py+ph-10} {px+pw-10},{py+ph-10} {px+pw/2},{py+10}" fill="none" stroke="#e74c3c" stroke-width="3"/>'
            return ""

        content = ""
        if "Sash" in layout:
            content += f'<rect x="{off_x}" y="{off_y}" width="{view_w}" height="{view_h}" fill="#fff" stroke="#333" stroke-width="6"/>'
            content += f'<rect x="{off_x+8}" y="{off_y+8}" width="{view_w-16}" height="{view_h/2}" fill="#f8f9fa" stroke="#666" stroke-width="2"/>'
            content += f'<rect x="{off_x+4}" y="{off_y+view_h/2}" width="{view_w-8}" height="{view_h/2-4}" fill="#f8f9fa" stroke="#333" stroke-width="4"/>'
            # Sliding Indicators
            content += f'<line x1="{off_x-15}" y1="{off_y+view_h*0.8}" x2="{off_x-15}" y2="{off_y+view_h*0.4}" stroke="#3498db" stroke-width="2"/>'
            content += f'<polyline points="{off_x-20},{off_y+view_h*0.5} {off_x-15},{off_y+view_h*0.4} {off_x-10},{off_y+view_h*0.5}" fill="none" stroke="#3498db" stroke-width="2"/>'
        elif "Transom" in layout:
            t_h = view_h * 0.3
            content += f'<rect x="{off_x}" y="{off_y}" width="{view_w}" height="{t_h}" fill="#f8f9fa" stroke="#333" stroke-width="4"/>'
            content += f'<rect x="{off_x}" y="{off_y+t_h}" width="{view_w}" height="{view_h-t_h}" fill="#f8f9fa" stroke="#333" stroke-width="4"/>'
            content += get_symbols(off_x, off_y, view_w, t_h, op_t)
            content += get_symbols(off_x, off_y+t_h, view_w, view_h-t_h, op_b)
        else:
            content += f'<rect x="{off_x}" y="{off_y}" width="{view_w}" height="{view_h}" fill="#f8f9fa" stroke="#333" stroke-width="6"/>'
            content += get_symbols(off_x, off_y, view_w, view_h, op_s)

        return f'<div style="background:#fff; border-radius:10px; padding:10px; border:1px solid #ddd;"><svg width="340" height="320" xmlns="http://www.w3.org/2000/svg">{content}</svg></div>'

# ==========================================
# 5. DATA ORCHESTRATION & STATE
# ==========================================
if 'enterprise_db' not in st.session_state:
    st.session_state.enterprise_db = {}

# ==========================================
# 6. SIDEBAR: PROJECT MANAGEMENT HUB
# ==========================================
with st.sidebar:
    st.title("📂 Site Inventory")
    with st.expander("➕ NEW PROJECT", expanded=False):
        site_address = st.text_input("Project Address")
        client_name = st.text_input("Client/Reference")
        if st.button("INITIALIZE FOLDER"):
            if site_address:
                st.session_state.enterprise_db[site_address] = {
                    "units": [], "client": client_name, "status": "SURVEY", "date": datetime.now().strftime("%Y-%m-%d")
                }
                st.success(f"Project '{site_address}' Registered.")

    project_list = ["Select Project..."] + list(st.session_state.enterprise_db.keys())
    active_site = st.selectbox("ACTIVE SITE FOLDER", project_list)
    
    if active_site != "Select Project...":
        st.divider()
        st.subheader("Order Settings")
        order_env = st.radio("Context", ["Replacement", "New Build"])
        vat_calc = st.toggle("Show VAT-Inclusive Prices", value=True)
        st.divider()
        st.button("Generate Cloud Backup")

# ==========================================
# 7. MAIN MODULES
# ==========================================
if active_site == "Select Project...":
    st.title("Window Survey Enterprise Hub")
    st.info("👈 Use the sidebar to create or select a site folder. All data is synchronized across Rep and Fitter views.")
    st.image("https://img.freepik.com/free-vector/blueprint-architecture-construction-concept_52683-39328.jpg", width=600)
else:
    site = st.session_state.enterprise_db[active_site]
    
    # SITE HUD (Heads-Up Display)
    m1, m2, m3, m4 = st.columns(4)
    total_quote = sum(u['p'] for u in site['units'])
    m1.metric("Site Address", active_site)
    m2.metric("Units Measured", len(site['units']))
    m3.metric("Project Valuation", f"€{total_quote:,.2f}")
    m4.metric("Site Rep", "Admin")

    tabs = st.tabs(["🏗️ SURVEYOR CAPTURE", "📊 REP DASHBOARD", "🚚 FITTER PACK"])

    # ------------------------------------------
    # MODULE A: SURVEYOR CAPTURE
    # ------------------------------------------
    with tabs[0]:
        col_form, col_vis = st.columns([2, 1.2])
        
        with col_form:
            with st.container(border=True):
                st.subheader("1. Elevation Geometry & Material")
                cr1, cr2, cr3 = st.columns(3)
                room = cr1.text_input("Location/Room", "Kitchen")
                prod = cr2.selectbox("Product Line", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
                lay = cr3.selectbox("Configuration", ["Single Elevation", "Transom (Top over Bottom)", "Vertical Sliding Sash"])
                
                dr1, dr2, dr3 = st.columns(3)
                width = dr1.number_input("Finished Width (mm)", 100, 6000, 1200)
                height = dr2.number_input("Finished Height (mm)", 100, 6000, 1000)
                color = dr3.selectbox("Finish/RAL", ["White", "7016 Anthracite", "9005 Black", "Oak Grain", "Cream"])

            with st.container(border=True):
                st.subheader("2. Opening Configuration")
                opt, opb, ops = "Fixed", "Fixed", "Fixed"
                if "Transom" in lay:
                    tr1, tr2 = st.columns(2)
                    opt = tr1.selectbox("Top Fanlight", ["Fixed", "Top Hung"])
                    opb = tr2.selectbox("Bottom Main", ["Fixed", "Side Left", "Side Right"])
                elif "Single" in lay:
                    ops = st.selectbox("Main Opening Style", ["Fixed", "Side Left", "Side Right", "Top Hung"])
                
                sash_qty = st.slider("Total Opening Sash Count", 0, 10, 0 if (opt=="Fixed" and opb=="Fixed" and ops=="Fixed") else 1)

            with st.container(border=True):
                st.subheader("3. Technical Factory Specs")
                tr1, tr2, tr3 = st.columns(3)
                drip = tr1.selectbox("Head Drip Detail", ["Standard Drip", "28mm Drip", "No Drip"])
                cill = tr2.selectbox("Cill Specification", ["None", "30mm (Stub)", "85mm", "150mm", "180mm"])
                glass = tr3.selectbox("Glazing Unit", ["Double Glazed", "Triple Glazed", "Toughened Safety", "Acoustic (6.4mm)"])

        with col_vis:
            st.subheader("Elevation Preview")
            st.markdown(ElevationDrawer.generate_svg(width, height, lay, opt, opb, ops), unsafe_allow_html=True)
            
            st.subheader("Site Logistics")
            floor = st.selectbox("Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "Roof Access"])
            access = st.radio("Access Requirements", ["Standard Ladder", "Scaffold Required", "Cherry Picker"], horizontal=True)
            site_note = st.text_area("Critical Fitter Notes", placeholder="e.g., 'Internal scaffold required', 'Restricted parking'")
            
            if st.button("✅ FINALIZE & SYNC UNIT", use_container_width=True, type="primary"):
                p = PricingEngine.calculate_unit(width, height, sash_qty, prod, order_env, vat_calc)
                site['units'].append({
                    "id": len(site['units'])+1, "r": room, "s": f"{width}x{height}", "m": prod,
                    "p": p, "dr": drip, "ci": cill, "gl": glass, "fl": floor, "ac": access, "no": site_note
                })
                st.toast(f"Synchronized: {room}")
                st.rerun()

    # ------------------------------------------
    # MODULE B: REP DASHBOARD (Customer Proposal)
    # ------------------------------------------
    with tabs[1]:
        st.subheader(f"Customer Proposal: {active_site}")
        if site['units']:
            # High-density Rep Data View
            rep_df = pd.DataFrame(site['units'])
            st.dataframe(rep_df[['r', 's', 'm', 'p']], use_container_width=True, hide_index=True)
            
            st.divider()
            c_rep1, c_rep2 = st.columns([2, 1])
            with c_rep2:
                st.metric("GRAND TOTAL (GROSS)", f"€{total_quote:,.2f}")
                st.button("Review Digital Contract")
        else:
            st.warning("No survey data detected for this project.")

    # ------------------------------------------
    # MODULE C: FITTER PACK (Technical Brief)
    # ------------------------------------------
    with tabs[2]:
        st.subheader("📋 INSTALLER TECHNICAL BRIEF")
        st.write("Clean data summary for site check and installation day.")
        
        if site['units']:
            for i, u in enumerate(site['units']):
                with st.expander(f"📍 UNIT {i+1}: {u['r']} ({u['s']})"):
                    fc1, fc2, fc3 = st.columns(3)
                    with fc1:
                        st.markdown(f"**Factory Specs:**")
                        st.write(f"- Drip: {u['dr']}")
                        st.write(f"- Cill: {u['ci']}")
                    with fc2:
                        st.markdown(f"**Glazing:**")
                        st.write(f"- {u['gl']}")
                    with fc3:
                        st.markdown(f"**Logistics:**")
                        st.write(f"- Level: {u['fl']}")
                        st.write(f"- Access: {u['ac']}")
                    
                    st.markdown(f"<div class='fitter-brief'><b>Site Notes:</b> {u['no']}</div>", unsafe_allow_html=True)
            
            st.divider()
            if st.button("🗑️ CLEAR ENTIRE SITE DATABASE", type="secondary"):
                site['units'] = []
                st.rerun()
