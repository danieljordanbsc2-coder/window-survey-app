import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np
import io

# --- PRICING ENGINE ---
def get_p(w, h, sas, mat, job, vat):
    a = (w * h) / 1e6
    # Pricing Tiers [cite: 2026-02-10]
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
    
    unit_ex = b + (sas * 80)
    c, f = 0, 0
    # Material Logic [cite: 2026-02-11]
    if mat == "PVC Standard": c = unit_ex * 0.55
    elif mat == "Aluclad Standard": c = unit_ex; f = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (unit_ex * 0.6) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (unit_ex * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = unit_ex * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = unit_ex * 0.55; f = 245 if job == "Replacement" else 0
    
    final = max(c, 300.0) + f
    return round(final * (1.135 if vat else 1), 2)

# --- THE FRAME BUILDER ---
def mk_fr(w, h):
    img = Image.new('RGB', (300, 300), "white")
    d = ImageDraw.Draw(img)
    r = w/h
    # Scale within 300x300 pad
    if r > 1: bw, bh = 260, 260/r
    else: bh, bw = 260, 260*r
    x, y = (300-bw)/2, (300-bh)/2
    # Draw heavy black frame
    d.rectangle([x, y, x+bw, y+bh], outline="black", width=12)
    return img

# --- APP SETUP ---
st.set_page_config(page_title="Pro Survey", layout="centered")
for k in ['db','sigs','v','e','fc']:
    if k not in st.session_state: 
        st.session_state[k] = {} if k in ['db','sigs'] else ("S" if k=='v' else None if k=='e' else 0)

# --- SIDEBAR ---
st.sidebar.title("📁 Site Folders")
with st.sidebar.expander("Add New Site"):
    sn = st.text_input("Address")
    if st.button("Create"):
        if sn: st.session_state.db[sn] = []; st.rerun()

sel = st.sidebar.selectbox("Active Site", ["Select..."] + list(st.session_state.db.keys()))

if sel != "Select...":
    job = st.sidebar.radio("Job Type", ["New Build", "Replacement"])
    vat = st.sidebar.toggle("Include 13.5% VAT", True)
    st.sidebar.divider()
    if st.sidebar.button("🛠 Survey Mode"): st.session_state.v = "S"; st.rerun()
    if st.sidebar.button("📜 Quote Mode"): st.session_state.v = "Q"; st.rerun()

# --- MAIN SCREEN ---
if sel != "Select...":
    # Header Dashboard
    items = st.session_state.db[sel]
    total_val = sum([x['Price'] for x in items])
    st.metric(label=f"Project: {sel}", value=f"€{total_val:,.2f}", delta=f"{len(items)} Units")

    if st.session_state.v == "S":
        idx = st.session_state.e
        is_e = idx is not None
        curr = st.session_state.db[sel][idx] if is_e else {}
        
        with st.container(border=True):
            room = st.text_input("Room", value=curr.get("Room", ""))
            prod = st.selectbox("Product Type", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"], 
                               index=0 if not is_e else ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"].index(curr["Material"]))
            
            c1, c2 = st.columns(2)
            with c1: w = st.number_input("Width (mm)", value=int(curr.get("Size", "1200x1000").split('x')[0]) if is_e else 1200)
            with c2: h = st.number_input("Height (mm)", value=int(curr.get("Size", "1200x1000").split('x')[1]) if is_e else 1000)
            
            st.write("**Design Elevation** (Frame updates automatically)")
            # The key forced refresh based on W/H ensures the black frame redraws
            canvas = st_canvas(
                stroke_width=4, 
                stroke_color="#000000", 
                background_image=mk_fr(w, h), 
                height=300, width=300, 
                drawing_mode="freedraw", 
                key=f"canv_{w}_{h}_{st.session_state.fc}"
            )

            sas = st.number_input("Extra Openers", value=curr.get("Sashes", 0))
            col = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"], 
                               index=0 if not is_e else ["White", "Anthracite", "Black", "Oak", "Cream"].index(curr.get("Color", "White")))
            
            if st.button("✅ Save Window"):
                p = get_p(w, h, sas, prod, job, vat)
                entry = {"Room": room, "Material": prod, "Size": f"{w}x{h}", "Sashes": sas, "Color": col, "Price": p, "Sketch": canvas.image_data}
                if is_e: st.session_state.db[sel][idx] = entry; st.session_state.e = None
                else: st.session_state.db[sel].append(entry)
                st.session_state.fc += 1; st.rerun()

        # Site List
        st.subheader("Elevations")
        for i, itm in enumerate(st.session_state.db[sel]):
            with st.container(border=True):
                c_img, c_txt, c_btn = st.columns([1, 2, 1])
                with c_img: st.image(itm["Sketch"], width=80)
                with c_txt: st.write(f"**{itm['Room']}**\n{itm['Size']} | €{itm['Price']}")
                with c_btn:
                    if st.button("✏️", key=f"ed_{i}"): st.session_state.e = i; st.rerun()
                    if st.button("🗑", key=f"dl_{i}"): st.session_state.db[sel].pop(i); st.rerun()

    elif st.session_state.v == "Q":
        st.title(f"Quote Summary")
        st.write(f"**Total Units:** {len(items)}")
        st.write(f"**Grand Total:** €{total_val:,.2f}")
        
        st.write("---")
        st.subheader("Client Signature")
        sig_pad = st_canvas(stroke_width=2, stroke_color="black", height=150, width=500, key="sig")
        if st.button("Save Signature"):
            st.session_state.sigs[sel] = sig_pad.image_data
            st.success("Signature Captured!")

        if st.button("Download Signed Order Sheet"):
            # Image logic would go here
            st.info("Generating high-res JPG...")
