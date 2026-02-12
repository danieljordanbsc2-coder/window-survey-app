import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import io
import base64
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ==============================================================================
# 1. ENTERPRISE DATA ACCESS LAYER (DAO)
# ==============================================================================

class SiteDatabase:
    """Persistent SQLite implementation for project and measurement storage."""
    def __init__(self, db_path="pro_survey_enterprise.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.bootstrap()

    def bootstrap(self):
        cursor = self.conn.cursor()
        # Projects: The top-level container for all site data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                client_ref TEXT,
                job_type TEXT, -- Replacement, New Build, Supply Only
                status TEXT DEFAULT 'Surveying',
                vat_enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP
            )
        """)
        # Units: The granular technical specs for every opening
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS units (
                unit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                room TEXT,
                width REAL,
                height REAL,
                material TEXT,
                layout TEXT,
                opening_style TEXT,
                drip_spec TEXT,
                cill_spec TEXT,
                glazing TEXT,
                price REAL,
                is_fitter_verified INTEGER DEFAULT 0,
                fitter_notes TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            )
        """)
        self.conn.commit()

    def add_project(self, name, ref, j_type, vat):
        query = "INSERT INTO projects (name, client_ref, job_type, vat_enabled, created_at) VALUES (?,?,?,?,?)"
        self.conn.execute(query, (name, ref, j_type, 1 if vat else 0, datetime.now()))
        self.conn.commit()

    def add_unit(self, p_id, data):
        query = """INSERT INTO units (project_id, room, width, height, material, layout, 
                   opening_style, drip_spec, cill_spec, glazing, price) 
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)"""
        self.conn.execute(query, (p_id, data['room'], data['w'], data['h'], data['mat'], 
                                   data['lay'], data['op'], data['drip'], data['cill'], 
                                   data['glass'], data['price']))
        self.conn.commit()

# ==============================================================================
# 2. BUSINESS LOGIC: THE 2026 PRICING KERNEL
# ==============================================================================

class PricingKernel:
    """
    Implements strict 2026 Area-Tiered Pricing Ladder.
    Ensures proportional scaling where larger area = lower m2 rate.
   
    """
    TIERS = [
        (0.6, 698), (0.8, 652), (1.0, 501), (1.2, 440), (1.5, 400),
        (2.0, 380), (2.5, 344), (3.0, 330), (3.5, 316), (4.0, 304),
        (4.5, 291), (999.0, 277)
    ]

    MAT_MULTIPLIERS = {
        "PVC Standard": 0.55, "Aluclad Standard": 1.0, "PVC Sliding Sash": 1.2,
        "Hardwood Sliding Sash": 2.09, "Aluclad Sliding Sash": 2.5, "Fireproof": 0.55
    }

    FITTING_CHARGES = {
        "Aluclad Standard": 325, "PVC Sliding Sash": 438,
        "Hardwood Sliding Sash": 480, "Aluclad Sliding Sash": 480, "Fireproof": 245
    }

    @classmethod
    def calculate(cls, w, h, sas, mat, job_env, vat_inc):
        area = (w * h) / 1_000_000
        # Determine Base Rate per m2
        base_rate = next(rate for limit, rate in cls.TIERS if area < limit)
        
        # Calculate List Price
        list_val = (base_rate * area) + (sas * 80)
        
        # Apply Material Logic and €300 Floor
        net_unit = max(list_val * cls.MAT_MULTIPLIERS.get(mat, 1.0), 300.0)
        
        # Add Fitting for Replacement jobs
        fitting = cls.FITTING_CHARGES.get(mat, 0) if job_env == "Replacement" else 0
        total = net_unit + fitting
        
        return round(total * (1.135 if vat_inc else 1.0), 2)

# ==============================================================================
# 3. CAD SCHEMATIC RENDERER (SVG)
# ==============================================================================

class TechnicalCAD:
    """Renders proportional 2D elevations for factory/fitter verification."""
