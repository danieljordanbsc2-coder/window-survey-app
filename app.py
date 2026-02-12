import streamlit as st
import pandas as pd

# --- PRICING ENGINE ---
def get_p(w, h, sas, mat, job, vat):
    area = (w * h) / 1000000
    # Tiered Pricing Logic
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
    
    u_base = b + (sas * 80)
    c, f = 0, 0
    if mat == "PVC Standard": c = u_base * 0.55
    elif mat == "Aluclad Standard": c = u_base; f = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (u_base * 0.6) * 2; f = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (u_base * 0.95) * 2.2; f = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = u_base * 2.5; f = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = u_base * 0.55; f = 245 if job == "Replacement" else 0
    
    final = max(c, 300.0) + f
    return round(final * (1.135 if vat else 1), 2)

# --- AUTO-TECHNICAL DRAWING ---
def draw_win(w, h, mode):
    r = w / h
    bw = 260 if r > 1 else 260 * r
    bh = 260 if r < 1 else 260 / r
    x, y = (300 - bw)/2, (300 - bh)/2
    
    sym = ""
    if "Left" in mode:
        sym = f'<polyline points="{x+10},{y+bh/2} {x+bw-10},{y+10} {x+bw-10},{y+bh-10} {x+10},{y+bh/2}" fill="none" stroke="red" stroke-width="4"/>'
    elif "Right" in mode:
        sym = f'<polyline points="{x+bw-10},{y+bh/2} {x+10},{y+10} {x+10},{y+bh-10} {x+bw-10},{y+bh/2}" fill="none" stroke="red" stroke-width="4"/>'
    elif "Top"
