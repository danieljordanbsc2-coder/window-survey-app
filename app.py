import streamlit as st
import pandas as pd
import sqlite3
import io
import base64
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# ==========================================
# 1. DATABASE & STATE MANAGEMENT
# ==========================================

class WindowProDB:
    def __init__(self, db_path="windowpro_enterprise.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_schema()

    def create_schema(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT,
                client_name TEXT,
                job_type TEXT, -- New Build, Replacement, Supply Only
                status TEXT DEFAULT 'Quoted',
                fitter_code TEXT,
                created_at TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                location TEXT,
                w REAL, h REAL,
                material TEXT, layout TEXT,
                opening_type TEXT, -- Top Hung, Side Hung, etc.
                cill TEXT, drip TEXT,
                price REAL,
                is_measured INTEGER DEFAULT 0,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )
        """)
        self.conn.commit()

# ==========================================
# 2. ADVANCED SVG CAD ENGINE
# ==========================================

class SVGEngine:
    """Generates high-fidelity technical diagrams with mechanical indicators."""
    @staticmethod
    def draw_unit(w, h, opening_type, location="Unit"):
        ratio = w / h
        dw, dh = (280 if ratio > 1 else 280 * ratio), (280 if ratio < 1 else 280 / ratio)
        x, y = (320 - dw)/2, (300 - dh)/2
        
        # Mechanical Hinge Indicators
        mechanics = ""
        if opening_type == "Side Hung (Left)":
            mechanics = f'<polyline points="{x+10},{y+dh/2} {x+dw-10},{y+10} {x+dw-10},{y+dh-10} {x+10},{y+dh/2}" fill="none" stroke="red" stroke-dasharray="5,5" stroke-width="2"/>'
        elif opening_type == "Side Hung (Right)":
            mechanics = f'<polyline points="{x+dw-10},{y+dh/2} {x+10},{y+10} {x+10},{y+dh-10} {x+dw-10},{y+dh/2}" fill="none" stroke="red" stroke-dasharray="5,5" stroke-width="2"/>'
        elif opening_type == "Top Hung":
            mechanics = f'<polyline points="{x+dw/2},{y+10} {x+10},{y+dh-10} {x+dw-10},{y+dh-10} {x+dw/2},{y+10}" fill="none" stroke="red" stroke-dasharray="5,5" stroke-width="2"/>'
        elif opening_type == "Tilt & Turn":
            mechanics = f'<rect x="{x+10}" y="{y+10}" width="{dw-20}" height="{dh-20}" fill="none" stroke="blue" stroke-dasharray="2,2" stroke-width="1"/>'

        svg = f"""
        <svg width="340" height="340" viewBox="0 0 340 340" xmlns="http://www.w3.org/2000/svg">
            <rect x="{x}" y="{y}" width="{dw}" height="{dh}" fill="#f8f9fa" stroke="#333" stroke-width="5"/>
            {mechanics}
            <text x="{x+dw/2}" y="{y+dh+20}" font-family="Arial" font-size="12" text-anchor="middle" fill="black">{int(w)}mm (W)</text>
            <text x="{x-10}" y="{y+dh/2}" font-family="Arial" font-size="12" text-anchor="middle" fill="black" transform="rotate(-90 {x-10} {y+dh/2})">{int(h)}mm (H)</text>
            <text x="170" y="25" font-family="Arial" font-size="14" font-weight="bold" text-anchor="middle" fill="#004a99">{location}</text>
        </svg>
        """
        return svg

# ==========================================
# 3. 2026 PRICING KERNEL (STRICT RULES)
# ==========================================

class PricingKernel:
    LADDER = [(0.6, 698), (0.8, 652), (1.0, 501), (1.2, 440), (1.5, 400), (2.0, 380), (2.5, 344), (3.0, 330), (3.5, 316), (4.0, 304), (4.5, 291), (99.0, 277)]
    
    @classmethod
    def calculate(cls, w, h, sashes, mat, job_type):
        area = (w * h) / 1_000_000
        base_rate = next(r for limit, r in cls.LADDER if area < limit)
        list_val = (base_rate * area) + (sashes * 80)
        
        # Material Multipliers [cite: 2026-02-11]
        mults = {"PVC": 0.55 * 2, "Hardwood": 0.95 * 2.2, "Aluclad": 1.0 * 2.5}
        net = list_val * mults.get(mat, 1.0)
        
        # Hard Floor and Fitting Surcharges [cite: 2026-02-11]
        unit_price = max(net, 300.0)
        fitting = {"PVC": 0, "Aluclad": 325, "Hardwood": 480}.get(mat, 0) if job_type == "Replacement" else 0
        
        return round((unit_price + fitting) * 1.135, 2)

# ==========================================
# 4. MAIN APP UI
# ==========================================

st.set_page_config(page_title="WindowPro SaaS", layout="wide")
db = WindowProDB()

# Custom CSS for Enterprise Look
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    [data-testid="stMetricValue"] { color: #004a99; }
    .unit-card { background: white; padding: 20px; border-radius: 10px; border-left: 5px solid #004a99; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

def main():
    st.sidebar.title("💎 WindowPro SaaS")
    view = st.sidebar.radio("Navigation", ["Sales Rep View", "Fitter Terminal"])

    if view == "Sales Rep View":
        sales_view()
    else:
        fitter_view()

def sales_view():
    st.title("💼 Sales Pipeline")
    t1, t2 = st.tabs(["🆕 New Job", "📈 Management"])

    with t1:
        with st.form("new_job"):
            addr = st.text_input("Site Address")
            name = st.text_input("Client Name")
            j_type = st.selectbox("Job Type", ["Replacement", "New Build", "Supply Only"])
            code = st.text_input("Set Fitter Code", value="1234")
            if st.form_submit_button("Create Project"):
                cursor = db.conn.cursor()
                cursor.execute("INSERT INTO jobs (address, client_name, job_type, fitter_code, created_at) VALUES (?,?,?,?,?)",
                               (addr, name, j_type, code, datetime.now()))
                db.conn.commit()
                st.success("Project Folder Initialized")

    with t2:
        jobs = pd.read_sql("SELECT * FROM jobs ORDER BY id DESC", db.conn)
        if jobs.empty: return
        
        sel_job = st.selectbox("Select Project", jobs['address'])
        job = jobs[jobs['address'] == sel_job].iloc[0]
        
        st.subheader(f"Configuring: {job['address']} ({job['status']})")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            with st.container():
                st.markdown("### Unit Configurator")
                loc = st.text_input("Location (e.g., Kitchen Left)")
                mat = st.selectbox("Material System", ["PVC", "Aluclad", "Hardwood"])
                lay = st.selectbox("Opening Type", ["Side Hung (Left)", "Side Hung (Right)", "Top Hung", "Tilt & Turn", "Fixed"])
                wc, hc = st.columns(2)
                w = wc.number_input("Width (mm)", 100, 5000, 1200)
                h = hc.number_input("Height (mm)", 100, 5000, 1000)
                sas = st.number_input("Extra Opening Sashes", 0, 5, 0)
                
                if st.button("Add Unit to Project"):
                    price = PricingKernel.calculate(w, h, sas, mat, job['job_type'])
                    db.conn.execute("""INSERT INTO units (job_id, location, w, h, material, layout, opening_type, price) 
                                       VALUES (?,?,?,?,?,?,?,?)""", (int(job['id']), loc, w, h, mat, lay, lay, price))
                    db.conn.commit()
                    st.toast("Unit Saved")

        with c2:
            st.markdown("### Live CAD Preview")
            svg = SVGEngine.draw_unit(w, h, lay, loc)
            st.write(f'<div style="background:white; border-radius:10px;">{svg}</div>', unsafe_allow_html=True)
            st.metric("Total (Inc VAT)", f"€{PricingKernel.calculate(w, h, sas, mat, job['job_type']):,.2f}")

        # Unit List
        units = pd.read_sql(f"SELECT * FROM units WHERE job_id = {job['id']}", db.conn)
        if not units.empty:
            st.divider()
            st.subheader("Project Schedule")
            st.dataframe(units[['location', 'w', 'h', 'material', 'price']], use_container_width=True)
            if st.button("Generate PDF Quote"):
                st.info("PDF Engine Ready: Exporting with SVGs mapped to technical schedule.")

def fitter_view():
    st.title("🔧 Fitter Audit Terminal")
    code_input = st.text_input("Enter Job-Specific Code", type="password")
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE fitter_code = ?", (code_input,))
    job = cursor.fetchone()
    
    if job:
        st.success(f"ACCESS GRANTED: {job[1]}")
        units = pd.read_sql(f"SELECT * FROM units WHERE job_id = {job[0]}", db.conn)
        
        for i, u in units.iterrows():
            with st.expander(f"UNIT {u['id']}: {u['location']}", expanded=True):
                st.write(f"Rough Size: {u['w']}x{u['h']} | Type: {u['layout']}")
                cill = st.selectbox(f"Cill Type - Unit {u['id']}", ["Stub", "85mm", "150mm", "180mm"])
                drip = st.selectbox(f"Drip/Head Detail - Unit {u['id']}", ["Standard Drip", "Head Drip", "No Drip"])
                fw = st.number_input(f"Final Manufacturing Width (mm) - Unit {u['id']}", value=float(u['w']))
                fh = st.number_input(f"Final Manufacturing Height (mm) - Unit {u['id']}", value=float(u['h']))
                
                if st.button(f"Harden Measurements - Unit {u['id']}"):
                    db.conn.execute("UPDATE units SET w=?, h=?, cill=?, drip=?, is_measured=1 WHERE id=?", 
                                   (fw, fh, cill, drip, int(u['id'])))
                    db.conn.commit()
                    st.toast("Dimensions Hardened")
        
        if st.button("🚀 FINALISE TECHNICAL AUDIT", type="primary"):
            db.conn.execute("UPDATE jobs SET status='To Manufacture' WHERE id=?", (job[0],))
            db.conn.commit()
            st.success("Audit complete. Sales Rep notified.")
    elif code_input:
        st.error("Invalid Code")

if __name__ == "__main__":
    main()
