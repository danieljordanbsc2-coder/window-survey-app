import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np
import io

# --- PRICING ENGINE ---
def get_pricing(w, h, sas, mat, job, vat):
    area = (w * h) / 1000000
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
    
    unit = b + (sas * 80)
    c, fee = 0, 0
    if mat == "PVC Standard": c = unit * 0.55
    elif mat == "Aluclad Standard": c = unit; fee = 325 if job == "Replacement" else 0
    elif mat == "PVC Sliding Sash": c = (unit * 0.60) * 2; fee = 438 if job == "Replacement" else 0
    elif mat == "Hardwood Sliding Sash": c = (unit * 0.95) * 2.2; fee = 480 if job == "Replacement" else 0
    elif mat == "Aluclad Sliding Sash": c = (unit * 1.0) * 2.5; fee = 480 if job == "Replacement" else 0
    elif mat == "Fireproof": c = unit * 0.55; fee = 245 if job == "Replacement" else 0
    return round((max(c, 300.0) + fee) * (1.135 if vat else 1), 2)

# --- IMAGE TOOLS ---
def create_frame(w, h):
    img = Image.new('RGB', (300, 300), "white")
    d = ImageDraw.Draw(img)
    r = w/h
    bw, bh = (260, 260/r) if r > 1 else (260*r, 260)
    x, y = (300-bw)/2, (300-bh)/2
    d.rectangle([x, y, x+bw, y+bh], outline="black", width=8)
    return img

def create_ver_img(name, data, sig=None):
    bh, hh, cw = 450, 150, 900
    img = Image.new('RGB', (cw, (bh*len(data)) + hh + (300 if sig is not None else 0)), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 40), f"VERIFICATION: {name.upper()}", fill="black")
    y = hh
    for itm in data:
        if itm["Sketch"] is not None:
            sk = Image.fromarray(np.array(itm["Sketch"]).astype('uint8')).convert("RGB")
            sk.thumbnail((350, 350)); img.paste(sk, (40, y))
        d.text((420, y+40), f"ROOM: {itm['Room']}", fill="black")
        d.text((420, y+80), f"PRODUCT: {itm['Material']}", fill="black")
        d.text((420, y+120), f"SIZE: {itm['Size']} | COL: {itm['
