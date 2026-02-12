import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Window Survey Pro", layout="centered")

# --- PRICING ENGINE ---
def get_pricing(w, h, sashes, material, job_type, include_vat):
    area = (w * h) / 1000000
    
    # 1. Base List Price Tiers [cite: 2026-02-10]
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
    window_cost = 0
    replacement_fee = 0
    
    # 2. Material & Sash Logic [cite: 2026-02-11]
    if material == "PVC Standard":
        window_cost = unit_ex_vat * 0.55 # 45% Discount
    elif material == "Aluclad Standard":
        window_cost = unit_ex_vat # 0% Discount
        if job_type == "Replacement": replacement_fee = 325
    elif material == "PVC Sliding Sash":
        window_cost = (unit_ex_vat * 0.60) * 2 # 40% Disc, then x2
        if job_type == "Replacement": replacement_fee = 438
    elif material == "Hardwood Sliding Sash":
        window_cost = (unit_ex_vat * 0.95) * 2.2 # 5% Disc, then x2.2
        if job_type == "Replacement": replacement_fee = 480
    elif material == "Aluclad Sliding Sash":
        window_cost = (unit_ex_vat * 1.0) * 2.5 # 0% Disc, then x2.5
        if job_type == "Replacement": replacement_fee = 480
    elif material == "Fireproof":
        window_cost = unit_ex_vat * 0.55
        if job_type == "Replacement": replacement_fee = 245

    # 3. Floor (€300 ex vat) [cite: 2026-02-11]
    final_ex_vat = max(window_cost, 300.0) + replacement_fee
    return round(final_ex_vat * 1.135, 2) if include_vat else round(final_ex_vat, 2)

# --- DYNAMIC FRAME GENERATOR ---
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

# --- VERIFICATION IMAGE GENERATOR ---
def create_ver_img(name, data, sig=None):
    b_h, h_h, c_w = 480, 200, 900
    total_h = (b_h * len(data)) + h_h + (350 if sig is not None else 0)
    img = Image.new('RGB', (c_w, total_h), 'white')
    draw = ImageDraw.Draw(img)
    draw.text((40, 40), f"DESIGN VERIFICATION: {name.upper()}", fill="black")
    
    y = h_h
    for item in data:
        if item["Sketch"] is not None:
            sk_a = np.array(item["Sketch"]).astype('uint8')
            sk = Image.fromarray(sk_a).convert("RGB")
            sk.thumbnail((350, 350))
            img.paste(sk, (40, y))
        tx = 420
        draw.text((tx, y+40), f"ROOM: {item['Room'].upper()}", fill="black")
        draw.text((tx, y+90), f"PRODUCT: {item['Material']}", fill="black")
        draw.text((tx, y+140), f"SIZE: {item['Size']}mm", fill="black")
        draw.text((tx, y+190), f"SPECS: {item['Glazing']}, {item['Color']}", fill="black")
        y += b_h
        draw.line([(40, y-20), (c_w-40, y-20)], fill="lightgrey")
        
    if sig is not None:
        draw.text((40, y), "CLIENT APPROVAL SIGNATURE:", fill="black")
        s_img = Image.fromarray(np.array(sig).astype('uint8')).convert("RGB")
        s_img.thumbnail((700, 250))
        img.paste(s_img, (40, y+50))
    return img

# --- SESSION STATE ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'sigs' not in st.session_state: st.session_state.sigs = {}
if 'view' not in st.session_state: st.session_view = "Survey"
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
if 'f_count' not in st.session_state: st.session_state.f_count = 0

# --- SIDEBAR ---
st.sidebar.title("📁 Site Management")
with st.sidebar.expander("➕ Add New Site"):
    site_n = st.text_input("Site Address")
    if st.button("Create Folder"):
        if site_n: st.session_state.db[site_n] = []; st.rerun()

sites = list(st.session_state.db.keys())
sel_site = st.sidebar.selectbox("Active Site", options=["Select..."] + sites)

if sel_site != "Select...":
    st.sidebar.divider()
    job = st.sidebar.radio("Job Type", ["New Build", "Replacement"])
    vat = st.sidebar.toggle("Include 13.5% VAT", value=True)
    if st.sidebar.button("🛠 Survey Mode"): st.session_state.view = "Survey"; st.rerun()
    if st.sidebar.button("📜 Quote Mode"): st.session_state.view = "Quote"; st.rerun()

# --- MAIN APP ---
if sel_site != "Select...":
    if st.session_state.get('view', 'Survey') == "Survey":
        idx = st.session_state.edit_idx
        is_e = idx is not None
        curr = st.session_state.db[sel_site][idx] if is_e else None
        st.title(f"{'Edit' if is_e else 'Survey'}: {sel_site}")

        with st.form(key=f"survey_{st.session_state.f_count}", clear_on_submit=True):
            room = st.text_input("Room", value=curr["Room"] if is_e else "")
            prod = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"], 
                               index=0 if not is_e else ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"].index(curr["Material"]))
            c1, c2 = st.columns(2)
            with c1: w = st.number_input("Width (mm)", value=int(curr["Size"].split('x')[0]) if is_e else 1200)
            with c2: h = st.number_input("Height (mm)", value=int(curr["Size"].split('x')[1]) if is_e else 1000)
            c3, c4, c5 = st.columns(3)
            with c3: sas = st.number_input("Openers", value=curr.get("Sashes", 0) if is_e else 0)
            with c4: glaz = st.selectbox("Glazing", ["Double", "Triple"], index=0 if not is_e else ["Double", "Triple"].index(curr["Glazing"]))
            with c5: col = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"], index=0 if not is_e else ["White", "Anthracite", "Black", "Oak", "Cream"].index(curr["Color"]))
            
            st.write(f"**Draw in {w}x{h} Frame:**")
            canvas = st_canvas(stroke_width=3, stroke_color="black", background_image=create_frame_bg(w, h), height=300, width=300, key=f"c_{w}_{h}_{st.session_state.f_count}")

            if st.form_submit_button("Save Window"):
                p = get_pricing(w, h, sas, prod, job, vat)
                entry = {"Room": room, "Material": prod, "Size": f"{w}x{h}", "Sashes": sas, "Glazing": glaz, "Color": col, "Price": p, "Sketch": canvas.image_data}
                if is_e: st.session_state.db[sel_site][idx] = entry; st.session_state.edit_idx = None
                else: st.session_state.db[sel_site].append(entry)
                st.session_state.f_count += 1; st.rerun()

        st.divider()
        for i, itm in enumerate(st.session_state.db[sel_site]):
            with st.container(border=True):
                c_i, c_t, c_b = st.columns([1, 2, 1])
                with c_i: st.image(itm["Sketch"], width=80) if itm["Sketch"] is not None else None
                with c_t: st.write(f"**{itm['Room']}** - €{itm['Price']:,}")
                with c_b:
                    if st.button("✏️", key=f"ed_{i}"): st.session_state.edit_idx = i; st.rerun()
                    if st.button("🗑", key=f"dl_{i}"): st.session_state.db[sel_site].pop(i); st.rerun()

    elif st.session_state.get('view') == "Quote":
        st.title(f"Quote: {sel_site}")
        items = st.session_state.db[sel_site]
        total = sum([x['Price'] for x in items])
        lead = "3 weeks" if job == "New Build" else "6 weeks"
        
        email = f"Hi {sel_site},\n\nQuote for {job.lower()} project involves {len(items)} units.\n"
        if job == "Replacement": email += "Note: Skip required on-site as we do not dispose of old units.\n"
        email += f"Total: €{total:,.2f} ({'inc VAT' if vat else 'ex VAT'}). Lead time: {lead}.\n"
        email += "Visit showrooms in Ballymount or Galway.\n\nKind regards,\n[Your Name]"
        st.text_area("Email Draft", value=email, height=250)
        
        st.write("--- Client Approval ---")
        sig_c = st_canvas(stroke_width=2, stroke_color="black", height=150, width=500, key="sig_pad")
        if st.button("Save Signature"): st.session_state.sigs[sel_site] = sig_c.image_data; st.success("Signed!")
        
        if st.button("Download Verification Image"):
            v_img = create_ver_img(sel_site, items, st.session_state.sigs.get(sel_site))
            buf = io.BytesIO(); v_img.save(buf, format="JPEG")
            st.download_button("Download JPEG", buf.getvalue(), f"{sel_site}_verified.jpg")
        
        st.write("--- Client Signature ---")
        sig = st_canvas(stroke_width=2, stroke_color="black", height=150, width=400, key="sig")
        if st.button("Sign & Approve"): st.session_state.sigs[sel_site] = sig.image_data; st.success("Signed!")
