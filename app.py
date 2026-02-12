import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np
import io

# --- PRICING ENGINE ---
def get_p(w, h, sas, mat, job, vat):
    area = (w * h) / 1000000
    # List Price Tiers [cite: 2026-02-10]
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
    # Discounts & Sash Multipliers [cite: 2026-02-11]
    if mat == "PVC Standard": c = unit_base * 0.55
    elif mat == "Aluclad Standard": c = unit_base; f = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (unit_base * 0.60) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (unit_base * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = unit_base * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = unit_base * 0.55; f = 245 if job == "Replacement" else 0
    
    # Calculation: Max of (Discounted Unit, €300 Floor) + Fitting Fee
    final = max(c, 300.0) + f
    return round(final * (1.135 if vat else 1), 2)

# --- PROPORTIONAL FRAME GENERATOR ---
def mk_fr(w, h):
    img = Image.new('RGB', (300, 300), "white")
    d = ImageDraw.Draw(img)
    r = w/h
    # Scale to fit a 300x300 canvas
    if r > 1: bw, bh = 260, 260/r
    else: bh, bw = 260, 260*r
    x, y = (300-bw)/2, (300-bh)/2
    # Draw Bold Frame
    d.rectangle([x, y, x+bw, y+bh], outline="black", width=12)
    return img

# --- SESSION SETUP ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'f_cnt' not in st.session_state: st.session_state.f_cnt = 0

st.sidebar.title("📁 Site Management")
job_m = st.sidebar.radio("Job Type", ["New Build", "Replacement"])
vat_m = st.sidebar.toggle("Inc 13.5% VAT", True)
site_n = st.sidebar.text_input("Site Name")
if st.sidebar.button("Create Site"):
    if site_n: st.session_state.db[site_n] = []; st.rerun()

sel = st.sidebar.selectbox("Active Site", ["Select..."] + list(st.session_state.db.keys()))

if sel != "Select...":
    items = st.session_state.db[sel]
    # RUNNING TOTAL (Top Dashboard)
    total_val = sum(x['Price'] for x in items)
    st.metric("Total Project Value", f"€{total_val:,.2f}", f"{len(items)} Units")
    
    st.divider()
    
    # SURVEY INPUTS
    room = st.selectbox("Room", ["Kitchen", "Living", "Master Bed", "Bathroom", "Other"])
    prod = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
    
    c_w, c_h = st.columns(2)
    w = c_w.number_input("Width (mm)", 100, 4000, 1200)
    h = c_h.number_input("Height (mm)", 100, 4000, 1000)
    
    # LIVE SKETCH PAD
    st.write(f"**Elevation: {w}x{h}** (Frame updates as you type)")
    canvas = st_canvas(
        stroke_width=4, stroke_color="black", background_image=mk_fr(w, h),
        height=300, width=300, key=f"c_{w}_{h}_{st.session_state.f_cnt}"
    )
    
    sas = st.number_input("Extra Openers", 0, 10, 0)
    col = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak"])
    
    if st.button("💾 Save Window"):
        p = get_p(w, h, sas, prod, job_m, vat_m)
        st.session_state.db[sel].append({
            "Room": room, "Mat": prod, "Size": f"{w}x{h}", "Price": p, "Sketch": canvas.image_data
        })
        st.session_state.f_cnt += 1
        st.rerun()

    # SAVED WINDOWS LIST
    st.divider()
    for i, itm in enumerate(st.session_state.db[sel]):
        with st.container(border=True):
            ci, ct, cb = st.columns([1, 2, 1])
            if itm["Sketch"] is not None: ci.image(itm["Sketch"], width=80)
            ct.write(f"**{itm['Room']}** - €{itm['Price']:,}")
            if cb.button("🗑", key=f"d_{i}"):
                st.session_state.db[sel].pop(i)
                st.rerun()
