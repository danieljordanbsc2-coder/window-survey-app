import streamlit as st
import pandas as pd

# --- 1. THE PRICING ENGINE (Locked to 2026 Tiers) ---
def get_p(w, h, sas, mat, job, vat):
    area = (w * h) / 1000000
    # Tiered Base Rates
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
    
    unit_base = b + (sas * 80)
    c, f = 0, 0
    # Replacement logic and multipliers
    if mat == "PVC Standard": c = unit_base * 0.55
    elif mat == "Aluclad Standard": c = unit_base; f = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (unit_base * 0.60) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (unit_base * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = unit_base * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = unit_base * 0.55; f = 245 if job == "Replacement" else 0
    
    final_ex = max(c, 300.0) + f
    return round(final_ex * (1.135 if vat else 1), 2)

# --- 2. THE VISUAL ENGINE ---
def draw_win(w, h, lay, s1, s2):
    r = w / h
    bw = 260 if r > 1 else 260 * r
    bh = 260 if r < 1 else 260 / r
    x, y = (300 - bw)/2, (300 - bh)/2
    
    def sym(px, py, pw, ph, mode):
        if "Left" in mode: return f'<polyline points="{px+5},{py+ph/2} {px+pw-5},{py+5} {px+pw-5},{py+ph-5} {px+5},{py+ph/2}" fill="none" stroke="red" stroke-width="2"/>'
        if "Right" in mode: return f'<polyline points="{px+pw-5},{py+ph/2} {px+5},{py+5} {px+5},{py+ph-5} {px+pw-5},{py+ph/2}" fill="none" stroke="red" stroke-width="2"/>'
        if "Top" in mode: return f'<polyline points="{px+pw/2},{py+5} {px+5},{py+ph-5} {px+pw-5},{py+ph-5} {px+pw/2},{py+5}" fill="none" stroke="red" stroke-width="2"/>'
        return ""

    frames = ""
    if "Sash" in lay:
        frames += f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="none" stroke="black" stroke-width="4"/>'
        frames += f'<rect x="{x+4}" y="{y+4}" width="{bw-8}" height="{bh/2}" fill="#f8f9fa" stroke="black" stroke-width="2"/>'
        frames += f'<rect x="{x+2}" y="{y+bh/2}" width="{bw-4}" height="{bh/2-2}" fill="#f8f9fa" stroke="black" stroke-width="3"/>'
        frames += f'<line x1="{x+bw+10}" y1="{y+bh*0.2}" x2="{x+bw+10}" y2="{y+bh*0.4}" stroke="blue" stroke-width="2"/>'
    elif "Transom" in lay:
        th = bh * 0.3
        frames += f'<rect x="{x}" y="{y}" width="{bw}" height="{th}" fill="#f8f9fa" stroke="black" stroke-width="3"/>'
        frames += f'<rect x="{x}" y="{y+th}" width="{bw}" height="{bh-th}" fill="#f8f9fa" stroke="black" stroke-width="3"/>'
        frames += sym(x, y, bw, th, s1) + sym(x, y+th, bw, bh-th, s2)
    else:
        frames += f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="#f8f9fa" stroke="black" stroke-width="4"/>'
        frames += sym(x, y, bw, bh, s1)

    st.write(f'<div style="display:flex;justify-content:center;"><svg width="320" height="300">{frames}</svg></div>', unsafe_allow_html=True)

# --- 3. APP INTERFACE ---
st.set_page_config(page_title="Pro Survey 3.5", layout="wide")
if 'db' not in st.session_state: st.session_state.db = {}

st.sidebar.title("🛠 Site Folder")
site_n = st.sidebar.text_input("Site Address")
if st.sidebar.button("Create Site"): st.session_state.db[site_n] = []
sel = st.sidebar.selectbox("Active Project", ["Select..."] + list(st.session_state.db.keys()))

if sel != "Select...":
    job_m = st.sidebar.radio("Job Mode", ["New Build", "Replacement"])
    vat_m = st.sidebar.toggle("Include VAT (13.5%)", True)
    
    st.header(f"Surveying: {sel}")
    
    t1, t2 = st.tabs(["🛠 Survey Entry", "📜 Quote Summary"])
    
    with t1:
        with st.expander("1. Dimensions & Elevation", expanded=True):
            c1, c2, c3 = st.columns(3)
            room = c1.text_input("Room Name", "Kitchen")
            mat = c2.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
            lay = c3.selectbox("Layout", ["Single", "Vertical Slider (Sash)", "Transom (Top over Bottom)"])
            
            c4, c5, c6 = st.columns(3)
            w = c4.number_input("Width (mm)", 100, 5000, 1200)
            h
