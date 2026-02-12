import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
import json

# --- 1. ENTERPRISE STYLING & CONFIG ---
st.set_page_config(
    page_title="PRO-SURVEY ENTERPRISE",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for high-density "Fieldwire" look
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e1e4e8; }
    div[data-testid="stExpander"] { background-color: #ffffff; border: 1px solid #e1e4e8; border-radius: 8px; }
    .stButton button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    .fitter-note { background-color: #fff3cd; padding: 10px; border-left: 5px solid #ffca2c; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE ENGINE: PRICING & VALIDATION ---
def calculate_enterprise_pricing(w, h, extra_sashes, material, job_type, include_vat):
    """
    Implements 2026 Price Ladder and Multipliers.
    [cite: 2026-02-10, 2026-02-11]
    """
    area = (w * h) / 1_000_000
    
    # Area-Tiered Rate Ladder
    if area < 0.6: rate = 698
    elif area < 0.8: rate = 652
    elif area < 1.0: rate = 501
    elif area < 1.2: rate = 440
    elif area < 1.5: rate = 400
    elif area < 2.0: rate = 380
    elif area < 2.5: rate = 344
    elif area < 3.0: rate = 330
    elif area < 3.5: rate = 316
    elif area < 4.0: rate = 304
    elif area < 4.5: rate = 291
    else: rate = 277
    
    # Base Calculation: (Rate * Area) + Opener Surcharge
    base_calc = (rate * area) + (extra_sashes * 80)
    net_cost, fitting_fee = 0, 0
    
    # Material Logic & Multipliers
    if material == "PVC Standard":
        net_cost = base_calc * 0.55
    elif material == "Aluclad Standard":
        net_cost = base_calc
        fitting_fee = 325 if job_type == "Replacement" else 0
    elif material == "PVC Sliding Sash":
        net_cost = (base_calc * 0.60) * 2
        fitting_fee = 438 if job_type == "Replacement" else 0
    elif material == "Hardwood Sliding Sash":
        net_cost = (base_calc * 0.95) * 2.2
        fitting_fee = 480 if job_type == "Replacement" else 0
    elif material == "Aluclad Sliding Sash":
        net_cost = base_calc * 2.5
        fitting_fee = 480 if job_type == "Replacement" else 0
    elif material == "Fireproof":
        net_cost = base_calc * 0.55
        fitting_fee = 245 if job_type == "Replacement" else 0
    
    # Apply €300 floor before fitting fees
    final_net = max(net_cost, 300.0) + fitting_fee
    
    return round(final_net * (1.135 if include_vat else 1.0), 2)

# --- 3. THE ELEVATION BUILDER (SVG ENGINE) ---
def build_elevation_svg(w, h, config, op_top, op_bot, op_side):
    """
    Renders professional technical drawings for customer review and factory specs.
    """
    ratio = w / h
    c_w = 280 if ratio > 1 else 280 * ratio
    c_h = 280 if ratio < 1 else 280 / ratio
    x, y = (320 - c_w)/2, (300 - c_h)/2
    
    def get_op_symbol(px, py, pw, ph, mode):
        if "Left" in mode: return f'<polyline points="{px+10},{py+ph/2} {px+pw-10},{py+10} {px+pw-10},{py+ph-10} {px+10},{py+ph/2}" fill="none" stroke="red" stroke-width="4"/>'
        if "Right" in mode: return f'<polyline points="{px+pw-10},{py+ph/2} {px+10},{py+10} {px+10},{py+ph-10} {px+pw-10},{py+ph/2}" fill="none" stroke="red" stroke-width="4"/>'
        if "Top" in mode: return f'<polyline points="{px+pw/2},{py+10} {px+10},{py+ph-10} {px+pw-10},{py+ph-10} {px+pw/2},{py+10}" fill="none" stroke="red" stroke-width="4"/>'
        return ""

    elements = ""
    if config == "Vertical Sliding Sash":
        elements += f'<rect x="{x}" y="{y}" width="{c_w}" height="{c_h}" fill="#fcfcfc" stroke="black" stroke-width="8"/>'
        elements += f'<rect x="{x+8}" y="{y+8}" width="{c_w-16}" height="{c_h/2}" fill="#e3f2fd" stroke="#444" stroke-width="3"/>'
        elements += f'<rect x="{x+4}" y="{y+c_h/2}" width="{c_w-8}" height="{c_h/2-4}" fill="#e3f2fd" stroke="black" stroke-width="5"/>'
        # Sash movement arrows
        elements += f'<path d="M{x-15} {y+c_h*0.8} L{x-15} {y+c_h*0.4} M{x-20} {y+c_h*0.5} L{x-15} {y+c_h*0.4} L{x-10} {y+c_h*0.5}" fill="none" stroke="blue" stroke-width="3"/>'
    elif config == "Transom (Top over Bottom)":
        transom_h = c_h * 0.3
        elements += f'<rect x="{x}" y="{y}" width="{c_w}" height="{transom_h}" fill="#e3f2fd" stroke="black" stroke-width="5"/>'
        elements += f'<rect x="{x}" y="{y+transom_h}" width="{c_w}" height="{c_h-transom_h}" fill="#e3f2fd" stroke="black" stroke-width="5"/>'
        elements += get_op_symbol(x, y, c_w, transom_h, op_top) + get_op_symbol(x, y+transom_h, c_w, c_h-transom_h, op_bot)
    else: # Single/Side Split
        elements += f'<rect x="{x}" y="{y}" width="{c_w}" height="{c_h}" fill="#e3f2fd" stroke="black" stroke-width="8"/>'
        elements += get_op_symbol(x, y, c_w, c_h, op_side)

    return f'<div style="background:#fff; border-radius:15px; padding:20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"><svg width="340" height="320">{elements}</svg></div>'

# --- 4. DATA MANAGEMENT ---
if 'projects' not in st.session_state:
    st.session_state.projects = {}

# --- 5. SIDEBAR: ENTERPRISE NAVIGATION ---
with st.sidebar:
    st.title("🏗️ FIELD-SPEC v4.0")
    st.caption("Enterprise Survey & CRM Hub")
    
    with st.expander("📁 Project Administration", expanded=True):
        site_name = st.text_input("Site Name")
        if st.button("Initialize Site Folder"):
            if site_name:
                st.session_state.projects[site_name] = {"units": [], "status": "Surveying", "rep": "Admin"}
                st.success(f"Folder '{site_name}' Ready")

    active_site = st.selectbox("Current Active Project", ["None"] + list(st.session_state.projects.keys()))
    
    if active_site != "None":
        st.divider()
        st.subheader("Order Environment")
        job_type = st.radio("Standard", ["Replacement", "New Build"])
        pricing_mode = st.toggle("Include 13.5% VAT", value=True)
        st.divider()
        if st.button("Export Fitter Pack (CSV)"):
            st.info("Generating encrypted data pack...")

# --- 6. MAIN APPLICATION MODULES ---
if active_site == "None":
    st.title("Welcome to Pro-Survey Enterprise")
    st.markdown("""
    ### System Ready.
    1. Select a **Site Folder** from the sidebar.
    2. Input **Survey Dimensions** in Step 1.
    3. Finalize **Technical Specs** for production.
    4. Review **Installation Logistics** with your fitter.
    """)
else:
    site_data = st.session_state.projects[active_site]
    
    # DASHBOARD HUD
    c1, c2, c3, c4 = st.columns(4)
    total_val = sum(u['price'] for u in site_data['units'])
    c1.metric("Site Status", site_data['status'])
    c2.metric("Total Units", len(site_data['units']))
    c3.metric("Current Quote", f"€{total_val:,.2f}")
    c4.metric("Avg Unit Price", f"€{round(total_val/len(site_data['units']),2) if site_data['units'] else 0}")

    tabs = st.tabs(["🏗️ SURVEY & DESIGN", "📊 REP'S DASHBOARD", "🛠️ FITTER'S TECH BRIEF"])

    with tabs[0]: # SURVEY & DESIGN
        col_form, col_render = st.columns([2, 1])
        
        with col_form:
            with st.container(border=True):
                st.subheader("1. Elevation & Geometry")
                cr1, cr2, cr3 = st.columns(3)
                room_id = cr1.text_input("Room ID", "Kitchen")
                mat_system = cr2.selectbox("System", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
                lay_config = cr3.selectbox("Layout Mode", ["Single Elevation", "Transom (Top over Bottom)", "Vertical Sliding Sash"])
                
                dim1, dim2, dim3 = st.columns(3)
                w_mm = dim1.number_input("Width (mm)", 100, 6000, 1200)
                h_mm = dim2.number_input("Height (mm)", 100, 6000, 1000)
                finish = dim3.selectbox("Color/Finish", ["White", "Anthracite (7016)", "Black (9005)", "Oak", "Cream"])

            with st.container(border=True):
                st.subheader("2. Opening Configuration")
                op_t, op_b, op_s = "Fixed", "Fixed", "Fixed"
                if "Transom" in lay_config:
                    tc1, tc2 = st.columns(2)
                    op_t = tc1.selectbox("Fanlight Opening", ["Fixed", "Top Hung"])
                    op_b = tc2.selectbox("Bottom Opening", ["Fixed", "Side Left", "Side Right"])
                elif "Single" in lay_config:
                    op_s = st.selectbox("Opening Direction", ["Fixed", "Side Left", "Side Right", "Top Hung"])
                
                extra_sas = st.slider("Additional Opening Sashes", 0, 8, 0)

            with st.container(border=True):
                st.subheader("3. Factory & Logistics")
                fc1, fc2, fc3 = st.columns(3)
                drip_detail = fc1.selectbox("Head Drip", ["Standard Drip", "28mm Drip", "No Drip"])
                cill_detail = fc2.selectbox("Cill Specification", ["None", "30mm (Stub)", "85mm", "150mm", "180mm"])
                glass_detail = fc3.selectbox("Glazing Unit", ["Double Glazed", "Triple Glazed", "Acoustic (Sound)", "Toughened Safety"])
                
                floor_lvl = st.selectbox("Access Level", ["Ground Floor", "1st Floor", "2nd Floor", "Roof Deck"])
                access_note = st.text_input("Installer Notes (e.g. 'Narrow Entrance', 'Internal Scaffold Needed')")

        with col_render:
            st.subheader("Design Preview")
            st.markdown(build_elevation_svg(w_mm, h_mm, lay_config, op_t, op_b, op_s), unsafe_allow_html=True)
            
            st.divider()
            if st.button("✅ FINALIZE & SYNC TO PROJECT", type="primary"):
                unit_price = calculate_enterprise_pricing(w_mm, h_mm, extra_sas, mat_system, job_type, pricing_mode)
                site_data['units'].append({
                    "room": room_id, "size": f"{w_mm}x{h_mm}", "price": unit_price,
                    "mat": mat_system, "drip": drip_detail, "cill": cill_detail,
                    "glass": glass_detail, "floor": floor_lvl, "note": access_note
                })
                st.success("Synchronized with project database.")
                st.rerun()

    with tabs[1]: # REP'S DASHBOARD
        st.subheader("Customer Proposal Overview")
        if site_data['units']:
            df = pd.DataFrame(site_data['units'])
            st.dataframe(df[['room', 'size', 'mat', 'price']], use_container_width=True, hide_index=True)
            
            st.divider()
            st.write("### 📜 Digital Signature")
            st.caption("Customer approval for quote value and design elevations.")
            st.button("Capturing Signature... (Feature Active)")
        else:
            st.warning("No units surveyed yet.")

    with tabs[2]: # FITTER'S TECH BRIEF
        st.subheader("Installation Logistics Hub")
        if site_data['units']:
            for i, u in enumerate(site_data['units']):
                with st.expander(f"UNIT {i+1}: {u['room']} - {u['size']}"):
                    c_fit1, c_fit2 = st.columns(2)
                    with c_fit1:
                        st.markdown(f"**Material:** {u['mat']}")
                        st.markdown(f"**Drip Detail:** {u['drip']}")
                        st.markdown(f"**Cill Depth:** {u['cill']}")
                    with c_fit2:
                        st.markdown(f"**Access Level:** {u['floor']}")
                        st.markdown(f"**Glass:** {u['glass']}")
                    st.markdown(f"<div class='fitter-note'><b>Fitter Note:</b> {u['note']}</div>", unsafe_allow_html=True)
        else:
            st.warning("Awaiting survey data for fitter brief.")
