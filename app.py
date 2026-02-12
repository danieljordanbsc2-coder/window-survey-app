import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np
import io

# --- PRICING ENGINE ---
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
    elif mat == "PVC Sliding Sash": c = (u * 0.60) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (u * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = u * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = u * 0.55; f = 245 if job == "Replacement" else 0
    
    final = max(c, 300.0) + f
    return round(final * (1.135 if vat else 1), 2)

# --- FRAME GENERATOR ---
def mk_fr(w, h):
    img = Image.new('RGB', (300, 300), "white")
    d = ImageDraw.Draw(img)
    r = w/h
    bw, bh = (260, 260/r) if r > 1 else (260*r, 260)
    x, y = (300-bw)/2, (300-bh)/2
    d.rectangle([x, y, x+bw, y+bh], outline="black", width=12)
    return img

# --- SESSION SETUP ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'f_cnt' not in st.session_state: st.session_state.f_cnt = 0

st.sidebar.title("📁 Site Management")
job_m = st.sidebar.radio("Job Type", ["New Build", "Replacement"])
vat_m = st.sidebar.toggle("Include 13.5% VAT", True)
site_n = st.sidebar.text_input("New Address")
if st.sidebar.button("Create Folder"):
    if site_n: st.session_state.db[site_n] = []; st.rerun()

sel = st.sidebar.selectbox("Active Site", ["Select..."] + list(st.session_state.db.keys()))

if sel != "Select...":
    items = st.session_state.db[sel]
    # SITE DASHBOARD (Metric bar for efficiency)
    c1, c2 = st.columns(2)
    c1.metric("Units", len(items))
    c2.metric("Total Order", f"€{sum(x['Price'] for x in items):,.2f}")
    
    st.divider()
    
    # INPUT SECTION
    room = st.selectbox("Room", ["Kitchen", "Living", "Master Bed", "Bathroom", "Other"])
    prod = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
    
    col_w, col_h = st.columns(2)
    w = col_w.number_input("Width (mm)", 100, 4000, 1200)
    h = col_h.number_input("Height (mm)", 100, 4000, 1000)
    
    st.write("### ✏️ Draw Openings")
    st.caption("The black box below matches your exact size. Draw arrows (< or V) to show opening direction.")
    
    # KEY is tied to W/H to force the frame to update
    canvas = st_canvas(
        stroke_width=4, stroke_color="black", background_image=mk_fr(w, h),
        height=300, width=300, key=f"c_{w}_{h}_{st.session_state.f_cnt}"
    )
    
    sas = st.number_input("Extra Sashes", 0, 10, 0)
    col = st.selectbox("Colour", ["
                                
