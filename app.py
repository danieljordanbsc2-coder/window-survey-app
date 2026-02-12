import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
import base64

# --- 1. ENTERPRISE CONFIGURATION ---
st.set_page_config(page_title="Windows Enterprise v5.0", layout="wide", initial_sidebar_state="expanded")

# --- 2. THE PRICING ENGINE (Locked to 2026 Rules) ---
def get_p(w, h, sas, mat, job, vat):
    """
    Implements the 2026 Area-Tiered Price Ladder.
    [cite: 2026-02-10, 2026-02-11]
    """
    area = (w * h) / 1_000_000
    # Strict Area Tiers
    if area < 0.6: b = 698
    elif area < 0.8: b = 652
    elif area < 1.0: b = 501
    elif area < 1.2: b = 440
    elif area < 1.5: b = 400
    elif area < 2.0: b = 380
    elif area < 2.5: b = 344
    elif area < 3.0: b = 330
    elif area < 3.5: b = 316
    elif area < 4.0: b = 304
    elif area < 4.5: b = 291
    else: b = 277
    
    # Calculation Logic
    unit_base = (b * area) + (sas * 80)
    c, fee = 0, 0
    
    if mat == "PVC Standard": 
        c = unit_base * 0.55
    elif mat == "Aluclad Standard": 
        c = unit_base
        fee = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": 
        c = (unit_base * 0.60) * 2
        fee = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": 
        c = (unit_base * 0.95) * 2.2
        fee = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": 
        c = unit_base * 2.5
        fee = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": 
        c = unit_base * 0.55
        fee = 245 if job == "Replacement" else 0
        
    return round((max(c, 300.0) + fee) * (1.135 if vat else 1), 2)

# --- 3. TECHNICAL DESIGN ENGINE ---
def render_elevation(w, h, style, o1, o2):
    """
    Automated CAD-style rendering for Rep/Customer review.
    """
    ratio = w / h
    box_w = 280 if ratio > 1 else 280 * ratio
    box_h = 280 if ratio < 1 else 280 / ratio
    x, y = (320 - box_w)/2, (300 - box_h)/2
    
    def get_arrow(px, py, pw, ph, mode):
        if "Left" in mode: return f'<polyline points="{px+10},{py+ph/2} {px+pw-10},{py+10} {px+pw-10},{py+ph-10} {px+10},{py+ph/2}" fill="none" stroke="red" stroke-width="3"/>'
        if "Right" in mode: return f'<polyline points="{px+pw-10},{py+ph/2} {px+10},{py+10} {px+10},{py+ph-10} {px+pw-10},{py+ph/2}" fill="none" stroke="red" stroke-width="3"/>'
        if "Top" in mode: return f'<polyline points="{px+pw/2},{py+10} {px+10},{py+ph-10} {px+pw-10},{py+ph-10} {px+pw/2},{py+10}" fill="none" stroke="red" stroke-width="3"/>'
        return ""

    frames = ""
    if style == "Vertical Sash":
        frames += f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" fill="none" stroke="black" stroke-width="5"/>'
        frames += f'<rect x="{x+6}" y="{y+6}" width="{box_w-12}" height="{box_h/2}" fill="#e3f2fd" stroke="#444" stroke-width="2"/>'
        frames += f'<rect x="{x+2}" y="{y+box_h/2}" width="{box_w-4}" height="{box_h/2-2}" fill="#e3f2fd" stroke="black" stroke-width="4"/>'
    elif style == "Transom (Top/Bottom)":
        th = box_h * 0.3
        frames += f'<rect x="{x}" y="{y}" width="{box_w}" height="{th}" fill="#f8f9fa" stroke="black" stroke-width="3"/>'
        frames += f'<rect x="{x}" y="{y+th}" width="{box_w}" height="{box_h-th}" fill="#f8f9fa" stroke="black" stroke-width="3"/>'
        frames += get_arrow(x, y, box_w, th, o1) + get_arrow(x, y+th, box_w, box_h-th, o2)
    else:
        frames += f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" fill="#f8f9fa" stroke="black" stroke-width="5"/>'
        frames += get_arrow(x, y, box_w, box_h, o1)

    return f'<div style="text-align:center;"><svg width="340" height="320" style="background:white; border-radius:12px; padding:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">{frames}</svg></div>'

# --- 4. SESSION MANAGEMENT ---
if 'projects' not in st.session_state: st.session_state.projects = {}

# --- 5. SIDEBAR: PROJECT DASHBOARD ---
with st.sidebar:
    st.title("📂 Site Folders")
    new_site = st.text_input("Site Address")
    if st.button("Initialize Folder"):
        if new_site:
            st.session_state.projects[new_site] = {"data": [], "status": "Surveying"}
            st.success(f"{new_site} Created")
    
    active_site = st.selectbox("Current Active Project", ["Select Project..."] + list(st.session_state.projects.keys()))
    
    if active_site != "Select Project...":
        st.divider()
        st.subheader("Global Job Setup")
        job_type = st.radio("Order Environment", ["Replacement", "New Build"])
        vat_mode = st.toggle("Price Including VAT (13.5%)", value=True)

# --- 6. MAIN APPLICATION MODULES ---
if active_site == "Select Project...":
    st.title("Window Survey Enterprise v5.0")
    st.info("Select or create a site folder to begin the capture process.")
else:
    site_db = st.session_state.projects[active_site]
    
    # 🛰️ STATUS HUD
    h1, h2, h3 = st.columns(3)
    total_val = sum(u['price'] for u in site_db['data'])
    h1.metric("Units Measured", len(site_db['data']))
    h2.metric("Quote Total", f"€{total_val:,.2f}")
    h3.metric("Project Status", site_db['status'])

    tabs = st.tabs(["🏗️ SURVEY INPUT", "🛠️ THE FITTER'S PACK"])

    with tabs[0]:
        col_design, col_preview = st.columns([2, 1])
        
        with col_design:
            with st.container(border=True):
                st.subheader("1. Elevation Geometry")
                r1, r2, r3 = st.columns(3)
                room = r1.text_input("Room Identifier", "Kitchen")
                mat = r2.selectbox("Product System", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
                lay = r3.selectbox("Layout Config", ["Single Opening", "Transom (Top/Bottom)", "Vertical Sash"])
                
                d1, d2, d3 = st.columns(3)
                w_mm = d1.number_input("Width (mm)", 100, 6000, 1200)
                h_mm = d2.number_input("Height (mm)", 100, 6000, 1000)
                col = d3.selectbox("Finish", ["White", "Anthracite", "Black", "Oak", "Cream"])

            with st.container(border=True):
                st.subheader("2. Opening Style & Hardware")
                o1, o2 = "Fixed", "Fixed"
                if lay == "Transom (Top/Bottom)":
                    oc1, oc2 = st.columns(2)
                    o1 = oc1.selectbox("Top Pane (Fanlight)", ["Fixed", "Top Hung"])
                    o2 = oc2.selectbox("Main Bottom", ["Fixed", "Side Left", "Side Right"])
                elif lay == "Single Opening":
                    o1 = st.selectbox("Operation Style", ["Fixed", "Side Left", "Side Right", "Top Hung"])
                
                sas_num = st.slider("Total Opening Sashes (Pricing)", 0, 8, 0 if o1 == "Fixed" and o2 == "Fixed" else 1)

            with st.container(border=True):
                st.subheader("3. Technical Validation")
                tc1, tc2, tc3 = st.columns(3)
                drip = tc1.selectbox("Head Drip Spec", ["Standard Drip", "28mm Drip", "No Drip"])
                cill = tc2.selectbox("Cill Requirement", ["None", "30mm (Stub)", "85mm", "150mm", "180mm"])
                glass = tc3.selectbox("Glazing Unit", ["Double Glazed", "Triple Glazed", "Toughened Safety", "Acoustic", "Obscure"])

        with col_preview:
            st.subheader("Elevation Review")
            st.markdown(render_elevation(w_mm, h_mm, lay, o1, o2), unsafe_allow_html=True)
            
            st.subheader("Installer Logistics")
            floor = st.selectbox("Installation Level", ["Ground Floor", "1st Floor", "2nd Floor", "Roof Level"])
            access = st.radio("Access Req.", ["Ladder", "Scaffolding", "Cherry Picker"], horizontal=True)
            note = st.text_area("Site Specific Notes (e.g. 'Narrow Entrance')")
            
            if st.button("✅ FINALIZE & SYNC", use_container_width=True, type="primary"):
                p = get_p(w_mm, h_mm, sas_num, mat, job_type, vat_mode)
                site_db['data'].append({
                    "id": len(site_db['data'])+1, "room": room, "size": f"{w_mm}x{h_mm}", "mat": mat,
                    "price": p, "drip": drip, "cill": cill, "glass": glass, "floor": floor, "access": access, "note": note
                })
                st.rerun()

    with tabs[1]:
        st.subheader("📋 THE FITTER'S TECHNICAL PACK")
        st.write("Professional summary for site checking and installation logistics.")
        
        if site_db['data']:
            # Technical Table
            df = pd.DataFrame(site_db['data'])
            st.table(df[['room', 'size', 'mat', 'drip', 'cill', 'floor', 'access']])
            
            st.divider()
            st.subheader("Quote Breakdown")
            st.table(df[['room', 'size', 'price']])
            st.metric("GRAND TOTAL VALUE", f"€{total_val:,.2f}")
            
            if st.button("🗑️ RESET PROJECT"):
                site_db['data'] = []
                st.rerun()
