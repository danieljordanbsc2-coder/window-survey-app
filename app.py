import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ==============================================================================
# 1. ENTERPRISE CORE: DATA & PRICING KERNEL
# ==============================================================================

class PricingKernel:
    """
    The 'Brain' of the app. Implements strict 2026 Area-Tiered Logic.
    [cite: 2026-02-10, 2026-02-11]
    """
    # Tiered pricing list (Area < Limit, List Price per m2)
    TIERS = [
        (0.6, 698), (0.8, 652), (1.0, 501), (1.2, 440), (1.5, 400),
        (2.0, 380), (2.5, 344), (3.0, 330), (3.5, 316), (4.0, 304),
        (4.5, 291), (999.0, 277)
    ]

    # Material Multipliers (Applied to List Price)
    # [Calculated from: PVC 0.6*2, Hardwood 0.95*2.2, Aluclad 1.0*2.5]
    MAT_MAP = {
        "PVC Standard": 0.55,           # Std PVC Discount approx 45%
        "Aluclad Standard": 1.0,
        "PVC Sliding Sash": 1.2,        # 0.6 * 2
        "Hardwood Sliding Sash": 2.09,  # 0.95 * 2.2
        "Aluclad Sliding Sash": 2.5,    # 1.0 * 2.5
        "Fireproof": 0.55
    }

    # Replacement Charges (Flat fees added after discount)
    FIXED_FEES = {
        "Aluclad Standard": 325,
        "PVC Sliding Sash": 438,
        "Hardwood Sliding Sash": 480,
        "Aluclad Sliding Sash": 480,
        "Fireproof": 245
    }

    @classmethod
    def calculate(cls, w, h, sashes, mat, job_type, vat_inc):
        area = (w * h) / 1_000_000
        # Determine List Price from Tiers
        base_rate = next(rate for limit, rate in cls.TIERS if area < limit)
        
        # Calculate List Total
        list_total = (base_rate * area) + (sashes * 80)
        
        # Apply Multiplier & Check €300 Floor [cite: 2026-02-11]
        discounted_price = list_total * cls.MAT_MAP.get(mat, 1.0)
        net_unit = max(discounted_price, 300.0)
        
        # Add Fitting for Replacements
        fitting = cls.FIXED_FEES.get(mat, 0) if job_type == "Replacement" else 0
        final_ex_vat = net_unit + fitting
        
        return round(final_ex_vat * (1.135 if vat_inc else 1.0), 2)

# ==============================================================================
# 2. TECHNICAL CAD ENGINE (SVG)
# ==============================================================================

class CADDrawer:
    """Professional 2D Schematics for Reps and Fitters."""
    @staticmethod
    def get_svg(w, h, config, op_t, op_b, drip):
        ratio = w / h
        dw, dh = (280 if ratio > 1 else 280 * ratio), (280 if ratio < 1 else 280 / ratio)
        x, y = (320 - dw)/2, (300 - dh)/2
        
        def sym(sx, sy, sw, sh, mode):
            if "Left" in mode: return f'<polyline points="{sx+10},{sy+sh/2} {sx+sw-10},{sy+10} {sx+sw-10},{sy+sh-10} {sx+10},{sy+sh/2}" fill="none" stroke="red" stroke-width="3"/>'
            if "Right" in mode: return f'<polyline points="{sx+sw-10},{sy+sh/2} {sx+10},{sy+10} {sx+10},{sy+sh-10} {sx+sw-10},{sy+sh/2}" fill="none" stroke="red" stroke-width="3"/>'
            if "Top" in mode: return f'<polyline points="{sx+sw/2},{sy+10} {sx+10},{sy+sh-10} {sx+sw-10},{sy+sh-10} {sx+sw/2},{sy+10}" fill="none" stroke="red" stroke-width="3"/>'
            return ""

        # Base Frame
        svg = f'<rect x="{x}" y="{y}" width="{dw}" height="{dh}" fill="none" stroke="black" stroke-width="6"/>'
        
        # Head Drip Visualization
        if drip == "28mm Drip":
            svg += f'<line x1="{x-10}" y1="{y}" x2="{x+dw+10}" y2="{y}" stroke="blue" stroke-width="4"/>'
            svg += f'<text x="{x+dw/4}" y="{y-5}" font-size="10" fill="blue">28mm HEAD DRIP</text>'

        if config == "Transom Split":
            th = dh * 0.3
            svg += f'<rect x="{x}" y="{y}" width="{dw}" height="{th}" fill="#f0f7ff" stroke="black" stroke-width="3"/>'
            svg += f'<rect x="{x}" y="{y+th}" width="{dw}" height="{dh-th}" fill="#f0f7ff" stroke="black" stroke-width="3"/>'
            svg += sym(x, y, dw, th, op_t) + sym(x, y+th, dw, dh-th, op_b)
        elif "Sash" in config:
            svg += f'<rect x="{x+6}" y="{y+6}" width="{dw-12}" height="{dh/2}" fill="#f0f7ff" stroke="#666" stroke-width="2"/>'
            svg += f'<rect x="{x+2}" y="{y+dh/2}" width="{dw-4}" height="{dh/2-2}" fill="#f0f7ff" stroke="black" stroke-width="4"/>'
            svg += f'<path d="M{x-15} {y+dh*0.8} L{x-15} {y+dh*0.4}" stroke="blue" stroke-width="2" marker-end="url(#arrowhead)"/>'
        else:
            svg += sym(x, y, dw, dh, op_t)

        return f'<div style="text-align:center; background:white; padding:15px; border-radius:10px;"><svg width="340" height="320">{svg}</svg></div>'

# ==============================================================================
# 3. PDF EXPORT COMPONENT
# ==============================================================================

class PDFExporter:
    """Compiles Technical Project Proposals."""
    @staticmethod
    def generate(project_name, units):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        style = getSampleStyleSheet()
        elems = [Paragraph(f"<b>OFFICIAL QUOTATION: {project_name}</b>", style['Title']), Spacer(1, 20)]
        
        data = [['Room', 'Size', 'Specs', 'Drip', 'Price']]
        for u in units:
            data.append([u['room'], u['size'], u['mat'], u['drip'], f"€{u['price']:,}"])
        
        total = sum(u['price'] for u in units)
        data.append(['', '', '', '<b>TOTAL (INC VAT)</b>', f'<b>€{total:,.2f}</b>'])
        
        t = Table(data, colWidths=[100, 80, 150, 80, 80])
        t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.grey), ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke)]))
        elems.append(t)
        doc.build(elems)
        return buf.getvalue()

# ==============================================================================
# 4. MAIN APP LOGIC (UI MODULES)
# ==============================================================================

def main():
    st.set_page_config(page_title="Windows Pro Enterprise", layout="wide")
    if 'projects' not in st.session_state: st.session_state.projects = {}

    with st.sidebar:
        st.title("🏗️ Pro-Window Hub")
        role = st.selectbox("Role Access", ["Sales Rep", "Fitter Tech"])
        st.divider()
        if role == "Sales Rep":
            p_name = st.text_input("New Site Address")
            p_mode = st.radio("Context", ["Replacement", "New Build"])
            if st.button("Create Site"):
                st.session_state.projects[p_name] = {"units": [], "mode": p_mode, "vat": True}
        
    active_sites = list(st.session_state.projects.keys())
    if not active_sites:
        st.info("Please create a site folder to begin.")
        return

    sel_site = st.selectbox("Active Project Folder", active_sites)
    proj = st.session_state.projects[sel_site]

    if role == "Sales Rep":
        sales_view(sel_site, proj)
    else:
        fitter_view(sel_site, proj)

def sales_view(name, proj):
    st.title(f"💼 Rep View: {name}")
    t1, t2 = st.tabs(["📐 Survey Input", "📜 Quote Manager"])

    with t1:
        c1, c2 = st.columns([2, 1])
        with c1:
            with st.container(border=True):
                room = st.text_input("Room Identifier")
                mat = st.selectbox("Product", list(PricingKernel.MAT_MAP.keys()))
                lay = st.selectbox("Layout", ["Single", "Transom Split", "Vertical Sash"])
                wc1, wc2 = st.columns(2)
                w, h = wc1.number_input("Width (mm)", 100, 6000, 1200), wc2.number_input("Height (mm)", 100, 6000, 1000)
                drip = st.selectbox("Head Drip Detail", ["Standard Drip", "28mm Drip", "No Drip"])
                ot, ob = "Fixed", "Fixed"
                if lay == "Transom Split":
                    ot, ob = st.selectbox("Top", ["Fixed", "Top Hung"]), st.selectbox("Bottom", ["Fixed", "Side Left", "Side Right"])
                else: ot = st.selectbox("Operation", ["Fixed", "Side Left", "Side Right", "Top Hung"])
                sas = st.slider("Extra Sashes", 0, 6, 1 if ot != "Fixed" else 0)

        with c2:
            st.subheader("CAD Preview")
            st.markdown(CADDrawer.get_svg(w, h, lay, ot, ob, drip), unsafe_allow_html=True)
            if st.button("✅ SAVE UNIT", use_container_width=True, type="primary"):
                price = PricingKernel.calculate(w, h, sas, mat, proj['mode'], proj['vat'])
                proj['units'].append({"room": room, "size": f"{w}x{h}", "mat": mat, "price": price, "drip": drip, "w": w, "h": h})
                st.rerun()

    with t2:
        if proj['units']:
            st.table(pd.DataFrame(proj['units'])[['room', 'size', 'mat', 'price']])
            if st.button("Generate Official PDF"):
                pdf_data = PDFExporter.generate(name, proj['units'])
                st.download_button("📥 Download Quote", pdf_data, f"Quote_{name}.pdf")

def fitter_view(name, proj):
    st.title(f"🔧 Fitter Terminal: {name}")
    code = st.text_input("Fitter Code (FIT-2026)", type="password")
    if code != "FIT-2026": return st.warning("Access Restricted.")
    
    for i, u in enumerate(proj['units']):
        with st.container(border=True):
            st.write(f"### {u['room']} - {u['mat']}")
            st.caption(f"Survey Meas: {u['size']} | Drip: {u['drip']}")
            fw = st.number_input(f"Final Width {i}", value=float(u['w']))
            if st.button(f"Harden Dimension {i}"):
                u['size'] = f"{fw}x{u['h']}"
                st.success("Production Measure Confirmed")

if __name__ == "__main__":
    main()
