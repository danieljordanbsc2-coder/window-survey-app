import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Window Survey Pro", layout="centered")

# --- PRICING LOGIC ---
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
    
    window_unit = base + (sashes * 80)
    replacement_fee = 0
    
    if material == "PVC Standard":
        window_unit *= 0.55
    elif material == "Aluclad Standard":
        window_unit *= 1.0
        if job_type == "Replacement": replacement_fee = 325
    elif material == "PVC Sliding Sash":
        window_unit = (window_unit * 0.60) * 2
        if job_type == "Replacement": replacement_fee = 438
    elif material == "Hardwood Sliding Sash":
        window_unit = (window_unit * 0.95) * 2.2
        if job_type == "Replacement": replacement_fee = 480
    elif material == "Aluclad Sliding Sash":
        window_unit = (window_unit * 1.0) * 2.5
        if job_type == "Replacement": replacement_fee = 480
    elif material == "Fireproof":
        window_unit *= 0.55
        if job_type == "Replacement": replacement_fee = 245

    final_ex_vat = max(window_unit, 300.0) + replacement_fee
    return round(final_ex_vat * 1.135, 2) if include_vat else round(final_ex_vat, 2)

# --- FRAME GENERATOR ---
def create_frame_bg(w, h):
    side = 300
    bg = Image.new('RGB', (side, side), (255, 255, 255))
    draw = ImageDraw.Draw(bg)
    ratio = w / h
    if ratio > 1: box_w = 260; box_h = 260 / ratio
    else: box_h = 260; box_w = 260 * ratio
    x0 = (side - box_w) / 2; y0 = (side - box_h) / 2
    draw.rectangle([x0, y0, x0 + box_w, y0 + box_h], outline="black", width=4)
    return bg

# --- SESSION STATE ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'signatures' not in st.session_state: st.session_state.signatures = {}
if 'edit_index' not in st.session_state: st.session_state.edit_index = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = "Survey"
if 'form_count' not in st.session_state: st.session_state.form_count = 0

# --- SIDEBAR: SITE MANAGEMENT ---
st.sidebar.title("📁 Site Management")

# 1. Option to create a new site
with st.sidebar.expander("➕ Add New Site", expanded=len(st.session_state.db) == 0):
    new_addr = st.text_input("Site Address / Name")
    if st.button("Create Site Folder"):
        if new_addr and new_addr not in st.session_state.db:
            st.session_state.db[new_addr] = []
            st.sidebar.success(f"Created: {new_addr}")
            st.rerun()

# 2. Dropdown to select existing site
site_list = list(st.session_state.db.keys())
selected_client = st.sidebar.selectbox("Open Site Folder", options=["Select a site..."] + site_list)

# --- MAIN CONTENT ---
if selected_client != "Select a site...":
    st.sidebar.divider()
    job_type = st.sidebar.radio("Job Type", ["New Build", "Replacement"])
    vat_mode = st.sidebar.toggle("Include 13.5% VAT", value=True)
    
    col_nav1, col_nav2 = st.sidebar.columns(2)
    if col_nav1.button("🛠 Survey"): st.session_state.view_mode = "Survey"; st.rerun()
    if col_nav2.button("📜 Quote"): st.session_state.view_mode = "Quote"; st.rerun()

    if st.session_state.view_mode == "Survey":
        edit_idx = st.session_state.edit_index
        is_editing = edit_idx is not None
        curr = st.session_state.db[selected_client][edit_idx] if is_editing else None

        st.title(f"{'✏️ Edit Window' if is_editing else '📋 Site Survey'}")
        st.caption(f"Address: {selected_client}")
        
        with st.form(key=f"survey_form_{st.session_state.form_count}", clear_on_submit=True):
            room = st.text_input("Room (e.g. Kitchen)", value=curr["Room"] if is_editing else "")
            prod = st.selectbox("Product Type", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"], 
                               index=0 if not is_editing else ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"].index(curr["Material"]))
            
            c_w, c_h = st.columns(2)
            with c_w: w = st.number_input("Width (mm)", value=int(curr["Size"].split('x')[0]) if is_editing else 1200)
            with c_h: h = st.number_input("Height (mm)", value=int(curr["Size"].split('x')[1]) if is_editing else 1000)
            
            c_s, c_g, c_c = st.columns(3)
            with c_s: sashes = st.number_input("Openers", value=curr.get("Sashes", 0) if is_editing else 0)
            with c_g: glazing = st.selectbox("Glazing", ["Double", "Triple"], index=0 if not is_editing else ["Double", "Triple"].index(curr.get("Glazing", "Double")))
            with c_c: color = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"], index=0 if not is_editing else ["White", "Anthracite", "Black", "Oak", "Cream"].index(curr.get("Colour", "White")))
            
            st.write(f"**Sketch Design:**")
            frame_bg = create_frame_bg(w, h)
            canvas = st_canvas(stroke_width=3, stroke_color="#000000", background_image=frame_bg, height=300, width=300, drawing_mode="freedraw", key=f"canv_{w}_{h}_{st.session_state.form_count}")

            if st.form_submit_button("Save Window Details"):
                price = get_pricing(w, h, sashes, prod, job_type, vat_mode)
                entry = {"Room": room, "Material": prod, "Design": prod.split()[-1], "Size": f"{w}x{h}", "Sashes": sashes, "Glazing": glazing, "Colour": color, "Price": price, "Sketch": canvas.image_data}
                if is_editing:
                    st.session_state.db[selected_client][edit_idx] = entry
                    st.session_state.edit_index = None
                else:
                    st.session_state.db[selected_client].append(entry)
                st.session_state.form_count += 1
                st.rerun()

        # Display list of windows
        st.divider()
        for i, item in enumerate(st.session_state.db[selected_client]):
            with st.container(border=True):
                c_img, c_txt, c_btn = st.columns([1, 2, 1])
                with c_img:
                    if item["
