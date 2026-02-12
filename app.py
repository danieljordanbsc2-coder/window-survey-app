import streamlit as st
import pandas as pd

# --- PRICING RULES ---
def get_p(w, h, sas, mat, job, vat):
    a = (w * h) / 1000000
    if a < 0.6: b = 698
    elif a < 0.8: b = 652
    elif a < 1.0: b = 501
    elif a < 1.2: b = 440
    elif a < 1.5: b = 400
    elif a < 2.0: b = 380
    elif a < 2.5: b = 344
    elif a < 3.0: b = 330
    elif a < 3.5: b = 316
    elif a < 4.0: b = 304
    elif a < 4.5: b = 291
    else: b = 277
    
    u = b + (sas * 80)
    c, f = 0, 0
    if mat == "PVC Standard": c = u * 0.55
    elif mat == "Aluclad Standard": c = u; f = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (u * 0.6) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (u * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = u * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = u * 0.55; f = 245 if job == "Replacement" else 0
    
    final = max(c, 300.0) + f
    return round(final * (1.135 if vat else 1), 2)

# --- AUTO-DRAWING ENGINE ---
def draw_win(w, h, mode):
    r = w / h
    bw = 260 if r > 1 else 260 * r
    bh = 260 if r < 1 else 260 / r
    x, y = (300 - bw)/2, (300 - bh)/2
    
    sym = ""
    if "Left" in mode:
        sym = f'<polyline points="{x+10},{y+bh/2} {x+bw-10},{y+10} {x+bw-10},{y+bh-10} {x+10},{y+bh/2}" fill="none" stroke="red" stroke-width="4"/>'
    elif "Right" in mode:
        sym = f'<polyline points="{x+bw-10},{y+bh/2} {x+10},{y+10} {x+10},{y+bh-10} {x+bw-10},{y+bh/2}" fill="none" stroke="red" stroke-width="4"/>'
    elif "Top" in mode:
        sym = f'<polyline points="{x+bw/2},{y+10} {x+10},{y+bh-10} {x+bw-10},{y+bh-10} {x+bw/2},{y+10}" fill="none" stroke="red" stroke-width="4"/>'
    
    svg = f'<svg width="300" height="300"><rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="#f8f9fa" stroke="black" stroke-width="10" />{sym}</svg>'
    st.write(f'<div style="display:flex;justify-content:center;">{svg}</div>', unsafe_allow_html=True)

# --- APP LAYOUT ---
if 'db' not in st.session_state: st.session_state.db = {}

st.sidebar.title("Survey Pro")
site_addr = st.sidebar.text_input("New Site Address")
if st.sidebar.button("Create Site"): st.session_state.db[site_addr] = []

sel = st.sidebar.selectbox("Active Project", ["Select..."] + list(st.session_state.db.keys()))

if sel != "Select...":
    job = st.sidebar.radio("Mode", ["New Build", "Replacement"])
    vat = st.sidebar.toggle("Inc VAT", True)
    items = st.session_state.db[sel]
    st.metric("Running Total", f"€{sum(i['Price'] for i in items):,.2f}", f"{len(items)} units")
    
    with st.expander("➕ Add Window", expanded=True):
        room = st.selectbox("Room", ["Kitchen", "Living", "Master Bed", "Ensuite", "Hall", "Other"])
        mat = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
        c1, c2 = st.columns(2)
        w = c1.number_input("Width (mm)", 100, 5000, 1200)
        h = c2.number_input("Height (mm)", 100, 5000, 1000)
        style = st.radio("Opening", ["Fixed", "Side (Left)", "Side (Right)", "Top Hung"], horizontal=True)
        draw_win(w, h, style)
        sas = st.number_input("Extra Sashes", 0, 10, 0)
        col = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"])
        
        if st.button("💾 Save Window", use_container_width=True):
            p = get_p(w, h, sas, mat, job, vat)
            st.session_state.db[sel].append({"Room": room, "Size": f"{w}x{h}", "Style": style, "Price": p})
            st.rerun()

    if items:
        st.divider()
        st.subheader("Window Schedule")
        st.dataframe(pd.DataFrame(items)[['Room', 'Size', 'Style', 'Price']], hide_index=True)
