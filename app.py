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
    
    # 1. Get Base List Price (Aluclad Rate)
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
    
    # 2. Add Extra Sashes (€80 per opening ex vat)
    extra_sash_cost = sashes * 80
    list_price_ex_vat = base + extra_sash_cost
    
    # 3. Apply Discounts
    if material == "PVC":
        discounted_price = list_price_ex_vat * 0.55 # 45% discount
    else:
        discounted_price = list_price_ex_vat # 0% discount for Aluclad
        
    # 4. Apply Minimum Cost Floor (€300 ex vat)
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
            # Handle potential RGBA from canvas
            sketch_data = np.array(item["Sketch"]).astype('uint8')
            sketch = Image.fromarray(sketch_data).convert("RGB")
            sketch.thumbnail((350, 350))
            img.paste(sketch, (40, y_offset))
        draw.text((420, y_offset + 50), f"ROOM: {item['Room'].upper()}", fill="black")
        draw.text((420, y_offset + 90), f"STYLE: {item['Design']} ({item['Material']})", fill="black")
        draw.text((420, y_offset + 130), f"SIZE: {item['Size']}mm", fill="black")
        draw.text((420, y_offset + 170), f"COLOUR: {item['Colour']}", fill="black")
        y_offset += block_height
    return img

# --- SESSION STATE ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'edit_index' not in st.session_state: st.session_state.edit_index = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = "Survey"

# --- SIDEBAR ---
st.sidebar.title("📁 Client Folders")
new_
