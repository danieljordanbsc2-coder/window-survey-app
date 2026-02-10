import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas # This is the key line

# --- PRICING & SETTINGS ---
def get_pricing(w, h, sashes, include_vat):
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
    
    unit_ex_vat = base + (sashes * 80) # [cite: 2026-02-10]
    return round(unit_ex_vat * 1.135, 2) if include_vat else round(unit_ex_vat, 2) # [cite: 2026-02-10]

if 'db' not in st.session_state: st.session_state.db = {}

# --- SIDEBAR ---
st.sidebar.title("🛠 Settings")
job_type = st.sidebar.radio("Job Category", ["New Build", "Replacement"]) # [cite: 2026-02-10]
vat_mode = st.sidebar.toggle("Include 13.5% VAT", value=True) # [cite: 2026-02-10]
selected_client = st.sidebar.text_input("Active Client Name")

# --- MAIN SURVEY ---
if selected_client:
    if selected_client not in st.session_state.db: st.session_state.db[selected_client] = []
    
    st.title(f"Survey: {selected_client}")
    
    with st.container(border=True):
        col_data, col_draw = st.columns([1, 1])
        
        with col_data:
            room = st.text_input("Room")
            design = st.selectbox("Style", ["Casement", "Fixed", "T&T", "French", "Bifold"])
            w = st.number_input("Width (mm)", value=1000)
            h = st.number_input("Height (mm)", value=1000)
            sashes = st.number_input("Extra Openers", min_value=0) # [cite: 2026-02-10]
            glaze = st.selectbox("Glazing", ["Double", "Triple"])
            color = st.selectbox("Colour", ["White", "Anthracite", "Oak"])
        
        with col_draw:
            st.write("**Sketch Elevation Here**")
            # This replaces the upload button with a live pad
            canvas_result = st_canvas(
                stroke_width=3,
                stroke_color="#000000",
                background_color="#ffffff",
                height=350,
                width=350,
                drawing_mode="freedraw",
                key="canvas_field",
            )

        if st.button("Save Window Details"):
            price = get_pricing(w, h, sashes, vat_mode)
            st.session_state.db[selected_client].append({
                "Room": room, "Design": design, "Size": f"{w}x{h}",
                "Specs": f"{glaze}, {color}", "Price": price,
                "Sketch": canvas_result.image_data
            })
            st.success("Saved to Elevation Sheet!")

    # PROJECT SUMMARY
    st.header("Project Quote")
    for item in st.session_state.db[selected_client]:
        with st.expander(f"{item['Room']} - €{item['Price']}", expanded=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                if item["Sketch"] is not None: st.image(item["Sketch"])
            with c2:
                st.write(f"**Size:** {item['Size']} | **Style:** {item['Design']}")
                st.write(f"**Details:** {item['Specs']}")
    
    total = sum([x['Price'] for x in st.session_state.db[selected_client]])
    st.sidebar.divider()
    st.sidebar.header(f"Total: €{total:,.2f}")

else:
    st.info("Enter a client name in the sidebar to start.")
