import streamlit as st
import pandas as pd

# --- 1. PRICING ENGINE (Restored Tiered Logic) ---
def get_p(w, h, sas, mat, job, vat):
    area = (w * h) / 1000000
    # Strict Area Tiers [cite: 2026-02-10]
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
    # Multipliers & Fees [cite: 2026-02-11]
    if mat == "PVC Standard": c = unit_base * 0.55
    elif mat == "Aluclad Standard": c = unit_base; f = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (unit_base * 0.60) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (unit_base * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = unit_base * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = unit_base * 0.55; f = 245 if job == "Replacement" else 0
    
    final_ex = max(c, 300.0) + f
    return round(final_ex * (1.135 if vat else 1), 2)

# --- 2. VISUAL ENGINE ---
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

    frms = ""
    if "Sash" in lay:
        frms += f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="none" stroke="black" stroke-width="4"/>'
        frms += f'<rect x="{x+4}" y="{y+4}" width="{bw-8}" height="{bh/2}" fill="#f8f9fa" stroke="black" stroke-width="2"/>'
        frms += f'<rect x="{x+2}" y="{y+bh/2}" width="{bw-4}" height="{bh/2-2}" fill="#f8f9fa" stroke="black" stroke-width="3"/>'
    elif "Transom" in lay:
        th = bh * 0.3
        frms += f'<rect x="{x}" y="{y}" width="{bw}" height="{th}" fill="#f8f9fa" stroke="black" stroke-width="3"/>'
        frms += f'<rect x="{x}" y="{y+th}" width="{bw}" height="{bh-th}" fill="#f8f9fa" stroke="black" stroke-width="3"/>'
        frms += sym(x, y, bw, th, s1) + sym(x, y+th, bw, bh-th, s2)
    else:
        frms += f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="#f8f9fa" stroke="black" stroke-width="4"/>'
        frms += sym(x, y, bw, bh, s1)

    st.write(f'<div style="display:flex;justify-content:center;"><svg width="320" height="300">{frms}</svg></div>', unsafe_allow_html=True)

# --- 3. APP INTERFACE ---
st.set_page_config(page_title="Pro Survey 3.6", layout="wide")
if 'db' not in st.session_state: st.session_state.db = {}

st.sidebar.title("🛠 Site Folder")
site_n = st.sidebar.text_input("Address")
if st.sidebar.button("Add Site"): st.session_state.db[site_n] = []
sel = st.sidebar.selectbox("Active Project", ["Select..."] + list(st.session_state.db.keys()))

if sel != "Select...":
    job_m = st.sidebar.radio("Job Mode", ["New Build", "Replacement"])
    vat_m = st.sidebar.toggle("Include VAT (13.5%)", True)
    
    st.header(f"Survey: {sel}")
    tab1, tab2 = st.tabs(["📝 Entry", "📜 Full Quote"])
    
    with tab1:
        with st.expander("1. Elevation Design", expanded=True):
            c1, c2, c3 = st.columns(3)
            room = c1.text_input("Room", "Living Room")
            mat = c2.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
            lay = c3.selectbox("Layout", ["Single", "Vertical Slider (Sash)", "Transom (Top over Bottom)"])
            
            c4, c5, c6 = st.columns(3)
            w = c4.number_input("Width (mm)", 100, 5000, 1200)
            h = c5.number_input("Height (mm)", 100, 5000, 1000)
            col = c6.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"])
            
            o1, o2 = "Fixed", "Fixed"
            if "Transom" in lay:
                co1, co2 = st.columns(2)
                o1 = co1.selectbox("Top", ["Fixed", "Top Hung"])
                o2 = co2.selectbox("Bottom", ["Fixed", "Side Left", "Side Right"])
            elif "Single" in lay:
                o1 = st.selectbox("Style", ["Fixed", "Side Left", "Side Right", "Top Hung"])
            draw_win(w, h, lay, o1, o2)

        with st.expander("2. Tech Specs"):
            tc1, tc2, tc3 = st.columns(3)
            drip = tc1.selectbox("Drip", ["Standard Drip", "28mm Drip", "No Drip"])
            cill = tc2.selectbox("Cill", ["None", "30mm (Stub)", "85mm", "150mm", "180mm"])
            glass = tc3.selectbox("Glass", ["Double", "Triple", "Toughened", "Acoustic", "Obscure"])
            sas_count = st.number_input("Extra Sashes", 0, 10, 0)

        if st.button("💾 Save Window", use_container_width=True):
            p = get_p(w, h, sas_count, mat, job_m, vat_m)
            st.session_state.db[sel].append({"Room": room, "Mat": mat, "Size": f"{w}x{h}", "Drip": drip, "Price": p})
            st.rerun()

    with tab2:
        st.subheader(f"Project Breakdown")
        if st.session_state.db[sel]:
            df = pd.DataFrame(st.session_state.db[sel])
            st.table(df)
            total = sum(x['Price'] for x in st.session_state.db[sel])
            st.metric("GRAND TOTAL", f"€{total:,.2f}")
