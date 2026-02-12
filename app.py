import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np
import io

# --- PRICING ENGINE ---
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
    
    unit_base = b + (sas * 80)
    c, fee = 0, 0
    if mat == "PVC Standard": c = unit_base * 0.55
    elif mat == "Aluclad Standard": c = unit_base; fee = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (unit_base * 0.60) * 2; fee = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (unit_base * 0.95) * 2.2; fee = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = unit_base * 2.5; fee = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = unit_base * 0.55; fee = 245 if job == "Replacement" else 0
    
    final = max(c, 300.0) + fee
    return round(final * (1.135 if vat else 1), 2)

# --- THE FRAME BUILDER ---
def mk_fr(w, h):
    img = Image.new('RGB', (300, 300), (255, 255, 255))
    d = ImageDraw.Draw(img)
    r = w/h
    # Scale within 300x300 pad
    if r > 1: bw, bh = 260, 260/r
    else: bh, bw = 260, 260*r
    x, y = (300-bw)/2, (300-bh)/2
    # Draw grey guide frame so your black pen stands out
    d.rectangle([x, y, x+bw, y+bh], outline="#D3D3D3", width=12)
    return img

# --- APP SETUP ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'f_cnt' not in st.session_state: st.session_state.f_cnt = 0

st.sidebar.title("📁 Site Management")
job_mode = st.sidebar.radio("Job Type", ["New Build", "Replacement"])
vat_mode = st.sidebar.toggle("Include 13.5% VAT", True)
site_n = st.sidebar.text_input("New Site Name")
if st.sidebar.button("Create Site"):
    if site_n: st.session_state.db[site_n] = []; st.rerun()

sel = st.sidebar.selectbox("Active Site", ["Select..."] + list(st.session_state.db.keys()))

if sel != "Select...":
    st.title(f"Survey: {sel}")
    
    with st.container(border=True):
        room = st.selectbox("Room", ["Kitchen", "Living Room", "Master Bed", "Bathroom", "Other"])
        prod = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
        
        c1, c2 = st.columns(2)
        with c1: w = st.number_input("Width (mm)", 100, 4000, 1200, 10)
        with c2: h = st.number_input("Height (mm)", 100, 4000, 1000, 10)
        
        st.write("### Design Openings")
        st.caption("Draw the opening arrows (< or V) inside the frame below:")
        
        # The key forces the canvas to redraw when W or H changes
        canvas = st_canvas(
            stroke_width=4,
            stroke_color="#000000",
            background_image=mk_fr(w, h),
            height=300,
            width=300,
            drawing_mode="freedraw",
            key=f"canv_{w}_{h}_{st.session_state.f_cnt}"
        )
        
        sas = st.number_input("Extra Openers", 0, 10, 0)
        col = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak"])
        
        if st.button("💾 Save Window", use_container_width=True):
            price = get_p(w, h, sas, prod, job_mode, vat_mode)
            st.session_state.db[sel].append({
                "Room": room, "Prod": prod, "Size": f"{w}x{h}", 
                "Price": price, "Col": col, "Sketch": canvas.image_data
            })
            st.session_state.f_cnt += 1
            st.rerun()

    # SITE SUMMARY
    st.divider()
    for i, itm in enumerate(st.session_state.db[sel]):
        with st.container(border=True):
            c_img, c_txt, c_btn = st.columns([1, 2, 1])
            with c_img:
                if itm["Sketch"] is not None:
                    st.image(itm["Sketch"], width=100)
            with c_txt:
                st.write(f"**{itm['Room']}** ({itm['Size']})")
                st.caption(f"€{itm['Price']:,} - {itm['Prod']}")
            with c_btn:
                if st.button("🗑", key=f"del_{i}"):
                    st.session_state.db[sel].pop(i)
                    st.rerun()
