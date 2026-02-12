import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Pro Survey", layout="centered")

# --- PRICING LOGIC (All your rules included) ---
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
    
    unit_cost = base + (sashes * 80)
    rep_fee = 0
    
    if material == "PVC Standard": unit_cost *= 0.55
    elif material == "Aluclad Standard": 
        if job_type == "Replacement": rep_fee = 325
    elif material == "PVC Sliding Sash":
        unit_cost = (unit_cost * 0.60) * 2
        if job_type == "Replacement": rep_fee = 438
    elif material == "Hardwood Sliding Sash":
        unit_cost = (unit_cost * 0.95) * 2.2
        if job_type == "Replacement": rep_fee = 480
    elif material == "Aluclad Sliding Sash":
        unit_cost = (unit_cost * 1.0) * 2.5
        if job_type == "Replacement": rep_fee = 480
    elif material == "Fireproof":
        unit_cost *= 0.55
        if job_type == "Replacement": rep_fee = 245

    final_ex = max(unit_cost, 300.0) + rep_fee
    return round(final_ex * 1.135, 2) if include_vat else round(final_ex, 2)

# --- DYNAMIC BOX GENERATOR ---
def create_frame_bg(w, h):
    side = 300
    bg = Image.new('RGB', (side, side), (255, 255, 255))
    draw = ImageDraw.Draw(bg)
    ratio = w / h
    if ratio > 1: bw, bh = 260, 260 / ratio
    else: bh, bw = 260, 260 * ratio
    x0, y0 = (side - bw) / 2, (side - bh) / 2
    draw.rectangle([x0, y0, x0 + bw, y0 + bh], outline="black", width=5)
    return bg

# --- SESSION STATE ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'sigs' not in st.session_state: st.session_state.sigs = {}
if 'view' not in st.session_state: st.session_state.view = "Survey"
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
if 'f_count' not in st.session_state: st.session_state.f_count = 0

# --- SIDEBAR ---
st.sidebar.title("📁 Site Management")
with st.sidebar.expander("➕ New Site"):
    n_site = st.text_input("Address")
    if st.button("Add Site"):
        if n_site: st.session_state.db[n_site] = []; st.rerun()

sel_site = st.sidebar.selectbox("Active Site", options=["None"] + list(st.session_state.db.keys()))

if sel_site != "None":
    job = st.sidebar.radio("Type", ["New Build", "Replacement"])
    vat = st.sidebar.toggle("Inc VAT", True)
    if st.sidebar.button("🛠 Survey"): st.session_state.view = "Survey"; st.rerun()
    if st.sidebar.button("📜 Quote"): st.session_state.view = "Quote"; st.rerun()

# --- MAIN APP ---
if sel_site != "None":
    if st.session_state.view == "Survey":
        e_idx = st.session_state.edit_idx
        is_e = e_idx is not None
        curr = st.session_state.db[sel_site][e_idx] if is_e else None
        
        st.title(f"{'Edit' if is_e else 'Add'} Window")
        with st.form(key=f"sf_{st.session_state.f_count}", clear_on_submit=True):
            room = st.text_input("Room", value=curr["Room"] if is_e else "")
            prod = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"], 
                               index=0 if not is_e else ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"].index(curr["Material"]))
            w = st.number_input("Width (mm)", value=int(curr["Size"].split('x')[0]) if is_e else 1200)
            h = st.number_input("Height (mm)", value=int(curr["Size"].split('x')[1]) if is_e else 1000)
            sas = st.number_input("Sashes", value=curr.get("Sashes", 0) if is_e else 0)
            
            # FRAME GENERATOR
            bg = create_frame_bg(w, h)
            st.write(f"**Draw Design in {w}x{h} frame:**")
            canvas = st_canvas(stroke_width=3, stroke_color="black", background_image=bg, height=300, width=300, key=f"c_{w}_{h}_{st.session_state.f_count}")

            if st.form_submit_button("Save Window"):
                p = get_pricing(w, h, sas, prod, job, vat)
                entry = {"Room": room, "Material": prod, "Size": f"{w}x{h}", "Sashes": sas, "Price": p, "Sketch": canvas.image_data}
                if is_e: st.session_state.db[sel_site][e_idx] = entry; st.session_state.edit_idx = None
                else: st.session_state.db[sel_site].append(entry)
                st.session_state.f_count += 1; st.rerun()

        for i, itm in enumerate(st.session_state.db[sel_site]):
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1: st.image(itm["Sketch"], width=100) if itm["Sketch"] is not None else None
                with c2:
                    st.write(f"**{itm['Room']}** - €{itm['Price']}")
                    if st.button("Edit", key=f"e_{i}"): st.session_state.edit_idx = i; st.rerun()
    
    elif st.session_state.view == "Quote":
        st.title(f"Quote: {sel_site}")
        items = st.session_state.db[sel_site]
        st.write(f"**Total: €{sum([x['Price'] for x in items]):,.2f}**")
        
        st.write("--- Client Signature ---")
        sig = st_canvas(stroke_width=2, stroke_color="black", height=150, width=400, key="sig")
        if st.button("Sign & Approve"): st.session_state.sigs[sel_site] = sig.image_data; st.success("Signed!")
