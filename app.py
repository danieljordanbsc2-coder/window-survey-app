import streamlit as st
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="Window Survey Pro", layout="centered")

# --- PRICING LOGIC ---
def calculate_price(w, h, sashes):
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
    
    total_ex_vat = base + (sashes * 80)
    return round(total_ex_vat * 1.135, 2) # Total Inc 13.5% VAT

# --- APP START ---
if 'clients' not in st.session_state:
    st.session_state.clients = {}

st.title("Window & Door Site Survey")

# CLIENT MANAGEMENT
client_name = st.text_input("Enter Client Name to Start/Open Survey")
if client_name:
    if client_name not in st.session_state.clients:
        st.session_state.clients[client_name] = []
    
    # SURVEY FORM
    with st.expander("➕ Add New Window/Door", expanded=True):
        room = st.text_input("Room (e.g. Kitchen)")
        w = st.number_input("Width (mm)", min_value=0, value=1200)
        h = st.number_input("Height (mm)", min_value=0, value=1000)
        extra_sashes = st.number_input("Extra Sashes (€80 ea)", min_value=0, step=1)
        
        if st.button("Save to Elevation Sheet"):
            price = calculate_price(w, h, extra_sashes)
            st.session_state.clients[client_name].append({
                "Room": room, "Size": f"{w}x{h}", "Price": price
            })
            st.success("Window Saved!")

    # SHOW RESULTS
    st.subheader(f"Elevation Sheet: {client_name}")
    if st.session_state.clients[client_name]:
        df = pd.DataFrame(st.session_state.clients[client_name])
        st.table(df)
        st.metric("Total Project Quote (Inc VAT)", f"€{df['Price'].sum():,.2f}")
