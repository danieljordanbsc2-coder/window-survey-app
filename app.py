import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np
import io

st.set_page_config(page_title="Pro Survey", layout="centered")

def get_pricing(w, h, sashes, material, job_type, include_vat):
    area = (w * h) / 1000000
    if area < 0.6: base = 698
    elif area < 0.8: base = 652
    elif area < 1.0: base = 501
    elif area < 1.2: base = 440
    elif area < 1.5: base = 400
    elif area < 2.0: base = 380
    elif area < 2.5: base = 344
    elif area < 3.0: base = 330
    elif area < 3.5: base = 316
    elif area < 4.0: base = 304
    elif area < 4.5: base = 291
    else: base = 277
    
    unit_ex = base + (sashes * 80)
    cost, fee = 0, 0
    if material == "PVC Standard": cost = unit_ex * 0.55
    elif material == "Aluclad Standard": 
        cost = unit_ex
        if job_type == "Replacement": fee = 325
    elif material == "PVC Sliding Sash":
        cost = (unit_ex * 0.60) * 2
        if job_type == "Replacement": fee = 438
    elif material == "Hardwood Sliding Sash":
        cost = (unit_ex * 0.95) * 2.2
        if job_type == "Replacement": fee = 480
    elif material == "Aluclad Sliding Sash":
        cost = (unit_ex * 1.0) * 2.5
        if job_type == "Replacement": fee = 480
    elif material == "Fireproof":
        cost = unit_ex * 0.55
        if job_type == "Replacement": fee = 245
    
    final = max(cost, 300.0) + fee
    return round(final * 1.135, 2) if include_vat else round(final, 2)

def create_frame(w, h):
    bg = Image.new('RGB', (300, 300), (255, 255, 255))
    draw = ImageDraw.Draw(bg)
    r = w / h
    bw, bh = (260, 260/r) if r > 1 else (260*r, 260)
    x, y = (300-bw)/2, (300-bh)/2
    draw.rectangle([x, y, x+bw, y+bh], outline="black", width=10)
    return bg

if 'db' not in st.session_state: st.session_state.db = {}
if 'sigs' not in st.session_state: st.session_state.sigs = {}
if 'view' not in st.session_state: st.session_state.view = "Survey"
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
if 'f_count' not in st.session_state: st.session_state.f_count = 0

st.sidebar.title("📁 Site Folders")
with st.sidebar.expander("➕ Add Site"):
    sn = st.text_input("Address")
    if st.button("Create"):
        if sn: st.session_state.db[sn] = []; st.rerun()

sel = st.sidebar.selectbox("Active Site", options=["Select..."] + list(st.session_state.db.keys()))

if sel != "Select...":
    job = st.sidebar.radio("Job", ["New Build", "Replacement"])
    vat = st.sidebar.toggle("Inc VAT", True)
    if st.sidebar.button("🛠 Survey"): st.session_state.view = "Survey"; st.rerun()
    if st.sidebar.button("📜 Quote"): st.session_state.view = "Quote"; st.rerun()

    if st.session_state.view == "Survey":
        idx = st.session_state.edit_idx
        is_e = idx is not None
        curr = st.session_state.db[sel][idx] if is_e else None
        st.title(f"{'Edit' if is_e else 'Survey'}")
        
        room = st.text_input("Room", value=curr["Room"] if is_e else "")
        prod = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"], 
                           index=0 if not is_e else ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"].index(curr["Material"]))
        w = st.number_input("Width (mm)", value=int(curr["Size"].split('x')[0]) if is_e else 1200)
        h = st.number_input("Height (mm)", value=int(curr["Size"].split('x')[1]) if is_e else 1000)
        
        st.write(f"**Sketch Design:**")
        canvas = st_canvas(stroke_width=3, stroke_color="black", background_image=create_frame
