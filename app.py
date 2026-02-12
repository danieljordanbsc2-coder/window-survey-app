import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# --- ENTERPRISE CONFIG ---
st.set_page_config(page_title="Pro-Survey Enterprise", layout="wide", initial_sidebar_state="expanded")

# --- CORE PRICING ENGINE ---
def calculate_unit_price(w, h, extra_sashes, material, job_type, include_vat):
    area = (w * h) / 1_000_000
    
    # Tiered Area Rates [cite: 2026-02-10]
    if area < 0.6: base_rate = 698
    elif area < 0.8: base_rate = 652
    elif area < 1.0: base_rate = 501
    elif area < 1.2: base_rate = 440
    elif area < 1.5: base_rate = 400
    elif area < 2.0: base_rate = 380
    elif area < 2.5: base_rate = 344
    elif area < 3.0: base_rate = 330
    elif area < 3.5: base_rate = 316
    elif area < 4.0: base_rate = 304
    elif area < 4.5: base_rate = 291
    else: base_rate = 277
    
    # Unit Calculation
    list_price = (base_rate * area) + (extra_sashes * 80)
    net_cost, install_fee = 0, 0
    
    # Material Multipliers [cite: 2026-02-11]
    if material == "PVC Standard":
        net_cost = list_price * 0.55
    elif material == "Aluclad Standard":
        net_cost = list_price
        install_fee = 325 if job_type == "Replacement" else 0
    elif material == "PVC Sliding Sash":
        net_cost = (list_price * 0.60) * 2
        install_fee = 438 if job_type == "Replacement" else 0
    elif material == "Hardwood Sliding Sash":
        net_cost = (list_price * 0.95) * 2.2
        install_fee = 480 if job_type == "Replacement" else 0
    elif material == "Aluclad Sliding Sash":
        net_cost = list_price * 2.5
        install_fee = 480 if job_type == "Replacement" else 0
    elif material == "Fireproof":
        net_cost = list_price * 0.55
        install_fee = 245 if job_type == "Replacement" else 0
    
    final_price = (max(net_cost, 300.0) + install_fee)
    if include_vat:
        final_price *= 1.135
        
    return round(final_price, 2)

# --- TECHNICAL DRAWING ENGINE ---
def render_technical_svg(w, h, layout, s1, s2):
    ratio = w / h
    bw = 280 if ratio > 1 else 280 * ratio
    bh = 280 if ratio < 1 else 280 / ratio
    x, y = (320 - bw)/2, (300 - bh)/2
    
    def get_arrow(px, py, pw, ph, mode):
        if "Left" in mode: return f'<polyline points="{px+10},{py+ph/2} {px+pw-10},{py+10} {px+pw-10},{py+ph-10} {px+10},{py+ph/2}" fill="none" stroke="red" stroke-width="3"/>'
        if "Right" in mode: return f'<polyline points="{px+pw-10},{py+ph/2} {px+10},{py+10} {px+10},{py+ph-10} {px+pw-10},{py+ph/2}" fill="none" stroke="red" stroke-width="3"/>'
        if "Top" in mode: return f'<polyline points="{px+pw/2},{py+10} {px+10},{py+ph-10} {px+pw-10},{py+ph-10} {px+pw/2},{py+10}" fill="none" stroke="red" stroke-width="3"/>'
        return ""

    svg_content = ""
    if layout == "Vertical Sliding Sash":
        svg_content += f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="none" stroke="black" stroke-width="5"/>'
        svg_content += f'<rect x="{x+6}" y="{y+6}" width="{bw-12}" height="{bh/2}" fill="#f0f2f6" stroke="#555" stroke-width="2"/>'
        svg_content += f'<rect x="{x+2}" y="{y+bh/2}" width="{bw-4}" height="{bh/2-2}" fill="#f0f2f6" stroke="black" stroke-width="4"/>'
        svg_content += f'<path d="M{x+bw+10} {y+20} L{x+bw+10} {y+60} M{x+bw+5} {y+50} L{x+bw+10} {y+60} L{x+bw+15} {y+50}" stroke="blue" fill="none" stroke-width="2"/>'
    elif layout == "Transom Split (Top/Bottom)":
        th = bh * 0.3
        svg_content += f'<rect x="{x}" y="{y}" width="{bw}" height="{th}" fill="#f8f9fa" stroke="black" stroke-width="3"/>'
        svg_content += f'<rect x="{x}" y="{y+th}" width="{bw}" height="{bh-th}" fill="#f8f9fa" stroke="black" stroke-width="3"/>'
        svg_content += get_arrow(x, y, bw, th, s1) + get_arrow(x, y+th, bw, bh-th, s2)
    else:
        svg_content += f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="#f8f9fa" stroke="black" stroke-width="5"/>'
        svg_content += get_arrow(x, y, bw, bh, s1)

    return f'<div style="text-align:center;"><svg width="340" height="320" style="background:#fff; border-radius:8px;">{svg_content}</svg></div>'

# --- STATE MANAGEMENT ---
if 'projects' not in st.session_state: st.session_state.projects = {}

# --- SIDEBAR: PROJECT MANAGEMENT ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1087/1087815.png", width=60)
    st.title("Project Center")
    with st.expander("🆕 Create New Site", expanded=False):
        site_name = st.text_input("Site Address")
        client_ref = st.text_input("Client Reference")
        if st.button("Initialize Project"):
            if site_name:
                st.session_state.projects[site_name] = {"data": [], "ref": client_ref, "created": datetime.now()}
                st.success("Project Created")

    sel_project = st.selectbox("Select Active Project", ["None"] + list(st.session_state.projects.keys()))
    
    if sel_project != "None":
        st.divider()
        st.subheader("Project Settings")
        order_type = st.radio("Standard Order", ["New Build", "Replacement"])
        vat_toggle = st.toggle("Price Including VAT", value=True)

# --- MAIN INTERFACE ---
if sel_project == "None":
    st.title("Professional Window Survey System")
    st.info("Please create or select a site folder from the sidebar to begin.")
else:
    proj_data = st.session_state.projects[sel_project]
    
    # --- TOP DASHBOARD ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Site Status", "In Progress")
    c2.metric("Unit Count", len(proj_data['data']))
    total_val = sum(item['price'] for item in proj_data['data'])
    c3.metric("Project Value", f"€{total_val:,.2f}")
    c4.metric("VAT Rate", "13.5%")

    tab_survey, tab_schedule, tab_logistics = st.tabs(["🏗 Surveyor Input", "📋 Production Schedule", "🚚 Fitter's View"])

    with tab_survey:
        col_input, col_visual = st.columns([2, 1])
        
        with col_input:
            st.subheader("1. Elevation Specification")
            with st.container(border=True):
                r1_c1, r1_c2, r1_c3 = st.columns(3)
                room = r1_c1.text_input("Room Identifier", "Living Room")
                prod_mat = r1_c2.selectbox("Material System", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
                win_lay = r1_c3.selectbox("Configuration", ["Single Opening", "Transom Split (Top/Bottom)", "Vertical Sliding Sash"])

                r2_c1, r2_c2, r2_c3 = st.columns(3)
                width = r2_c1.number_input("Survey Width (mm)", 100, 6000, 1200)
                height = r2_c2.number_input("Survey Height (mm)", 100, 6000, 1000)
                color = r2_c3.selectbox("RAL/Color", ["White", "Anthracite (7016)", "Black (9005)", "Oak", "Cream"])

            st.subheader("2. Opening Directions & Hardware")
            with st.container(border=True):
                h1_c1, h1_c2 = st.columns(2)
                op_top, op_bot = "Fixed", "Fixed"
                
                if win_lay == "Transom Split (Top/Bottom)":
                    op_top = h1_c1.selectbox("Fanlight (Top)", ["Fixed", "Top Hung"])
                    op_bot = h1_c2.selectbox("Main (Bottom)", ["Fixed", "Side Left", "Side Right"])
                elif win_lay == "Single Opening":
                    op_top = h1_c1.selectbox("Operation", ["Fixed", "Side Left", "Side Right", "Top Hung"])
                
                num_sashes = st.slider("Total Extra Opening Sashes", 0, 8, 0 if op_top == "Fixed" and op_bot == "Fixed" else 1)

            st.subheader("3. Technical Validation")
            with st.container(border=True):
                t1, t2, t3 = st.columns(3)
                drip_spec = t1.selectbox("Head Drip Detail", ["Standard Drip", "28mm Drip", "No Drip"])
                cill_spec = t2.selectbox("Cill Profile", ["None", "30mm Stub", "85mm", "150mm", "180mm"])
                glass_spec = t3.selectbox("Glazing Spec", ["Double Glazed", "Triple Glazed", "Toughened Safety", "Acoustic 6.4mm", "Obscure (Level 3)"])

        with col_visual:
            st.subheader("Technical Elevation")
            st.markdown(render_technical_svg(width, height, win_lay, op_top, op_bot), unsafe_allow_html=True)
            
            st.subheader("Fitter Notes")
            floor_lvl = st.selectbox("Floor Level", ["Ground", "1st Floor", "2nd Floor", "Roof/High Access"])
            access_req = st.radio("Access Requirements", ["Standard Ladder", "Scaffolding Required", "Mechanical Lift"], horizontal=True)
            
            if st.button("✅ FINALIZE & ADD TO PROJECT", use_container_width=True, type="primary"):
                calculated_price = calculate_unit_price(width, height, num_sashes, prod_mat, order_type, vat_toggle)
                entry = {
                    "id": len(proj_data['data']) + 1,
                    "room": room,
                    "size": f"{width}x{height}",
                    "material": prod_mat,
                    "layout": win_lay,
                    "drip": drip_spec,
                    "cill": cill_spec,
                    "glass": glass_spec,
                    "price": calculated_price,
                    "floor": floor_lvl,
                    "access": access_req
                }
                proj_data['data'].append(entry)
                st.toast(f"Unit saved to {sel_project}!")
                st.rerun()

    with tab_schedule:
        if not proj_data['data']:
            st.warning("No survey entries found for this project.")
        else:
            st.subheader("Comprehensive Production Schedule")
            full_df = pd.DataFrame(proj_data['data'])
            st.dataframe(full_df[['id', 'room', 'material', 'size', 'drip', 'cill', 'glass', 'price']], use_container_width=True, hide_index=True)
            
            st.divider()
            sq1, sq2 = st.columns([3, 1])
            sq2.metric("Grand Total (Gross)", f"€{total_val:,.2f}")
            if st.button("🗑️ Clear All Project Data", type="secondary"):
                proj_data['data'] = []
                st.rerun()

    with tab_logistics:
        if proj_data['data']:
            st.subheader("Installation & Site Access Log")
            log_df = pd.DataFrame(proj_data['data'])
            st.table(log_df[['room', 'size', 'floor', 'access']])
            
            with st.container(border=True):
                st.write("### Site Logistics Summary")
                needs_scaffold = any("Scaffold" in x for x in log_df['access'])
                st.write(f"**Scaffolding Required:** {'⚠️ YES' if needs_scaffold else 'No'}")
                st.write(f"**Total High Access Units:** {len(log_df[log_df['floor'] != 'Ground'])}")
