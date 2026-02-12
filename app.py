import streamlit as st
import pandas as pd

# --- THE FIELDWIRE PRICING ENGINE ---
def get_p(w, h, sas, mat, job, vat):
    area = (w * h) / 1e6
    # Pricing Tiers
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
    
    # Calculate Base Unit Price based on Area
    unit_total = (b * area) + (sas * 80)
    c, f = 0, 0
    # Multipliers & Replacement Fees
    if mat == "PVC Standard": c = unit_total * 0.55
    elif mat == "Aluclad Standard": c = unit_total; f = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (unit_total * 0.60) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (unit_total * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = unit_total * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = unit_total * 0.55; f = 245 if job == "Replacement" else 0
    
    return round((max(c, 300.0) + f) * (1.135 if vat else 1), 2)

# --- TECHNICAL DRAWING ENGINE ---
def draw_spec(w, h, lay, s1, s2):
    r = w / h
    bw = 260 if r > 1 else 260 * r
    bh = 260 if r < 1 else 260 / r
    x, y = (320 - bw)/2, (300 - bh)/2
    
    def arrow(px, py, pw, ph, mode):
        if "Left" in mode: return f'<polyline points="{px+10},{py+ph/2} {px+pw-10},{py+10} {px+pw-10},{py+ph-10} {px+10},{py+ph/2}" fill="none" stroke="red" stroke-width="4"/>'
        if "Right" in mode: return f'<polyline points="{px+pw-10},{py+ph/2} {px+10},{py+10} {px+10},{py+ph-10} {px+pw-10},{py+ph/2}" fill="none" stroke="red" stroke-width="4"/>'
        if "Top" in mode: return f'<polyline points="{px+pw/2},{py+10} {px+10},{py+ph-10} {px+pw-10},{py+ph-10} {px+pw/2},{py+10}" fill="none" stroke="red" stroke-width="4"/>'
        return ""

    svg = ""
    if "Sash" in lay:
        svg += f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="none" stroke="black" stroke-width="6"/>'
        svg += f'<rect x="{x+6}" y="{y+6}" width="{bw-12}" height="{bh/2}" fill="#f8f9fa" stroke="#444" stroke-width="2"/>'
        svg += f'<rect x="{x+2}" y="{y+bh/2}" width="{bw-4}" height="{bh/2-2}" fill="#f8f9fa" stroke="black" stroke-width="4"/>'
    elif "Transom" in lay:
        th = bh * 0.3
        svg += f'<rect x="{x}" y="{y}" width="{bw}" height="{th}" fill="#f8f9fa" stroke="black" stroke-width="4"/>'
        svg += f'<rect x="{x}" y="{y+th}" width="{bw}" height="{bh-th}" fill="#f8f9fa" stroke="black" stroke-width="4"/>'
        svg += arrow(x, y, bw, th, s1) + arrow(x, y+th, bw, bh-th, s2)
    else:
        svg += f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="#f8f9fa" stroke="black" stroke-width="6"/>'
        svg += arrow(x, y, bw, bh, s1)
    
    st.write(f'<div style="display:flex;justify-content:center;"><svg width="320" height="300">{svg}</svg></div>', unsafe_allow_html=True)

# --- APP UI ---
st.set_page_config(page_title="Field-Ready Survey Hub", layout="wide")
if 'db' not in st.session_state: st.session_state.db = {}

with st.sidebar:
    st.title("📂 Site Folders")
    new_site = st.text_input("Site Address")
    if st.button("Initialize New Project"): st.session_state.db[new_site] = []
    
    sel = st.selectbox("Active Project", ["Select..."] + list(st.session_state.db.keys()))
    if sel != "Select...":
        st.divider()
        job_m = st.radio("Order Type", ["New Build", "Replacement"])
        vat_m = st.toggle("Incl. 13.5% VAT", True)

if sel != "Select...":
    st.title(f"📍 {sel}")
    tab1, tab2 = st.tabs(["📝 Surveyor Input", "📐 Site Schedule & Quote"])

    with tab1:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("1. Elevation Config")
            room = st.text_input("Room (e.g. Master Bed)", "Living Room")
            mat = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
            lay = st.selectbox("Layout", ["Single Pane", "Vertical Slider (Sash)", "Transom (Top over Bottom)"])
            
            cw, ch = st.columns(2)
            w = cw.number_input("Width (mm)", 100, 5000, 1200)
            h = ch.number_input("Height (mm)", 100, 5000, 1000)
            
            st.subheader("2. Factory Specs")
