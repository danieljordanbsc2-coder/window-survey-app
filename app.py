import streamlit as st
import pandas as pd

# --- PAGE SETUP ---
st.set_page_config(page_title="Professional Window Survey", layout="wide")

# --- PRICING LOGIC ---
def get_pricing(w, h, sashes, include_vat):
    area = (w * h) / 1000000
    # Your specific tiers
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
    
    if include_vat:
        return round(unit_ex_vat * 1.135, 2)
    return round(unit_ex_vat, 2)

# --- DATABASE ---
if 'db' not in st.session_state:
    st.session_state.db = {}

# --- SIDEBAR: GLOBAL SETTINGS ---
st.sidebar.title("🛠 Project Settings")
job_type = st.sidebar.radio("Job Category", ["New Build / Supply Only", "Replacement / Full Fit"])
vat_mode = st.sidebar.toggle("Include 13.5% VAT in displayed prices", value=True)

st.sidebar.divider()
st.sidebar.subheader("📁 Client Folders")
new_client = st.sidebar.text_input("New Client Name")
if st.sidebar.button("Create Folder"):
    if new_client and new_client not in st.session_state.db:
        st.session_state.db[new_client] = []
        st.sidebar.success(f"Created {new_client}")

selected_client = st.sidebar.selectbox("Active Client", options=list(st.session_state.db.keys()))

# --- MAIN SCREEN ---
if selected_client:
    st.title(f"Survey: {selected_client}")
    st.caption(f"Mode: {job_type} | Prices: {'Inc VAT' if vat_mode else 'Ex VAT'}")

    # 1. THE SURVEY FORM
    with st.expander("➕ Add New Elevation", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            room = st.text_input("Room/Location")
            design = st.selectbox("Design", ["Casement", "Fixed", "Tilt & Turn", "French Door", "Bifold", "Slider"])
            color = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"])
        with c2:
            w = st.number_input("Width (mm)", min_value=0, value=1200)
            h = st.number_input("Height (mm)", min_value=0, value=1000)
            sashes = st.number_input("Extra Openers (€80)", min_value=0)
        with c3:
            glazing = st.selectbox("Glazing", ["Double Glazed", "Triple Glazed"])
            handle = st.selectbox("Handle", ["White", "Black", "Gold", "Chrome", "Satin"])
            sketch = st.file_uploader("Elevation Sketch", type=['jpg', 'png'])

        notes = st.text_area("Specific Requirements (e.g. Obscure glass, Fire Escape, etc.)")
        
        if st.button("Add to Quote Sheet"):
            price = get_pricing(w, h, sashes, vat_mode)
            st.session_state.db[selected_client].append({
                "Room": room, "Design": design, "W": w, "H": h, "Sashes": sashes,
                "Glazing": glazing, "Colour": color, "Handle": handle,
                "Notes": notes, "Price": price, "Image": sketch, "JobType": job_type
            })
            st.toast("Saved!")

    # 2. THE LIVE QUOTE SUMMARY
    st.header("Project Quote")
    if st.session_state.db[selected_client]:
        total_project = 0
        for i, item in enumerate(st.session_state.db[selected_client]):
            with st.container(border=True):
                col_img, col_txt, col_prc = st.columns([1, 3, 1])
                with col_img:
                    if item["Image"]: st.image(item["Image"])
                    else: st.write("No Sketch")
                with col_txt:
                    st.write(f"**{item['Room']}** ({item['Design']})")
                    st.write(f"{item['W']}mm x {item['H']}mm | {item['Glazing']} | {item['Colour']}")
                    if item['Notes']: st.info(f"Note: {item['Notes']}")
                with col_prc:
                    st.write(f"**€{item['Price']:,}**")
                    if st.button("🗑", key=f"del_{i}"):
                        st.session_state.db[selected_client].pop(i)
                        st.rerun()
                total_project += item['Price']
        
        st.divider()
        c_a, c_b = st.columns(2)
        with c_a:
            st.subheader("Total Project Quote")
            st.write(f"Type: **{job_type}**")
            if job_type == "Replacement / Full Fit":
                st.write("*(Includes removal and disposal of old units)*")
        with c_b:
            st.header(f"€{total_project:,.2f}")
            st.caption(f"{'Including 13.5% VAT' if vat_mode else 'Excluding VAT'}")

        # QUOTE OPTION
        if st.button("Prepare Final Quote for Office"):
            st.balloons()
            st.success("Quote finalized. Ready for download/export.")
    else:
        st.write("No elevations found. Add your first window above.")

else:
    st.info("👈 Use the sidebar to create a client folder or select an existing one.")
