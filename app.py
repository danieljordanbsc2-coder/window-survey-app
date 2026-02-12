import streamlit as st
import pandas as pd

# --- PRICING ENGINE (Locked to your 2026 Rules) ---
def get_p(w, h, sas, mat, job, vat):
    area = (w * h) / 1000000
    # Tiered Pricing
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
    c, f = 0, 0
    # Material & Replacement Logic
    if mat == "PVC Standard": c = unit_base * 0.55
    elif mat == "Aluclad Standard": c = unit_base; f = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (unit_base * 0.6) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (unit_base * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = unit_base * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = unit_base * 0.55; f = 245 if job == "Replacement" else 0
    
    final = max(c, 300.0) + f
    return round(final * (1.135 if vat else 1), 2)

# --- AUTO-TECHNICAL DRAWING ---
def draw_window_svg(w, h, style):
    ratio = w / h
    box_w = 260 if ratio > 1 else 260 * ratio
    box_h = 260 if ratio < 1 else 260 / ratio
    x, y = (300 - box_w)/2, (300 - box_h)/2
    
    # Opening Symbols (Standard Industry Notation)
    symbol = ""
    if "Left" in style:
        symbol = f'<polyline points="{x+10},{y+box_h/2} {x+box_w-10},{y+10} {x+box_w-10},{y+box_h-10} {x+10},{y+box_h/2}" fill="none" stroke="red" stroke-width="4"/>'
    elif "Right" in style:
        symbol = f'<polyline points="{x+box_w-10},{y+box_h/2} {x+10},{y+10} {x+10},{y+box_h-10} {x+box_w-10},{y+box_h/2}" fill="none" stroke="red" stroke-width="4"/>'
    elif "Top" in style:
        symbol = f'<polyline points="{x+box_w/2},{y+10} {x+10},{y+box_h-10} {x+box_w-10},{y+box_h-10} {x+box_w/2},{y+10}" fill="none" stroke="red" stroke-width="4"/>'
    
    svg = f"""
    <svg width="300" height="300
