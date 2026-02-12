import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np
import io

# --- PRICING ENGINE ---
def get_p(w, h, sas, mat, job, vat):
    # Calculate Area in Square Meters
    area = (w * h) / 1000000
    
    # Pricing Tiers [cite: 2026-02-10]
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
    else: b = 277 # Over 4.5m2
    
    unit_base = b + (sas * 80)
    c, f = 0, 0
    
    # Logic [cite: 2026-02-11]
    if mat == "PVC Standard": 
        c = unit_base * 0.55
    elif mat == "Aluclad Standard": 
        c = unit_base
        f = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": 
        c = (unit_base * 0.60) * 2
        f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": 
        c = (unit_base * 0.95) * 2.2
        f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": 
        c = unit_base * 2.5
        f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": 
        c = unit_base * 0.55
        f = 245 if job == "Replacement" else 0
        
    final = max(c, 300.0) + f
    return round(final * (1.135 if vat else 1), 2)

# --- FRAME GENERATOR ---
def mk_fr(w, h):
    img = Image.new('RGB', (300, 300), "white")
    d = ImageDraw.Draw(img)
    r = w/h
    if r > 1: bw, bh = 260, 260/r
    else: bh, bw = 260, 260*r
    x, y = (300-bw)/2, (300-bh)/2
    d.rectangle([x, y, x+bw, y+bh], outline="black", width=15) # Bold Frame
    return img

# --- SESSION STATE ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'view' not in st.session_state: st.session_state.view = "S"
if 'f_cnt' not in st.session_state: st.session_state.f_cnt = 0

# --- SIDEBAR ---
st.sidebar.title("📁 Site Management")
site_n = st.sidebar.text_input("New Site Address")
if st.sidebar.button("Create Folder"):
    if site_n: st.session_state.db[site_n] = []; st.rerun()

sel = st.sidebar.selectbox("Active Site", ["Select..."] + list(st.session_state.db.keys()))

if sel != "Select...":
    job = st.sidebar.radio("Job Type", ["New Build", "Replacement"])
    vat = st.sidebar.toggle("Include 13.5% VAT", True)
    if st.sidebar.button("🛠 Survey"): st.session_state.view = "S"; st.rerun()
    if st.sidebar.button("📜 Quote"): st.session_state.view = "Q"; st.rerun()

# --- MAIN APP ---
if sel != "Select...":
    if st.session_state.view == "S":
        st.title(f"Survey: {sel}")
        
        # Dimensions
        room = st.text_input("Room Name")
        prod = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
        
        c1, c2 = st.columns(2)
        with c1: w = st.number_input("Width (mm)", value=1200, step=10)
        with c2: h = st.number_input("Height (mm)", value=1000, step=10)
        
        # Frame Preview
        st.write(f"**Elevation Guide ({w}x{h}):**")
        
        # KEY CHANGE FORCING REFRESH
        canvas = st_canvas(
            stroke_width=4, stroke_color="black", 
            background_image=mk_fr(w, h), 
            height=300, width=300, 
            key=f"canv_{w}_{h}_{st.session_state.f_cnt}"
        )
        
        sas = st.number_input("Extra Openers", value=0)
        col = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"])
        
        if st.button("Save Window"):
            price = get_p(w, h, sas, prod, job, vat)
            st.session_state.db[sel].append({
                "Room": room, "Material": prod, "Size": f"{w}x{h}", "Price": price, "Sketch": canvas.image_data
            })
            st.session_state.f_cnt += 1
            st.success(f"Saved! Unit Price: €{price}")
            st.rerun()

        # Site List
        st.divider()
        for i, itm in enumerate(st.session_state.db[sel]):
            with st.container(border=True):
                st.write(f"**{itm['Room']}** | {itm['Size']} | €{itm['Price']}")
                if st.button("🗑", key=f"del_{i}"):
                    st.session_state.db[sel].pop(i)
                    st.rerun()
    
    elif st.session_state.view == "Q":
        st.title("Quote Summary")
        total = sum([x['Price'] for x in st.session_state.db[sel]])
        st.header(f"Total: €{total:,.2f}")
