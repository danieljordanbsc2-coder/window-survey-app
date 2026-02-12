import streamlit as st
import pandas as pd

# --- PRICING ENGINE (Your Exact Rules) ---
def get_p(w, h, sas, mat, job, vat):
    area = (w * h) / 1000000
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
    
    u = b + (sas * 80)
    c, f = 0, 0
    if mat == "PVC Standard": c = u * 0.55
    elif mat == "Aluclad Standard": c = u; f = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (u * 0.60) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (u * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = u * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = u * 0.55; f = 245 if job == "Replacement" else 0
    
    final = max(c, 300.0) + f
    return round(final * (1.135 if vat else 1), 2)

# --- AUTO-WINDOW RENDERER ---
def draw_window(w, h, style):
    r = w / h
    width = 250 if r > 1 else 250 * r
    height = 250 if r < 1 else 250 / r
    
    # Opening Symbols
    overlay = ""
    if style == "Side Hung (Left)": overlay = f'<polyline points="10,{height/2} {width-10},10 {width-10},{height-10} 10,{height/2}" fill="none" stroke="red" stroke-width="4"/>'
    elif style == "Top Hung": overlay = f'<polyline points="{width/2},10 10,{height-10} {width-10},{height-10} {width/2},10" fill="none" stroke="red" stroke-width="4"/>'
    
    svg = f"""
    <svg width="300" height="300" viewBox="-25 -25 350 350">
        <rect x="0" y="0" width="{width}" height="{height}" fill="#f0f8ff" stroke="black" stroke-width="8" />
        {overlay}
        <text x="{width/2}" y="{height + 30}" text-anchor="middle" font-family="Arial" font-weight="bold">{w} x {h}</text>
    </svg>
    """
    st.write(f'<div style="display:flex;justify-content:center;">{svg}</div>', unsafe_allow_html=True)

# --- SESSION SETUP ---
if 'db' not in st.session_state: st.session_state.db = {}

st.sidebar.title("📁 Site Manager")
site = st.sidebar.text_input("Site Address")
if st.sidebar.button("Create Site"): st.session_state.db[site] = []
sel = st.sidebar.selectbox("Active Folder", ["Select..."] + list(st.session_state.db.keys()))

if sel != "Select...":
    job = st.sidebar.radio("Job", ["New Build", "Replacement"])
    vat = st.sidebar.toggle("Inc VAT", True)
    
    st.title(f"Survey: {sel}")
    
    # 1. Inputs
    room = st.selectbox("Room", ["Kitchen", "Living", "Master Bed", "Bathroom", "Hall"])
    prod = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
    
    c1, c2 = st.columns(2)
    w = c1.number_input("Width (mm)", 100, 4000, 1200)
    h = c2.number_input("Height (mm)", 100, 4000, 1000)
    
    # 2. Tap to Choose Opening (Efficiency Hack)
    style = st.radio("Opening Type", ["Fixed", "Side Hung (Left)", "Top Hung"], horizontal=True)
    
    # 3. Visual Preview
    st.write("### Preview")
    draw_window(w, h, style)
    
    sas = st.number_input("Extra Openers", 0, 10, 0)
    col = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak"])
    
    if st.button("💾 Save Window", use_container_width=True):
        price = get_p(w, h, sas, prod, job, vat)
        st.session_state.db[sel].append({"Room": room, "Size": f"{w}x{h}", "Style": style, "Price": price})
        st.success(f"Saved! Unit Price: €{price}")

    # 4. Summary Table
    st.divider()
    if st.session_state.db[sel]:
        df = pd.DataFrame(st.session_state.db[sel])
        st.table(df)
        st.metric("Total Quote", f"€{df['Price'].sum():,.2f}")
