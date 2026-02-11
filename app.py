import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Window Survey Pro", layout="wide")

# --- PRICING LOGIC ---
def get_pricing(w, h, sashes, include_vat):
    area = (w * h) / 1000000
    # [cite: 2026-02-10] Tiers
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
    
    unit_ex_vat = base + (sashes * 80)
    return round(unit_ex_vat * 1.135, 2) if include_vat else round(unit_ex_vat, 2)

# --- IMAGE GENERATION LOGIC (FIXED) ---
def create_verification_image(client_name, data):
    block_height = 400
    total_height = (block_height * len(data)) + 150
    canvas_width = 800
    
    # Create white background
    img = Image.new('RGB', (canvas_width, total_height), color='white')
    
    y_offset = 120
    for item in data:
        if item["Sketch"] is not None:
            # FIX: Convert the sketch data from the canvas into a real image
            # We use numpy to handle the raw pixel data from the canvas
            sketch_array = np.array(item["Sketch"]).astype('uint8')
            sketch_img = Image.fromarray(sketch_array)
            
            # Convert to RGB (removes transparency which causes errors)
            sketch_img = sketch_img.convert("RGB")
            sketch_img.thumbnail((350, 350))
            img.paste(sketch_img, (30, y_offset))
        
        y_offset += block_height
    return img

# --- DATABASE & SESSION STATE ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'form_count' not in st.session_state: st.session_state.form_count = 0
if 'view_mode' not in st.session_state: st.session_state.view_mode = "Survey"

# --- SIDEBAR: CLIENT DIRECTORY ---
st.sidebar.title("📁 Client Folders")
new_client_name = st.sidebar.text_input("New Client Name/Address")
if st.sidebar.button("Add New Client"):
    if new_client_name and new_client_name not in st.session_state.db:
        st.session_state.db[new_client_name] = []

selected_client = st.sidebar.selectbox("Select Client", options=list(st.session_state.db.keys()))

if selected_client:
    st.sidebar.divider()
    if st.sidebar.button("🛠 Survey Mode"): st.session_state.view_mode = "Survey"
    if st.sidebar.button("📜 Quote Mode"): st.session_state.view_mode = "Quote"
    
    st.sidebar.divider()
    job_type = st.sidebar.radio("Job Type", ["New Build", "Replacement"])
    vat_mode = st.sidebar.toggle("Include 13.5% VAT", value=True)

# --- MAIN SCREEN ---
if selected_client:
    if st.session_state.view_mode == "Survey":
        st.title(f"Surveying: {selected_client}")
        
        with st.form(key=f"f_{st.session_state.form_count}", clear_on_submit=True):
            col_data, col_draw = st.columns([1, 1])
            with col_data:
                room = st.text_input("Room")
                design = st.selectbox("Style", ["Casement", "Fixed", "T&T", "French", "Bifold"])
                w = st.number_input("Width (mm)", value=1200)
                h = st.number_input("Height (mm)", value=1000)
                sashes = st.number_input("Extra Openers", min_value=0)
                color = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak"])
            
            with col_draw:
                st.write("**Sketch Elevation**")
                canvas_result = st_canvas(
                    stroke_width=3, stroke_color="#000000", background_color="#ffffff",
                    height=350, width=350, drawing_mode="freedraw", key=f"c_{st.session_state.form_count}"
                )

            if st.form_submit_button("Save & Clear"):
                price = get_pricing(w, h, sashes, vat_mode)
                st.session_state.db[selected_client].append({
                    "Room": room, "Design": design, "Size": f"{w}x{h}",
                    "Colour": color, "Price": price, "Sketch": canvas_result.image_data
                })
                st.session_state.form_count += 1
                st.rerun()

    else:
        st.title(f"Quote: {selected_client}")
        if st.session_state.db[selected_client]:
            if st.button("Generate Sendable Image"):
                final_img = create_verification_image(selected_client, st.session_state.db[selected_client])
                buf = io.BytesIO()
                final_img.save(buf, format="JPEG")
                st.image(buf.getvalue())
                st.download_button("Download Image", buf.getvalue(), "verify.jpg", "image/jpeg")
            
            for item in st.session_state.db[selected_client]:
                st.write(f"**{item['Room']}** - €{item['Price']}")
        else:
            st.warning("No windows added yet.")
