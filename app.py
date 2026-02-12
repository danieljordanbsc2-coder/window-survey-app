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
    
    # 1. Base List Price Tiers
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
    
    # 2. Material & Sash Logic
    if material == "PVC Standard":
        window_unit *= 0.55 # 45% Discount
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

    # 3. Floor (€300 ex vat)
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

# --- VERIFICATION IMAGE ---
def create_ver_img(name, data, sig=None):
    b_h, h_h, c_w = 450, 200, 900
    total_h = (b_h * len(data)) + h_h + (300 if sig is not None else 0)
    img = Image.new('RGB', (c_w, total_h), 'white')
    draw = ImageDraw.Draw(img)
    draw.text((40, 40), f"VERIFICATION: {name.upper()}", fill="black")
    y = h_h
    for item in data:
        if item["Sketch"] is not None:
            sk_a = np.array(item["Sketch"]).astype('uint8')
            sk = Image.fromarray(sk_a).convert("RGB")
            sk.thumbnail((350, 350))
            img.paste(sk, (40, y))
        draw.text((420, y+50), f"ROOM: {item['Room']}", fill="black")
        draw.text((420, y+100), f"PRODUCT: {item['Material']}", fill="black")
        draw.text((420, y+150), f"SIZE: {item['Size']}", fill="black")
        y += b_h
    if sig is not None:
        draw.text((40, y), "SIGNATURE:", fill="black")
        s_img = Image.fromarray(np.array(sig).astype('uint8')).convert("RGB")
        s_img.thumbnail((700, 200))
        img.paste(s_img, (40, y+50))
    return img

# --- SESSION STATE ---
for key in ['db', 'sigs', 'view_mode', 'form_count']:
    if key not in st.session_state:
        if key == 'db': st.session_state[key] = {}
        elif key == 'sigs': st.session_state[key] = {}
        elif key == 'view_mode': st.session_state[key] = "Survey"
        else: st.session_state[key] = 0
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None

# --- SIDEBAR ---
st.sidebar.title("📁 Site Management")
with st.sidebar.expander("➕ Add New Site"):
    n_a = st.text_input("Site Name")
    if st.button("Create Site"):
        if n_a: st.session_state.db[n_a] = []; st.rerun()

sites = list(st.session_state.db.keys())
sel_site = st.sidebar.selectbox("Open Site", options=["Select..."] + sites)

# --- MAIN APP ---
if sel_site != "Select...":
    st.sidebar.divider()
    job = st.sidebar.radio("Job", ["New Build", "Replacement"])
    vat = st.sidebar.toggle("Inc 13.5% VAT", value=True)
    if st.sidebar.button("🛠 Survey"): st.session_state.view_mode = "Survey"; st.rerun()
    if st.sidebar.button("📜 Quote"): st.session_state.view_mode = "Quote"; st.rerun()

    if st.session_state.view_mode == "Survey":
        e_i = st.session_state.edit_idx
        is_e = e_i is not None
        curr = st.session_state.db[sel_site][e_i] if is_e else None
        st.title(f"{'Edit' if is_e else 'Survey'}: {sel_site}")

        with st.form(key=f"sf_{st.session_state.form_count}", clear_on_submit=True):
            room = st.text_input("Room", value=curr["Room"] if is_e else "")
            prod = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"], 
                               index=0 if not is_e else ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"].index(curr["Material"]))
            w = st.number_input("Width (mm)", value=int(curr["Size"].split('x')[0]) if is_e else 1200)
            h = st.number_input("Height (mm)", value=int(curr["Size"].split('x')[1]) if is_e else 1000)
            sas = st.number_input("Openers", value=curr.get("Sashes", 0) if is_e else 0)
            col = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"])
            
            st.write(f"**Sketch inside {w}x{h} Frame:**")
            canvas = st_canvas(stroke_width=3, stroke_color="black", background_image=create_frame_bg(w,h), height=300, width=300, key=f"c_{w}_{h}_{st.session_state.form_count}")

            if st.form_submit_button("Save Window"):
                p = get_pricing(w, h, sas, prod, job, vat)
                entry = {"Room": room, "Material": prod, "Size": f"{w}x{h}", "Sashes": sas, "Colour": col, "Price": p, "Sketch": canvas.image_data}
                if is_e: st.session_state.db[sel_site][e_i] = entry; st.session_state.edit_idx = None
                else: st.session_state.db[sel_site].append(entry)
                st.session_state.form_count += 1; st.rerun()

        st.divider()
        for i, itm in enumerate(st.session_state.db[sel_site]):
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1: st.image(itm["Sketch"], width=70) if itm["Sketch"] is not None else None
                with c2: st.write(f"**{itm['Room']}** - €{itm['Price']:,}")
                with c3:
                    if st.button("✏️", key=f"ed_{i}"): st.session_state.edit_idx = i; st.rerun()
                    if st.button("🗑", key=f"dl_{i}"): st.session_state.db[sel_site].pop(i); st.rerun()

    elif st.session_state.view_mode == "Quote":
        st.title(f"Quote: {sel_site}")
        items = st.session_state.db[sel_site]
        total = sum([x['Price'] for x in items])
        st.subheader(f"Total: €{total:,.2f}")
        
        st.write("--- Signature ---")
        sig_c = st_canvas(stroke_width=2, stroke_color="black", height=150, width=500, key="spad")
        if st.button("Save Signature"): st.session_state.sigs[sel_site] = sig_c.image_data; st.success("Signed!")
        
        if st.button("Download Verification Image"):
            v_img = create_ver
