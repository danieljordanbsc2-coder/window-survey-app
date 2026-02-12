import streamlit as st
import pandas as pd

# --- PRICING ENGINE (Locked to your 2026 Rules) ---
def get_p(w, h, sas, mat, job, vat):
    area = (w * h) / 1000000
    # Tiered Pricing [cite: 2026-02-10]
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
    # Material & Replacement Logic [cite: 2026-02-11]
    if mat == "PVC Standard": c = unit_base * 0.55
    elif mat == "Aluclad Standard": c = unit_base; f = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (unit_base * 0.6) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (unit_base * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = unit_base * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = unit_base * 0.55; f = 245 if job == "Replacement" else 0
    
    final = max(c, 300.0) + f
    return round(final * (1.135 if vat else 1), 2)

# --- AUTO-DRAWING ENGINE ---
def draw_window_svg(w, h, mode):
    ratio = w / h
    box_w = 260 if ratio > 1 else 260 * ratio
    box_h = 260 if ratio < 1 else 260 / ratio
    x, y = (300 - box_w)/2, (300 - box_h)/2
    
    # Opening Symbol Logic
    symbol = ""
    if mode == "Side Hung (Left)":
        symbol = f'<polyline points="{x+10},{y+box_h/2} {x+box_w-10},{y+10} {x+box_w-10},{y+box_h-10} {x+10},{y+box_h/2}" fill="none" stroke="red" stroke-width="4"/>'
    elif mode == "Side Hung (Right)":
        symbol = f'<polyline points="{x+box_w-10},{y+box_h/2} {x+10},{y+10} {x+10},{y+box_h-10} {x+box_w-10},{y+box_h/2}" fill="none" stroke="red" stroke-width="4"/>'
    elif mode == "Top Hung":
        symbol = f'<polyline points="{x+box_w/2},{y+10} {x+10},{y+box_h-10} {x+box_w-10},{y+box_h-10} {x+box_w/2},{y+10}" fill="none" stroke="red" stroke-width="4"/>'
    
    svg = f"""
    <svg width="300" height="300" viewBox="0 0 300 300">
        <rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" fill="#f8f9fa" stroke="black" stroke-width="10" />
        {symbol}
    </svg>
    """
    st.write(f'<div style="display:flex;justify-content:center;">{svg}</div>', unsafe_allow_html=True)

# --- APP LAYOUT ---
if 'db' not in st.session_state: st.session_state.db = {}

st.sidebar.title("Survey Settings")
job_type = st.sidebar.radio("Job Mode", ["New Build", "Replacement"])
vat_inc = st.sidebar.toggle("Include 13.5% VAT", True)
site_addr = st.sidebar.text_input("New Site Address")
if st.sidebar.button("Create Site"): st.session_state.db[site_addr] = []

sel_site = st.sidebar.selectbox("Active Project", ["Select..."] + list(st.session_state.db.keys()))

if sel_site != "Select...":
    st.title(f"Project: {sel_site}")
    
    # Live Total Metric
    total = sum(item['Price'] for item in st.session_state.db[sel_site])
    st.metric("Running Total", f"€{total:,.2f}", f"{len(st.session_state.db[sel_site])} units")
    
    with st.expander("➕ Add Window", expanded=True):
        room = st.selectbox("Room", ["Kitchen", "Living", "Dining", "Master Bed", "Ensuite", "Hall", "Other"])
        mat = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
        
        c1, c2 = st.columns(2)
        w = c1.number_input("Width (mm)", 100, 5000, 1200)
        h = c2.number_input("Height (mm)", 100, 5000, 1000)
        
        # Tap-to-apply style
        style = st.pills("Opening Style", ["Fixed", "Side Hung (Left)", "Side Hung (Right)", "Top Hung"], default="Fixed")
        
        # Visual Preview
        draw_window_svg(w, h, style)
        
        sas = st.number_input("Extra Openers", 0, 10, 0)
        col = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"])
        
        if st.button("💾 Save to Site", use_container_width=True):
            price = get_p(w, h, sas, mat, job_type, vat_inc)
            st.session_state.db[sel_site].append({
                "Room": room, "Type": mat, "Size": f"{w}x{h}", "Style": style, "Price": price, "Color": col
            })
            st.rerun()

    # Site Summary
    if st.session_state.db[sel_site]:
        st.divider()
        st.subheader("Window Schedule")
        df = pd.DataFrame(st.session_state.db[sel_site])
        st.dataframe(df[['Room', 'Type', 'Size', 'Style', 'Price']], hide_index=True, use_container_width=True)
