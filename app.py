import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas

# --- PAGE SETUP ---
st.set_page_config(page_title="Pro Window Survey", layout="wide")

# --- PRICING LOGIC ---
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

# --- DATABASE ---
if 'db' not in st.session_state:
    st.session_state.db = {}

# --- SIDEBAR ---
st.sidebar.title("🛠 Settings")
job_type = st.sidebar.radio("Job Category", ["New Build / Supply Only", "Replacement / Full Fit"]) # [cite: 2026-02-10]
vat_mode = st.sidebar.toggle("Include 13.5% VAT", value=True) # [cite: 2026-02-10]

new_client = st.sidebar.text_input("New Client Name")
if st.sidebar.button("Create Folder"):
    if new_client and new_client not in st.session_state.db:
        st.session_state.db[new_client] = []

selected_client = st.sidebar.selectbox("Active Client", options=list(st.session_state.db.keys()))

# --- MAIN SCREEN ---
if selected_client:
    st.title(f"Survey: {selected_client}")

    with st.expander("➕ Add New Elevation", expanded=True):
        c1, c2 = st.columns([1, 1])
        with c1:
            room = st.text_input("Room/Location")
            design = st.selectbox("Design", ["Casement", "Fixed", "Tilt & Turn", "French Door", "Bifold"])
            w = st.number_input("Width (mm)", min_value=0, value=1200)
            h = st.number_input("Height (mm)", min_value=0, value=1000)
            sashes = st.number_input("Extra Openers (€80)", min_value=0) # [cite: 2026-02-10]
            glazing = st.selectbox("Glazing", ["Double Glazed", "Triple Glazed"])
            color = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"])
            notes = st.text_area("Specific Requirements")
        
        with c2:
            st.write("**Draw Elevation Sketch Below**")
            # THE SKETCHPAD
            canvas_result = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",  
                stroke_width=3,
                stroke_color="#000000",
                background_color="#ffffff",
                height=400,
                width=400,
                drawing_mode="freedraw",
                key="canvas",
            )
            st.caption("Draw mullions and openers with your finger/stylus")

        if st.button("Save to Quote Sheet"):
            price = get_pricing(w, h, sashes, vat_mode)
            # Save drawing as an image
            img_data = canvas_result.image_data if canvas_result.image_data is not None else None
            
            st.session_state.db[selected_client].append({
                "Room": room, "Design": design, "W": w, "H": h, "Sashes": sashes,
                "Glazing": glazing, "Colour": color, "Price": price, 
                "Image": img_data, "JobType": job_type, "Notes": notes
            })
            st.success("Saved!")

    # QUOTE SUMMARY
    st.header("Project Quote")
    if st.session_state.db[selected_client]:
        total_project = 0
        for i, item in enumerate(st.session_state.db[selected_client]):
            with st.container(border=True):
                col_img, col_txt = st.columns([1, 2])
                with col_img:
                    if item["Image"] is not None: st.image(item["Image"], width=200)
                with col_txt:
                    st.subheader(f"{item['Room']} - €{item['Price']:,}")
                    st.write(f"{item['W']}x{item['H']} | {item['Design']} | {item['Colour']}")
                    st.write(f"*{item['Notes']}*")
                total_project += item['Price']
        
        st.divider()
        st.header(f"Total: €{total_project:,.2f} ({'Inc VAT' if vat_mode else 'Ex VAT'})")
else:
    st.info("👈 Select or create a client folder in the sidebar.")
