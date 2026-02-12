import streamlit as st
import pandas as pd
import io

# --- PRICING ENGINE (Locked to your 2026 Price List) ---
def get_p(w, h, sas, mat, job, vat):
    area = (w * h) / 1000000
    # Tier Logic [cite: 2026-02-10]
    if area < 0.6: b = 698
    elif area < 0.8: b = 652
    elif area < 1.0: b = 501
    elif area < 1.2: b = 440
    elif area < 1.5: b = 400
    elif area < 2.0: b = 380
    elif area < 2.5: b = 344
    elif area < 3.0: b = 330
    elif area < 3.5: b = 316
    elif area < 4.0: b = 304
    elif area < 4.5: b = 291
    else: b = 277
    
    unit_base = b + (sas * 80)
    c, fee = 0, 0
    # Material & Sash Logic [cite: 2026-02-11]
    if mat == "PVC Standard": c = unit_base * 0.55
    elif mat == "Aluclad Standard": c = unit_base; fee = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (unit_base * 0.60) * 2; fee = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (unit_base * 0.95) * 2.2; fee = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = unit_base * 2.5; fee = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = unit_ex * 0.55; fee = 245 if job == "Replacement" else 0
    
    final = max(c, 300.0) + fee
    return round(final * (1.135 if vat else 1), 2)

# --- INSTANT PREVIEW (The Simpler Way) ---
def draw_window_preview(w, h):
    ratio = w / h
    # Scale to fit a 300px box
    if ratio > 1: width, height = 300, 300/ratio
    else: height, width = 300, 300*ratio
    
    svg = f"""
    <svg width="300" height="300" viewBox="0 0 320 320" xmlns="http://www.w3.org/2000/svg">
        <rect x="{(300-width)/2}" y="{(300-height)/2}" width="{width}" height="{height}" 
              fill="#e1f5fe" stroke="black" stroke-width="8" />
        <line x1="{(300-width)/2}" y1="{(300-height)/2}" x2="{(300+width)/2}" y2="{(300+height)/2}" stroke="#b3e5fc" stroke-width="2" />
        <text x="160" y="315" text-anchor="middle" font-family="sans-serif" font-size="14">Shape: {w}mm x {h}mm</text>
    </svg>
    """
    st.write(f'<div style="display: flex; justify-content: center;">{svg}</div>', unsafe_allow_html=True)

# --- SESSION STATE ---
if 'db' not in st.session_state: st.session_state.db = {}

# --- SIDEBAR & GLOBAL SETTINGS ---
st.sidebar.title("🛠 Project Control")
job_mode = st.sidebar.radio("Project Type", ["New Build", "Replacement"], help="Replacement adds fitting fees automatically.")
vat_mode = st.sidebar.toggle("Include 13.5% VAT", True)

st.sidebar.divider()
site_name = st.sidebar.text_input("Site Address")
if st.sidebar.button("Create Site Folder"):
    if site_name: st.session_state.db[site_name] = []; st.rerun()

sel_site = st.sidebar.selectbox("Active Folder", ["Select..."] + list(st.session_state.db.keys()))

# --- MAIN APP ---
if sel_site != "Select...":
    st.title(f"🏠 {sel_site}")
    
    with st.expander("➕ Add New Window", expanded=True):
        # Quick Room Select for efficiency
        room_preset = st.selectbox("Room", ["Kitchen", "Living Room", "Master Bed", "Bed 2", "Bed 3", "Bathroom", "Hall", "Other..."])
        if room_preset == "Other...":
            room_name = st.text_input("Enter Room Name")
        else:
            room_name = room_preset

        prod = st.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
        
        col1, col2 = st.columns(2)
        with col1: w = st.number_input("Width (mm)", 100, 5000, 1200, 10)
        with col2: h = st.number_input("Height (mm)", 100, 5000, 1000, 10)
        
        # INSTANT PREVIEW (This replaces the broken drawing box)
        st.write("### Live Design Shape")
        draw_window_preview(w, h)
        
        sas = st.number_input("Extra Openers", 0, 10, 0)
        col = st.selectbox("Finish", ["White", "Anthracite", "Black", "Oak", "Cream"])
        
        if st.button("💾 Save to Quote", use_container_width=True):
            price = get_p(w, h, sas, prod, job_mode, vat_mode)
            st.session_state.db[sel_site].append({
                "Room": room_name, "Prod": prod, "Size": f"{w}x{h}", "Price": price, "Col": col
            })
            st.success(f"Added! Unit: €{price}")
            st.rerun()

    # SITE SUMMARY TABLE
    if st.session_state.db[sel_site]:
        st.divider()
        st.subheader("Current Quote Breakdown")
        df = pd.DataFrame(st.session_state.db[sel_site])
        st.table(df[['Room', 'Prod', 'Size', 'Price']])
        
        total = sum(d['Price'] for d in st.session_state.db[sel_site])
        st.metric("Total Order Value", f"€{total:,.2f}")
        
        if st.button("🗑 Clear All Windows"):
            st.session_state.db[sel_site] = []
            st.rerun()

else:
    st.info("👈 Enter a site address in the sidebar to begin your survey.")
