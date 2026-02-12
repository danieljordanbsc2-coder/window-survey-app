import streamlit as st
import pandas as pd

# --- PRICING ENGINE ---
def get_p(w, h, sas, mat, job, vat):
    area = (w * h) / 1e6
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
    elif mat == "PVC Sliding Sash": c = (u * 0.6) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (u * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = u * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = u * 0.55; f = 245 if job == "Replacement" else 0
    
    return round((max(c, 300.0) + f) * (1.135 if vat else 1), 2)

# --- PRO-SPEC SVG RENDERER ---
def draw_pro_win(w, h, layout, op1, op2, op3):
    r = w / h
    bw = 260 if r > 1 else 260 * r
    bh = 260 if r < 1 else 260 / r
    x, y = (300 - bw)/2, (300 - bh)/2
    
    def get_sym(pane_x, pane_y, pane_w, pane_h, style):
        if "Left" in style: return f'<polyline points="{pane_x+5},{pane_y+pane_h/2} {pane_x+pane_w-5},{pane_y+5} {pane_x+pane_w-5},{pane_y+pane_h-5} {pane_x+5},{pane_y+pane_h/2}" fill="none" stroke="red" stroke-width="2"/>'
        if "Right" in style: return f'<polyline points="{pane_x+pane_w-5},{pane_y+pane_h/2} {pane_x+5},{pane_y+5} {pane_x+5},{pane_y+pane_h-5} {pane_x+pane_w-5},{pane_y+pane_h/2}" fill="none" stroke="red" stroke-width="2"/>'
        if "Top" in style: return f'<polyline points="{pane_x+pane_w/2},{pane_y+5} {pane_x+5},{pane_y+pane_h-5} {pane_x+pane_w-5},{pane_y+pane_h-5} {pane_x+pane_w/2},{pane_y+5}" fill="none" stroke="red" stroke-width="2"/>'
        return ""

    panes = ""
    if layout == "Single":
        panes += f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="#f8f9fa" stroke="black" stroke-width="6"/>'
        panes += get_sym(x, y, bw, bh, op1)
    elif layout == "Double Split":
        panes += f'<rect x="{x}" y="{y}" width="{bw/2}" height="{bh}" fill="#f8f9fa" stroke="black" stroke-width="6"/>'
        panes += f'<rect x="{x+bw/2}" y="{y}" width="{bw/2}" height="{bh}" fill="#f8f9fa" stroke="black" stroke-width="6"/>'
        panes += get_sym(x, y, bw/2, bh, op1)
        panes += get_sym(x+bw/2, y, bw/2, bh, op2)
    elif layout == "Triple Split":
        panes += f'<rect x="{x}" y="{y}" width="{bw/3}" height="{bh}" fill="#f8f9fa" stroke="black" stroke-width="6"/>'
        panes += f'<rect x="{x+bw/3}" y="{y}" width="{bw/3}" height="{bh}" fill="#f8f9fa" stroke="black" stroke-width="6"/>'
        panes += f'<rect x="{x+2*bw/3}" y="{y}" width="{bw/3}" height="{bh}" fill="#f8f9fa" stroke="black" stroke-width="6"/>'
        panes += get_sym(x, y, bw/3, bh, op1)
        panes += get_sym(x+bw/3, y, bw/3, bh, op2)
        panes += get_sym(x+2*bw/3, y, bw/3, bh, op3)
    elif layout == "Top Fanlight":
        panes += f'<rect x="{x}" y="{y}" width="{bw}" height="{bh*0.3}" fill="#f8f9fa" stroke="black" stroke-width="6"/>'
        panes += f'<rect x="{x}" y="{y+bh*0.3}" width="{bw}" height="{bh*0.7}" fill="#f8f9fa" stroke="black" stroke-width="6"/>'
        panes += get_sym(x, y, bw, bh*0.3, op1)
        panes += get_sym(x, y+bh*0.3, bw, bh*0.7, op2)

    svg = f'<svg width="300" height="300">{panes}</svg>'
    st.write(f'<div style="display:flex;justify-content:center;">{svg}</div>', unsafe_allow_html=True)

# --- APP SETUP ---
if 'db' not in st.session_state: st.session_state.db = {}

st.sidebar.title("Survey Pro 2.0")
site_addr = st.sidebar.text_input("Site Address")
if st.sidebar.button("Create Site"): st.session_state.db[site_addr] = []

sel = st.sidebar.selectbox("Active Project", ["Select..."] + list(st.session_state.db.keys()))

if sel != "Select...":
    job = st.sidebar.radio("Job Mode", ["New Build", "Replacement"])
    vat = st.sidebar.toggle("Inc 13.5% VAT", True)
    
    st.header(f"Site: {sel}")
    
    with st.expander("➕ Configure Window", expanded=True):
        room = st.selectbox("Room", ["Kitchen", "Living", "Master Bed", "Ensuite", "Hall", "Other"])
        mat = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
        
        c1, c2 = st.columns(2)
        w = c1.number_input("Width (mm)", 100, 5000, 1200)
        h = c2.number_input("Height (mm)", 100, 4000, 1000)
        
        lay = st.selectbox("Window Layout", ["Single", "Double Split", "Triple Split", "Top Fanlight"])
        
        o1, o2, o3 = "Fixed", "Fixed", "Fixed"
        if lay == "Single":
            o1 = st.selectbox("Opening", ["Fixed", "Side Left", "Side Right", "Top Hung"])
        elif lay == "Double Split":
            col1, col2 = st.columns(2)
            o1 = col1.selectbox("Left Pane", ["Fixed", "Side Left", "Side Right", "Top Hung"])
            o2 = col2.selectbox("Right Pane", ["Fixed", "Side Left", "Side Right", "Top Hung"])
        elif lay == "Triple Split":
            col1, col2, col3 = st.columns(3)
            o1 = col1.selectbox("Left", ["Fixed", "Side Left", "Top Hung"])
            o2 = col2.selectbox("Mid", ["Fixed", "Side Left", "Top Hung"])
            o3 = col3.selectbox("Right", ["Fixed", "Side Right", "Top Hung"])
        elif lay == "Top Fanlight":
            col1, col2 = st.columns(2)
            o1 = col1.selectbox("Top Pane", ["Fixed", "Top Hung"])
            o2 = col2.selectbox("Bottom Pane", ["Fixed", "Side Left", "Side Right"])

        draw_pro_win(w, h, lay, o1, o2, o3)
        
        col = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"])
        
        if st.button("💾 Save Window", use_container_width=True):
            sas = sum(1 for o in [o1, o2, o3] if o != "Fixed")
            p = get_p(w, h, sas, mat, job, vat)
            st.session_state.db[sel].append({"Room": room, "Size": f"{w}x{h}", "Layout": lay, "Price": p})
            st.rerun()

    if st.session_state.db[sel]:
        st.divider()
        st.subheader("Window Schedule")
        df = pd.DataFrame(st.session_state.db[sel])
        st.dataframe(df, hide_index=True)
        st.metric("Total Quote", f"€{df['Price'].sum():,.2f}")
