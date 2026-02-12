import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import io
from datetime import datetime

# ==========================================
# 1. PRICING & LOGIC ENGINE
# ==========================================

class PricingEngine:
    """Implements the 2026 Tiered Area Pricing & Material Multipliers."""
    
    # Area Tiers [cite: 2026-02-10]
    TIERS = [
        (0.6, 698), (0.8, 652), (1.0, 501), (1.2, 440), (1.5, 400),
        (2.0, 380), (2.5, 344), (3.0, 330), (3.5, 316), (4.0, 304),
        (4.5, 291), (999.0, 277)
    ]

    # Material Multipliers [cite: 2026-02-11]
    MULTIPLIERS = {
        "uPVC Standard": 0.55,
        "Aluclad Standard": 1.0,
        "uPVC Sliding Sash": 1.20,      # (0.60 * 2)
        "Hardwood Sliding Sash": 2.09,  # (0.95 * 2.2)
        "Aluclad Sliding Sash": 2.50,   # (1.0 * 2.5)
    }

    # Replacement/Fitting Fees [cite: 2026-02-11]
    FITTING_FEES = {
        "uPVC Standard": 0,
        "Aluclad Standard": 325,
        "uPVC Sliding Sash": 438,
        "Hardwood Sliding Sash": 480,
        "Aluclad Sliding Sash": 480
    }

    @classmethod
    def calculate_unit_price(cls, w_mm, h_mm, material, job_type, extra_sashes=0):
        area = (w_mm * h_mm) / 1_000_000
        # Determine Base Rate from Ladder
        base_rate = next(rate for limit, rate in cls.TIERS if area < limit)
        
        # Calculate Net Price
        list_price = (base_rate * area) + (extra_sashes * 80)
        net_price = list_price * cls.MULTIPLIERS.get(material, 1.0)
        
        # Enforce €300 floor [cite: 2026-02-11]
        final_unit = max(net_price, 300.0)
        
        # Add Fitting Fee if Replacement
        fitting = cls.FITTING_FEES.get(material, 0) if job_type == "Replacement" else 0
        
        return round(final_unit + fitting, 2)

# ==========================================
# 2. VISUALIZATION ENGINE (MATPLOTLIB)
# ==========================================

def generate_window_schematic(w, h, style):
    """Draws a 2D technical elevation of the window."""
    fig, ax = plt.subplots(figsize=(4, 4))
    
    # Outer Frame
    frame = patches.Rectangle((0, 0), w, h, linewidth=4, edgecolor='#2c3e50', facecolor='#ebf5fb')
    ax.add_patch(frame)
    
    if "Sash" in style:
        # Drawing top and bottom sash overlap
        top_sash = patches.Rectangle((w*0.05, h*0.5), w*0.9, h*0.45, linewidth=2, edgecolor='#34495e', facecolor='none')
        bot_sash = patches.Rectangle((w*0.02, h*0.05), w*0.96, h*0.48, linewidth=3, edgecolor='#2c3e50', facecolor='none')
        ax.add_patch(top_sash)
        ax.add_patch(bot_sash)
    elif "Casement" in style:
        # Central Mullion
        ax.plot([w/2, w/2], [0, h], color='#2c3e50', linewidth=3)
        # Opening indicator (triangle)
        ax.plot([w/2, w, w/2], [0, h/2, h], color='red', linestyle='--', linewidth=1)
        
    ax.set_xlim(-w*0.1, w*1.1)
    ax.set_ylim(-h*0.1, h*1.1)
    ax.axis('off')
    return fig

# ==========================================
# 3. PDF GENERATION (REPORTLAB)
# ==========================================

def create_pdf_quote(project_data, units):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph(f"<b>QUOTE: {project_data['name']}</b>", styles['Title']))
    elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Paragraph(f"Type: {project_data['type']}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Table
    data = [["Room", "Size (WxH)", "Material", "Style", "Price (Ex VAT)"]]
    subtotal = 0
    for u in units:
        data.append([u['room'], f"{u['w']}x{u['h']}", u['mat'], u['style'], f"€{u['price']:,}"])
        subtotal += u['price']
    
    vat = subtotal * 0.135
    total = subtotal + vat
    
    data.append(["", "", "", "Subtotal:", f"€{subtotal:,.2f}"])
    data.append(["", "", "", "VAT (13.5%):", f"€{vat:,.2f}"])
    data.append(["", "", "", "<b>GRAND TOTAL:</b>", f"<b>€{total:,.2f}</b>"])

    t = Table(data, colWidths=[100, 80, 100, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#004a99")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 10),
    ]))
    
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==========================================
# 4. MAIN STREAMLIT APP
# ==========================================

st.set_page_config(page_title="Pro-Window CRM", layout="wide")

# Theme styling
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    .main { color: #1f4e79; }
    div.stButton > button:first-child { background-color: #004a99; color: white; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# State Management
if 'jobs' not in st.session_state:
    st.session_state.jobs = [] # Mock Database

def main():
    st.sidebar.title("🏢 Pro-Window CRM")
    view = st.sidebar.radio("Navigation", ["Sales Rep View", "Fitter View"])
    
    if view == "Sales Rep View":
        sales_rep_dashboard()
    else:
        fitter_dashboard()

# ==========================================
# 5. USER ROLES: SALES REP
# ==========================================

def sales_rep_dashboard():
    st.title("💼 Sales Representative Portal")
    
    tab_setup, tab_config = st.tabs(["📁 Project Setup", "📐 Configurator & Quote"])
    
    with tab_setup:
        with st.form("project_form"):
            name = st.text_input("Project Name / Address")
            p_type = st.selectbox("Project Type", ["Replacement", "New Build", "Supply Only"])
            client = st.text_input("Client Reference")
            if st.form_submit_button("Initialize Project"):
                st.session_state.jobs.append({
                    "name": name, "type": p_type, "client": client, 
                    "units": [], "status": "Pending Measurement"
                })
                st.success(f"Project {name} Created.")

    with tab_config:
        if not st.session_state.jobs:
            st.warning("Please setup a project first.")
            return

        active_job = st.selectbox("Select Active Project", [j['name'] for j in st.session_state.jobs])
        job = next(j for j in st.session_state.jobs if j['name'] == active_job)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Add Window/Door Unit")
            room = st.text_input("Room Identifier (e.g. Kitchen)")
            w = st.number_input("Width (mm)", 100, 5000, 1200)
            h = st.number_input("Height (mm)", 100, 5000, 1000)
            mat = st.selectbox("Material", ["uPVC Standard", "Aluclad Standard", "uPVC Sliding Sash", "Hardwood Sliding Sash", "Aluclad Sliding Sash"])
            style = st.selectbox("Design Style", ["Casement", "Sliding Sash", "Tilt & Turn", "Fixed"])
            
            if st.button("➕ Add Unit to Project"):
                price = PricingEngine.calculate_unit_price(w, h, mat, job['type'])
                job['units'].append({
                    "room": room, "w": w, "h": h, "mat": mat, 
                    "style": style, "price": price, "verified": False
                })
                st.rerun()

        with col2:
            st.subheader("Elevation Preview")
            fig = generate_window_schematic(w, h, style)
            st.pyplot(fig)
            st.metric("Estimated Unit Price", f"€{PricingEngine.calculate_unit_price(w, h, mat, job['type']):,}")

        if job['units']:
            st.divider()
            st.subheader("Current Unit Schedule")
            df = pd.DataFrame(job['units'])
            st.dataframe(df[['room', 'w', 'h', 'mat', 'price']], use_container_width=True)
            
            pdf_buf = create_pdf_quote(job, job['units'])
            st.download_button("📥 Download Professional Quote (PDF)", pdf_buf, file_name=f"Quote_{job['name']}.pdf")

# ==========================================
# 6. USER ROLES: FITTER
# ==========================================

def fitter_dashboard():
    st.title("🔧 Fitter Technical Terminal")
    
    fitter_code = st.text_input("Enter Fitter Authorization Code", type="password")
    
    if fitter_code == "FITTER2026":
        st.success("Access Granted: Technical Validation Mode")
        
        pending_jobs = [j for j in st.session_state.jobs if j['status'] == "Pending Measurement"]
        
        if not pending_jobs:
            st.info("No pending measurements assigned.")
            return

        selected_job_name = st.selectbox("Select Job to Verify", [j['name'] for j in pending_jobs])
        job = next(j for j in st.session_state.jobs if j['name'] == selected_job_name)

        st.subheader(f"Project: {job['name']}")
        
        for i, unit in enumerate(job['units']):
            with st.expander(f"📍 Unit: {unit['room']} (Rough: {unit['w']}x{unit['h']})"):
                c1, c2 = st.columns(2)
                final_w = c1.number_input(f"Final Width (mm) - {unit['room']}", value=unit['w'], key=f"fw_{i}")
                final_h = c2.number_input(f"Final Height (mm) - {unit['room']}", value=unit['h'], key=f"fh_{i}")
                
                if st.button(f"Confirm Dimensions {i}"):
                    unit['w'] = final_w
                    unit['h'] = final_h
                    unit['verified'] = True
                    st.toast(f"{unit['room']} measurement hardened.")

        if all(u['verified'] for u in job['units']):
            if st.button("🚀 Push to Manufacturing"):
                job['status'] = "In Production"
                st.success("Project status updated to Production.")
                st.rerun()
    elif fitter_code:
        st.error("Invalid Code.")

if __name__ == "__main__":
    main()
