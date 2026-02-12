import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np
import io

# --- PRICING LOGIC ---
def get_p(w, h, sas, mat, job, vat):
    a = (w * h) / 1e6
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
    u = b + (sas * 80)
    c, f = 0, 0
    if mat == "PVC Standard": c = u * 0.55
    elif mat == "Aluclad Standard": c = u; f = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (u * 0.6) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (u * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = u * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = u * 0.55; f = 245 if job == "Replacement" else 0
    return round((max(c, 300.0) + f) * (1.135 if vat else 1), 2)

def mk_fr(w, h):
    img = Image.new('RGB', (300, 300), "white")
    d = ImageDraw.Draw(img)
    r = w/h
    bw, bh = (260, 260/r) if r > 1 else (260*r, 260)
    x, y = (300-bw)/2, (300-bh)/2
    d.rectangle([x, y, x+bw, y+bh], outline="black", width=8)
    return img

def mk_ver(name, data, sig=None):
    bh, hh, cw = 450, 150, 900
    img = Image.new('RGB', (cw, (bh*len(data)) + hh + (300 if sig is not None else 0)), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 40), f"CLIENT: {name.upper()}", fill="black")
    y = hh
    for itm in data:
        if itm["Sketch"] is not None:
            sk = Image.fromarray(np.array(itm["Sketch"]).astype('uint8')).convert("RGB")
            sk.thumbnail((350, 350)); img.paste(sk, (40, y))
        d.text((420, y+40), f"ROOM: {itm['Room']}", fill="black")
        d.text((420, y+80), f"TYPE: {itm['Material']}", fill="black")
        d.text((420, y+120), f"SIZE: {itm['Size']} | COL: {itm['Color']}", fill="black")
        y += bh
    if sig is not None:
        s_img = Image.fromarray(np.array(sig).astype('uint8')).convert("RGB")
        s_img.thumbnail((700, 200)); img.paste(s_img, (40, y+50))
    return img

# --- APP ---
st.set_page_config(page_title="Pro Survey")
for k in ['db','sigs','v','e','fc']:
    if k not in st.session_state: st.session_state[k] = {} if k in ['db','sigs'] else ("S" if k=='v' else None if k=='e' else 0)

st.sidebar.title("📁 Sites")
with st.sidebar.expander("Add New"):
    sn = st.text_input("Name")
    if st.button("Create"):
        if sn: st.session_state.db[sn] = []; st.rerun()

sel = st.sidebar.selectbox("Active", ["Select..."] + list(st.session_state.db.keys()))

if sel != "Select...":
    job = st.sidebar.radio("Job", ["New Build", "Replacement"])
    vat = st.sidebar.toggle("Inc VAT", True)
    if st.sidebar.button("🛠 Survey"): st.session_state.v = "S"; st.rerun()
    if st.sidebar.button("📜 Quote"): st.session_state.v = "Q"; st.rerun()

    if st.session_state.v == "S":
        idx = st.session_state.e
        is_e = idx is not None
        curr = st.session_state.db[sel][idx] if is_e else {}
        st.title("Survey Entry")
        room = st.text_input("Room", value=curr.get("Room", ""))
        prod = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"], index=0 if not is_e else ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"].index(curr["Material"]))
        w = st.number_input("Width (mm)", value=int(curr.get("Size", "1200x1000").split('x')[0]) if is_e else 1200)
        h = st.number_input("Height (mm)", value=int(curr.get("Size", "1200x1000").split('x')[1]) if is_e else 1000)
        st.write("**Draw Design:**")
        canvas = st_canvas(stroke_width=3, stroke_color="black", background_image=mk_fr(w, h), height=300, width=300, key=f"c_{w}_{h}_{st.session_state.fc}")
        sas = st.number_input("Openers", value=curr.get("Sashes", 0))
        col = st.selectbox("Color", ["White", "Black", "Oak", "Cream"], index=0 if not is_e else ["White", "Black", "Oak", "Cream"].index(curr.get("Color", "White")))
        if st.button("Save"):
            p = get_p(w, h, sas, prod, job, vat)
            entry = {"Room": room, "Material": prod, "Size": f"{w}x{h}", "Sashes": sas, "Color": col, "Price": p, "Sketch": canvas.image_data}
            if is_e: st.session_state.db[sel][idx] = entry; st.session_state.e = None
            else: st.session_state.db[sel].append(entry)
            st.session_state.fc += 1; st.rerun()

        for i, itm in enumerate(st.session_state.db[sel]):
            with st.container(border=True):
                st.write(f"**{itm['Room']}** - €{itm['Price']}")
                if st.button("Edit", key=f"ed_{i}"): st.session_state.e = i; st.rerun()

    elif st.session_state.v == "Q":
        st.title(f"Quote: {sel}")
        total = sum([x['Price'] for x in st.session_state.db[sel]])
        st.header(f"Total: €{total:,.2f}")
        sig_p = st_canvas(stroke_width=2, stroke_color="black", height=150, width=500, key="sig")
        if st.button("Save Signature"): st.session_state.sigs[sel] = sig_p.image_data; st.success("Signed")
        if st.button("Get Image"):
            v_img = mk_ver(sel, st.session_state.db[sel], st.session_state.sigs.get(sel))
            buf = io.BytesIO(); v_img.save(buf, format="JPEG")
            st.download_button("Download", buf.getvalue(), f"{sel}.jpg")
