import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Window Survey Pro", layout="wide")

# --- PRICING LOGIC ---
def get_pricing(w, h, sashes, material, include_vat):
    area = (w * h) / 1000000
    
    # 1. Base List Prices (Aluclad Rate)
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
    
    # 2. Add Extra Sashes (€80 ex vat)
    extra_sash_cost = sashes * 80
    list_price_ex_vat = base + extra_sash_cost
    
    # 3. Apply Discounts (PVC gets 45% off, Aluclad 0%)
    if material == "PVC":
        discounted_price = list_price_ex_vat * 0.55 
    else:
        discounted_price = list_price_ex_vat
        
    # 4. Minimum Cost Floor (€300 ex vat)
    final_ex_vat = max(discounted_price, 300.0)
    
    # 5. Add VAT if toggled
    if include_vat:
        return round(final_ex_vat * 1.135, 2)
    return round(final_ex_vat, 2)

# --- IMAGE GENERATION ---
def create_verification_image(client_name, data):
    block_height, header_height, canvas_width = 400, 150, 900
    img = Image.new('RGB', (canvas_width, (block_height * len(data)) + header_height), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((40, 40), f"DESIGN VERIFICATION: {client_name.upper()}", fill="black")
    y_offset = header_height
    for item in data:
        if item["Sketch"] is not None:
            sketch_array = np.array(item["Sketch"]).astype('uint8')
            sketch = Image.fromarray(sketch_array).convert("RGB")
            sketch.thumbnail((350, 350))
            img.paste(sketch, (40, y_offset))
        draw.text((420, y_offset + 50), f"ROOM: {item['Room'].upper()}", fill="black")
        draw.text((420, y_offset + 90), f"STYLE: {item['Design']} ({item['Material']})", fill="black")
        draw.text((420, y_offset + 130), f"SIZE: {item['Size']}mm", fill="black")
        y_offset += block_height
    return img

# --- SESSION STATE ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'edit_index' not in st.session_state: st.session_state.edit_index = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = "Survey"
if 'form_count' not in st.session_state: st.session_state.form_count = 0

# --- SIDEBAR ---
st.sidebar.title("📁 Client Folders")
new_c = st.sidebar.text_input("Add New Client")
if st.sidebar.button("Create Folder"):
    if new_c and new_c not in st.session_state.db:
        st.session_state.db[new_c] = []
        st.sidebar.success(f"Added {new_c}")

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
        edit_idx = st.session_state.edit_index
        is_editing = edit_idx is not None
        current_val = st.session_state.db[selected_client][edit_idx] if is_editing else None

        st.title(f"{'✏️ Editing Window' if is_editing else '📋 Site Survey'}: {selected_client}")
        
        with st.form(key=f"form_{st.session_state.form_count}", clear_on_submit=True):
            c1, c2 = st.columns([1, 1])
            with c1:
                room = st.text_input("Room", value=current_val["Room"] if is_editing else "")
                material = st.radio("Material Type", ["PVC (45% Disc)", "Aluclad (List)"], 
                                   index=1 if is_editing and current_val["Material"] == "Aluclad" else 0, horizontal=True)
                mat_key = "PVC" if "PVC" in material else "Aluclad"
                design = st.selectbox("Style", ["Casement", "Fixed", "T&T", "French", "Bifold", "Slider"], 
                                      index=["Casement", "Fixed", "T&T", "French", "Bifold", "Slider"].index(current_val["Design"]) if is_editing else 0)
                w = st.number_input("Width (mm)", value=int(current_val["Size"].split('x')[0]) if is_editing else 1200)
                h = st.number_input("Height (mm)", value=int(current_val["Size"].split('x')[1]) if is_editing else 1000)
                sashes = st.number_input("Extra Openers", value=current_val.get("Sashes", 0) if is_editing else 0)
                color = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"])
            
            with c2:
                st.write("**Sketch Elevation**")
                canvas_result = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff",
                                          height=300, width=300, drawing_mode="freedraw", key=f"c_{st.session_state.form_count}")
                notes = st.text_area("Notes", value=current_val["Notes"] if is_editing else "")

            if st.form_submit_button("Update" if is_editing else "Save Window"):
                price = get_pricing(w, h, sashes, mat_key, vat_mode)
                new_data = {
                    "Room": room, "Material": mat_key, "Design": design, "Size": f"{w}x{h}", "Sashes": sashes,
                    "Colour": color, "Notes": notes, "Price": price, 
                    "Sketch": canvas_result.image_data if canvas_result.image_data is not None else (current_val["Sketch"] if is_editing else None)
                }
                if is_editing:
                    st.session_state.db[selected_client][edit_idx] = new_data
                    st.session_state.edit_index = None
                else:
                    st.session_state.db[selected_client].append(new_data)
                st.session_state.form_count += 1
                st.rerun()

        # Elevation List
        st.divider()
        for i, item in enumerate(st.session_state.db[selected_client]):
            with st.container(border=True):
                col_img, col_txt, col_btn = st.columns([1, 2, 1])
                with col_img:
                    if item["Sketch"] is not None: st.image(item["Sketch"], width=80)
                with col_txt:
                    st.write(f"**{item['Room']}** ({item['Material']}) - €{item['Price']:,}")
                with col_btn:
                    if st.button("✏️", key=f"e_{i}"):
                        st.session_state.edit_index = i
                        st.rerun()
                    if st.button("🗑", key=f"d_{i}"):
                        st.session_state.db[selected_client].pop(i)
                        st.rerun()

    elif st.session_state.view_mode == "Quote":
        st.title(f"✉️ Quote Draft: {selected_client}")
        win_list = st.session_state.db[selected_client]
        total_p = sum([x['Price'] for x in win_list])
        lead_time = "3 weeks" if job_type == "New Build" else "6 weeks"
        
        email = f"Hi {selected_client},\n\n"
        email += f"Please see the quote for your {job_type.lower()} project involves {len(win_list)} unit(s).\n\n"
        if job_type == "Replacement":
            email += "Note: For replacement jobs, a skip is required on-site as we do not dispose of old units.\n\n"
        email += f"Total Price: €{total_p:,.2f} ({'inc VAT' if vat_mode else 'ex VAT'})\n"
        email += f"Lead time: {lead_time}.\n\n"
        email += "Visit our showrooms in Ballymount or Galway to see our products.\n\nKind regards,\n[Company Name]"
        
        st.text_area("Copy/Paste Email", value=email, height=300)
        
        if st.button("Generate Verification Image"):
            final_img = create_verification_image(selected_client, win_list)
            buf = io.BytesIO(); final_img.save(buf, format="JPEG")
            st.image(buf.getvalue()); st.download_button("Download Image", buf.getvalue(), "designs.jpg")
else:
    st.info("👈 Add a client to start.")
