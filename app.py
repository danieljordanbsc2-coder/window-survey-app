import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Window Survey Pro", layout="centered")

# --- MOBILE STYLING ---
st.markdown("""
    <style>
    div.stButton > button:first-child { width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    .stNumberInput, .stTextInput, .stSelectbox { margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

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
    
    # 2. Discount & Fee Logic
    if material == "PVC Standard":
        window_unit *= 0.55 # 45% Disc
    elif material == "Aluclad Standard":
        window_unit *= 1.0 # List Price
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

    # 3. €300 Floor + Fees
    final_ex_vat = max(window_unit, 300.0) + replacement_fee
    return round(final_ex_vat * 1.135, 2) if include_vat else round(final_ex_vat, 2)

# --- DYNAMIC FRAME GENERATOR ---
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

# --- VERIFICATION IMAGE GENERATOR (UPDATED WITH LABELS) ---
def create_verification_image(client_name, data, signature_data=None):
    block_h, head_h, canvas_w = 450, 200, 900 # Increased height for more text
    total_h = (block_h * len(data)) + head_h
    if signature_data is not None: total_h += 300 # Add space for signature

    img = Image.new('RGB', (canvas_w, total_h), color='white')
    draw = ImageDraw.Draw(img)
    
    # Header
    draw.text((40, 40), f"DESIGN VERIFICATION: {client_name.upper()}", fill="black")
    draw.text((40, 80), f"Date: {pd.Timestamp.now().strftime('%d/%m/%Y')}", fill="black")
    draw.line([(40, 130), (canvas_w-40, 130)], fill="black", width=3)

    y = head_h
    for item in data:
        if item["Sketch"] is not None:
            # Handle RGBA -> RGB conversion safely
            sk_array = np.array(item["Sketch"]).astype('uint8')
            if sk_array.shape[2] == 4: # If RGBA
                sk = Image.fromarray(sk_array).convert("RGB")
            else:
                sk = Image.fromarray(sk_array)
            sk.thumbnail((350, 350))
            img.paste(sk, (40, y))
            
        # DETAILED LABELS
        text_x = 420
        draw.text((text_x, y + 50), f"ROOM: {item['Room'].upper()}", fill="black")
        draw.text((text_x, y + 100), f"PRODUCT: {item['Material']} {item['Design']}", fill="black")
        draw.text((text_x, y + 150), f"SIZE: {item['Size']}mm", fill="black")
        draw.text((text_x, y + 200), f"SPECS: {item['Glazing']}, {item['Colour']}", fill="black")
        
        y += block_h
        draw.line([(40, y-20), (canvas_w-40, y-20)], fill="lightgrey", width=1)

    # Append Signature if it exists
    if signature_data is not None:
        y += 50
        draw.text((40, y), "CLIENT SIGNATURE OF APPROVAL:", fill="black")
        sig_array = np.array(signature_data).astype('uint8')
        if sig_array.shape[2] == 4:
             sig_img = Image.fromarray(sig_array).convert("RGB")
        else:
             sig_img = Image.fromarray(sig_array)
        sig_img.thumbnail((800, 200))
        img.paste(sig_img, (40, y + 50))

    return img

# --- SESSION STATE ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'signatures' not in st.session_state: st.session_state.signatures = {}
if 'edit_index' not in st.session_state: st.session_state.edit_index = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = "Survey"
if 'form_count' not in st.session_state: st.session_state.form_count = 0

# --- SIDEBAR ---
st.sidebar.title("📁 Site Survey")
selected_client = st.sidebar.selectbox("Select Site", options=["Add New..."] + list(st.session_state.db.keys()))

if selected_client == "Add New...":
    new_addr = st.sidebar.text_input("Site Address")
    if st.sidebar.button("Create Site Folder"):
        if new_addr:
            st.session_state.db[new_addr] = []
            st.rerun()
else:
    st.sidebar.divider()
    job_type = st.sidebar.radio("Job Type", ["New Build", "Replacement"])
    vat_mode = st.sidebar.toggle("Include 13.5% VAT", value=True)
    if st.sidebar.button("🛠 Survey Mode"): st.session_state.view_mode = "Survey"
    if st.sidebar.button("📜 Quote Mode"): st.session_state.view_mode = "Quote"

# --- MAIN SCREEN ---
if selected_client != "Add New...":
    if st.session_state.view_mode == "Survey":
        edit_idx = st.session_state.edit_index
        is_editing = edit_idx is not None
        curr = st.session_state.db[selected_client][edit_idx] if is_editing else None

        st.title(f"{'Edit Window' if is_editing else 'Add Window'}: {selected_client}")
        
        with st.form(key=f"f_{st.session_state.form_count}", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: room = st.text_input("Room Name", value=curr["Room"] if is_editing else "")
            with c2: design = st.selectbox("Style", ["Casement", "Fixed", "T&T", "French", "Bifold", "Slider"], index=["Casement", "Fixed", "T&T", "French", "Bifold", "Slider"].index(curr["Design"]) if is_editing else 0)

            prod = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"], index=["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"].index(curr["Material"]) if is_editing else 0)
            
            cw, ch = st.columns(2)
            with cw: w = st.number_input("Width (mm)", value=int(curr["Size"].split('x')[0]) if is_editing else 1200)
            with ch: h = st.number_input("Height (mm)", value=int(curr["Size"].split('x')[1]) if is_editing else 1000)
            
            c3, c4, c5 = st.columns(3)
            with c3: sashes = st.number_input("Openers", value=curr.get("Sashes", 0) if is_editing else 0)
            with c4: glazing = st.selectbox("Glazing", ["Double", "Triple"], index=["Double", "Triple"].index(curr.get("Glazing", "Double")) if is_editing else 0)
            with c5: color = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"], index=["White", "Anthracite", "Black", "Oak", "Cream"].index(curr.get("Colour", "White")) if is_editing else 0)
            
            st.write(f"**Sketch Design in {w}x{h} frame:**")
            frame_bg = create_frame_bg(w, h)
            canvas = st_canvas(stroke_width=3, stroke_color="#000000", background_image=frame_bg, height=300, width=300, drawing_mode="freedraw", key=f"c_{w}_{h}_{st.session_state.form_count}")

            if st.form_submit_button("Save Window"):
                price = get_pricing(w, h, sashes, prod, job_type, vat_mode)
                entry = {"Room": room, "Material": prod, "Design": design, "Size": f"{w}x{h}", "Sashes": sashes, "Glazing": glazing, "Colour": color, "Price": price, "Sketch": canvas.image_data}
                if is_editing:
                    st.session_state.db[selected_client][edit_idx] = entry
                    st.session_state.edit_index = None
                else:
                    st.session_state.db[selected_client].append(entry)
                st.session_state.form_count += 1
                st.rerun()

        st.divider()
        for i, item in enumerate(st.session_state.db[selected_client]):
            with st.container(border=True):
                c_i, c_t, c_b = st.columns([1, 2, 1])
                with c_i:
                    if item["Sketch"] is not None: st.image(item["Sketch"], width=80)
                with c_t: st.write(f"**{item['Room']}** - €{item['Price']}")
                with c_b:
                    if st.button("✏️", key=f"e_{i}"): st.session_state.edit_index = i; st.rerun()
                    if st.button("🗑", key=f"d_{i}"): st.session_state.db[selected_client].pop(i); st.rerun()

    elif st.session_state.view_mode == "Quote":
        st.title(f"Quote: {selected_client}")
        win_list = st.session_state.db[selected_client]
        total = sum([x['Price'] for x in win_list])
        lead = "3 weeks" if job_type == "New Build" else "6 weeks"
        
        # EMAIL GENERATOR
        email = f"Hi {selected_client},\n\nYour {job_type.lower()} quote for {len(win_list)} units is €{total:,.2f}.\n"
        if job_type == "Replacement": email += "Note: Replacement jobs require a skip on-site (not supplied).\n"
        email += f"Lead time: {lead}.\nVisit our showrooms in Ballymount or Galway.\n\nKind regards,\n[Your Name]"
        st.text_area("Email Draft", value=email, height=200)

        st.divider()
        st.subheader("Client Acceptance")

        # SIGNATURE PAD
        if selected_client not in st.session_state.signatures:
            st.write("Sign below to approve designs & pricing:")
            sig_canvas = st_canvas(stroke_width=2, stroke_color="black", background_color="#ffffff", height=150, width=600, drawing_mode="freedraw", key="sig_pad")
            if st.button("Save Signature"):
                if sig_canvas.image_data is not None:
                    st.session_state.signatures[selected_client] = sig_canvas.image_data
                    st.success("Signature saved!")
                    st.rerun()
        else:
            st.success("Signature on file.")
            st.image(st.session_state.signatures[selected_client], width=300)

        st.divider()
        # GENERATE IMAGE WITH SIGNATURE
        if st.button("Download Signed Verification Image"):
            sig_data = st.session_state.signatures.get(selected_client)
            final_img = create_verification_image(selected_client, win_list, sig_data)
            buf = io.BytesIO(); final_img.save(buf, format="JPEG")
            st.download_button("Download Image", buf.getvalue(), f"{selected_client}_signed.jpg")
