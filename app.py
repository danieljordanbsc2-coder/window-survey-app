import streamlit as st
import pandas as pd

# --- PRICING ENGINE (Kept your specific 2026 rules) ---
def get_p(w, h, sas, mat, job, vat):
    area = (w * h) / 1e6
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
    
    u = b + (sas * 80)
    c, f = 0, 0
    if mat == "PVC Standard": c = u * 0.55
    elif mat == "Aluclad Standard": c = u; f = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (u * 0.6) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (u * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = u * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = u * 0.55; f = 245 if job == "Replacement" else 0
    
    final = max(c, 300.0) + f
    return round(final * (1.135 if vat else 1), 2)

# --- APP LAYOUT ---
st.set_page_config(page_title="Pro Survey 3.0", layout="wide")

if 'db' not in st.session_state: st.session_state.db = {}

st.sidebar.title("🛠 Site Admin")
site_n = st.sidebar.text_input("Site Name/Address")
if st.sidebar.button("Add Site"): st.session_state.db[site_n] = []

sel = st.sidebar.selectbox("Active Project", ["Select..."] + list(st.session_state.db.keys()))

if sel != "Select...":
    # Sidebar Logistics
    job_m = st.sidebar.radio("Job Type", ["New Build", "Replacement"])
    vat_m = st.sidebar.toggle("Include VAT", True)
    
    st.header(f"Surveying: {sel}")
    
    with st.expander("📝 Step 1: Window Dimensions & Style", expanded=True):
        c1, c2, c3 = st.columns(3)
        room = c1.selectbox("Room", ["Kitchen", "Living", "Dining", "Master Bed", "Ensuite", "Hall", "Garage"])
        mat = c2.selectbox("Product", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
        col = c3.selectbox("Finish", ["White", "Anthracite", "Black", "Oak", "Cream"])
        
        c4, c5, c6 = st.columns(3)
        w = c4.number_input("Width (mm)", 100, 5000, 1200)
        h = c5.number_input("Height (mm)", 100, 5000, 1000)
        sas = c6.number_input("Opening Sashes", 0, 10, 0)

    with st.expander("⚙️ Step 2: Technical Specs (Factory Ready)"):
        tc1, tc2, tc3 = st.columns(3)
        glass = tc1.selectbox("Glass Type", ["Standard Double", "Standard Triple", "Toughened Safety", "Acoustic (Soundproof)", "Obscure/Frosted"])
        cill = tc2.selectbox("Cill Required", ["None", "30mm (Stub)", "85mm", "150mm", "180mm"])
        vent = tc3.selectbox("Tricklevents", ["None", "2500mm2", "5000mm2"])
        
        restrict = st.toggle("Add Child Safety Restrictors")
        pole = st.toggle("Add Pole-and-Hook (for high windows)")

    with st.expander("🏗 Step 3: Site Logistics (Installer Ready)"):
        lc1, lc2 = st.columns(2)
        floor = lc1.selectbox("Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "High Access"])
        access = lc2.selectbox("Access", ["Standard Ladder", "Scaffold Required", "Cherry Picker", "Internal Fit Only"])
        notes = st.text_area("Site Notes (e.g., 'Brickwork unstable', 'Wires overhead')")

    if st.button("💾 Finalize & Save Window", use_container_width=True):
        price = get_p(w, h, sas, mat, job_m, vat_m)
        st.session_state.db[sel].append({
            "Room": room, "Size": f"{w}x{h}", "Material": mat, "Price": price, "Glass": glass, "Floor": floor
        })
        st.success(f"Saved! Unit Price: €{price}")

    if st.session_state.db[sel]:
        st.divider()
        st.subheader("Window Schedule")
        st.table(pd.DataFrame(st.session_state.db[sel]))
        
        total_val = sum(x['Price'] for x in st.session_state.db[sel])
        st.metric("Total Order Value", f"€{total_val:,.2f}")
