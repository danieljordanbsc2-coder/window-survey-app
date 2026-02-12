import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
import sqlite3
from datetime import datetime
from abc import ABC, abstractmethod
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

# ==============================================================================
# 1. DATA ACCESS LAYER (SQLITE & SESSION)
# ==============================================================================

class DatabaseManager:
    """Manages persistent storage for projects and technical measurements."""
    def __init__(self, db_name="pro_window_crm.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Projects Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                client_ref TEXT,
                job_type TEXT,
                status TEXT DEFAULT 'Surveying',
                vat_enabled INTEGER,
                created_at TIMESTAMP
            )
        """)
        # Window Units Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                room TEXT,
                width REAL,
                height REAL,
                material TEXT,
                layout TEXT,
                opening_style TEXT,
                drip TEXT,
                cill TEXT,
                glass TEXT,
                price REAL,
                is_finalized INTEGER DEFAULT 0,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
        """)
        self.conn.commit()

# ==============================================================================
# 2. BUSINESS LOGIC: PRICING KERNEL
# ==============================================================================

class PricingKernel:
    """
    Implements the 2026 Area-Tiered Price Ladder.
    Base Rate ($R$) is determined by Area ($A$):
    """
    
    TIER_DATA = [
        (0.6, 698), (0.8, 652), (1.0, 501), (1.2, 440), (1.5, 400),
        (2.0, 380), (2.5, 344), (3.0, 330), (3.5, 316), (4.0, 304),
        (4.5, 291), (999.0, 277)
    ]

    MATERIAL_MULTIPLIERS = {
        "PVC Standard": 0.55, "Aluclad Standard": 1.0, "PVC Sliding Sash": 1.2,
        "Hardwood Sliding Sash": 2.09, "Aluclad Sliding Sash": 2.5, "Fireproof": 0.55
    }

    REPLACEMENT_CHARGES = {
        "Aluclad Standard": 325, "PVC Sliding Sash": 438,
        "Hardwood Sliding Sash": 480, "Aluclad Sliding Sash": 480, "Fireproof": 245
    }

    @classmethod
    def calculate_price(cls, w, h, sashes, mat, job_type, vat_on):
        area = (w * h) / 1_000_000
        # Determine Base Rate from Ladder
        rate = next(r for a, r in cls.TIER_DATA if area < a)
        
        # Financial Formula:
        # $$P_{net} = \max((R \times A + S_{extra} \times 80) \times M_{mat}, 300) + C_{replace}$$
        
        list_price = (rate * area) + (sashes * 80)
        multiplier = cls.MATERIAL_MULTIPLIERS.get(mat, 1.0)
        net_unit = max(list_price * multiplier, 300.0)
        
        replacement_fee = cls.REPLACEMENT_CHARGES.get(mat, 0) if job_type == "Replacement" else 0
        total_ex_vat = net_unit + replacement_fee
        
        return round(total_ex_vat * (1.135 if vat_on else 1.0), 2)

# ==============================================================================
# 3. CAD ELEVATION ENGINE (SVG)
# ==============================================================================

class ElevationCAD:
    """Renders technical 2D schematics for Rep and Fitter verification."""
    
    @staticmethod
    def draw(w, h, layout, op_style):
        ratio = w / h
        dw = 280 if ratio > 1 else 280 * ratio
        dh = 280 if ratio < 1 else 280 / ratio
        x, y = (320 - dw)/2, (300 - dh)/2
        
        def sym(sx, sy, sw, sh, mode):
            if "Left" in mode: return f'<polyline points="{sx+10},{sy+sh/2} {sx+sw-10},{sy+10} {sx+sw-10},{sy+sh-10} {sx+10},{sy+sh/2}" fill="none" stroke="red" stroke-width="3"/>'
            if "Right" in mode: return f'<polyline points="{sx+sw-10},{sy+sh/2} {sx+10},{sy+10} {sx+10},{sy+sh-10} {sx+sw-10},{sy+sh/2}" fill="none" stroke="red" stroke-width="3"/>'
            if "Top" in mode: return f'<polyline points="{sx+sw/2},{sy+10} {sx+10},{sy+sh-10} {sx+sw-10},{sy+sh-10} {sx+sw/2},{sy+10}" fill="none" stroke="red" stroke-width="3"/>'
            return ""

        svg = f'<rect x="{x}" y="{y}" width="{dw}" height="{dh}" fill="none" stroke="#222" stroke-width="6"/>'
        
        if layout == "Transom Split":
            svg += f'<rect x="{x}" y="{y}" width="{dw}" height="{dh*0.3}" fill="#f0f8ff" stroke="#222" stroke-width="3"/>'
            svg += f'<rect x="{x}" y="{y+dh*0.3}" width="{dw}" height="{dh*0.7}" fill="#f0f8ff" stroke="#222" stroke-width="3"/>'
            svg += sym(x, y, dw, dh*0.3, "Top Hung") # Standard Fanlight
        elif layout == "Sliding Sash":
            svg += f'<rect x="{x+6}" y="{y+6}" width="{dw-12}" height="{dh/2}" fill="#f0f8ff" stroke="#444" stroke-width="2"/>'
            svg += f'<rect x="{x+2}" y="{y+dh/2}" width="{dw-4}" height="{dh/2-2}" fill="#f0f8ff" stroke="#222" stroke-width="4"/>'
        else:
            svg += f'<rect x="{x}" y="{y}" width="{dw}" height="{dh}" fill="#f0f8ff" stroke="#222" stroke-width="6"/>'
            svg += sym(x, y, dw, dh, op_style)

        return f'<div style="text-align:center; background:white; padding:15px; border-radius:10px;"><svg width="340" height="320">{svg}</svg></div>'

# ==============================================================================
# 4. PRESENTATION LAYER: SALES REP VIEW
# ==============================================================================

def sales_rep_module(db):
    st.title("💼 Enterprise Sales Hub")
    
    with st.sidebar:
        st.header("Project Intake")
        p_name = st.text_input("Site Address")
        p_ref = st.text_input("Client ID")
        p_type = st.radio("Contract", ["Replacement", "New Build", "Supply Only"])
        p_vat = st.toggle("VAT (13.5%) Included", value=True)
        if st.button("🚀 Create Project Folder"):
            db.conn.execute("INSERT INTO projects (name, client_ref, job_type, vat_enabled, created_at) VALUES (?,?,?,?,?)",
                            (p_name, p_ref, p_type, 1 if p_vat else 0, datetime.now()))
            db.conn.commit()
            st.success("Folder Initialized")

    # Project Selection
    projects = pd.read_sql("SELECT * FROM projects WHERE status != 'Complete'", db.conn)
    if projects.empty:
        st.info("No active projects found.")
        return

    sel_p = st.selectbox("Select Active Project", projects['name'].tolist())
    curr_p = projects[projects['name'] == sel_p].iloc[0]

    tab_input, tab_quote = st.tabs(["📐 Survey Capture", "📜 Quote Generation"])

    with tab_input:
        c1, c2 = st.columns([2, 1])
        with c1:
            with st.container(border=True):
                st.subheader("Window Configuration")
                room = st.text_input("Room Location")
                mat = st.selectbox("Material System", ["PVC Standard", "Aluclad Standard", "PVC Sliding Sash", "Aluclad Sliding Sash", "Fireproof"])
                lay = st.selectbox("Layout", ["Single Elevation", "Transom Split", "Sliding Sash"])
                
                dim1, dim2 = st.columns(2)
                w = dim1.number_input("Width (mm)", 100, 6000, 1200)
                h = dim2.number_input("Height (mm)", 100, 6000, 1000)
                
                op = st.selectbox("Opening Direction", ["Fixed", "Side Left", "Side Right", "Top Hung"])
                sash_cnt = st.slider("Total Openers", 0, 5, 1 if op != "Fixed" else 0)

            with st.container(border=True):
                st.subheader("Technical Options")
                drip = st.selectbox("Head Drip", ["Standard", "28mm", "None"])
                cill = st.selectbox("Cill Depth", ["None", "30mm Stub", "85mm", "150mm"])
                glass = st.selectbox("Glazing", ["Double", "Triple", "Toughened"])

        with c2:
            st.subheader("Technical Preview")
            st.markdown(ElevationCAD.draw(w, h, lay, op), unsafe_allow_html=True)
            
            if st.button("💾 SAVE UNIT", type="primary", use_container_width=True):
                price = PricingKernel.calculate_price(w, h, sash_cnt, mat, curr_p['job_type'], curr_p['vat_enabled'])
                db.conn.execute("""INSERT INTO units (project_id, room, width, height, material, layout, opening_style, drip, cill, glass, price) 
                                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                                (int(curr_p['id']), room, w, h, mat, lay, op, drip, cill, glass, price))
                db.conn.commit()
                st.toast("Synchronized with Database")

    with tab_quote:
        units = pd.read_sql(f"SELECT * FROM units WHERE project_id = {curr_p['id']}", db.conn)
        if not units.empty:
            st.dataframe(units[['room', 'material', 'width', 'height', 'price']], use_container_width=True)
            st.metric("Total Contract Value", f"€{units['price'].sum():,.2f}")
            if st.button("📥 EXPORT PDF QUOTE"):
                st.success("Quote Compiled for Client")

# ==============================================================================
# 5. презентация Layer: FITTER VIEW
# ==============================================================================

def fitter_module(
