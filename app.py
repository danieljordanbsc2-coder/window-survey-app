import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw, ImageFont
import io

# --- APP CONFIG ---
st.set_page_config(page_title="Window Survey Pro", layout="wide")

# --- PRICING LOGIC ---
def get_pricing(w, h, sashes, include_vat):
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
    
    unit_ex_vat = base + (sashes * 80)
    return round(unit_ex_vat * 1.135, 2) if include_vat else round(unit_ex_vat, 2)

# --- IMAGE GENERATION LOGIC ---
def create_verification_image(client_name, data):
    # 1. Setup Canvas dimensions
    block_height = 400
    total_height = (block_height * len(data)) + 100 # Header space
    canvas_width = 800
    
    # 2. Create white background image
    img = Image.new('RGB', (canvas_width, total_height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to load a nice font, otherwise use default
    try:
        font_header = ImageFont.truetype("arial.ttf", 40)
        font_text = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font_header = ImageFont.load_default()
        font_text = ImageFont.load_default()

    # 3. Draw Header
    draw.text((20, 20), f"Design Verification: {client_name}", fill="black", font=font_header)
    y_offset = 100
    
    # 4. Loop through sketches and paste them
    for item in data:
        # Draw separator line
        draw.line([(20, y_offset-10), (canvas_width-20, y_offset-10)], fill="gray", width=2)
        
        if item["Sketch"] is not None:
            # Convert raw sketch data to an image
            sketch_img = Image.open(io.BytesIO(item["Sketch"]))
            # Resize sketch to fit nicely
            sketch_img.thumbnail((350, 350))
            # Paste sketch onto main canvas
            img.paste(sketch_img, (20, y_offset))
        
        # Draw Text Details next to sketch
        text_x = 400
        draw.text((text_x, y_offset + 20), f"Room: {item['Room']}", fill="black", font=font_text)
        draw.text((text_x, y_offset + 60), f"Style: {item['Design']}", fill="black", font=font_text)
        draw.text((text_x, y_offset + 100), f"Size: {item['Size']}", fill="black", font=font_text)
        draw.text((text_x, y_offset + 140), f"Colour: {item['Colour']}", fill="black", font=font_text)
        
        y_offset += block_height

    return img

# --- DATABASE & SESSION STATE ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'form_count' not in st.session_state: st.session_state.form_count = 0
if 'view_mode' not in st.session_state: st.session_state.view_mode = "Survey"

# --- SIDEBAR: CLIENT DIRECTORY ---
st.sidebar.title("📁 Client Folders")
new_client_name = st.sidebar.text_input("New Client Name/Address")
if st.sidebar.button("Add New Client"):
    if new_client_name and new_client_name not in st.session_state.db:
        st.session_state.db[new_client_name] = []
        st.sidebar.success(f"Folder created for {new_client_name}")

selected_client = st.sidebar.selectbox("Select Client", options=list(st.session_state.db.keys()))

if selected_client:
    st.sidebar.divider()
    st.sidebar.subheader("App Mode")
    # These buttons toggle between entering data and viewing the final output
    if st.sidebar.button("🛠 Survey Mode (Enter Windows)"):
        st.session_state.view_mode = "Survey"
    if st.sidebar.button("📜 Quote Mode (Show Client)"):
        st.session_state.view_mode = "Quote"
    
    st.sidebar.divider()
    job_type = st.sidebar.radio("Job Type", ["New Build", "Replacement"])
    vat_mode = st.sidebar.toggle("Include 13.5% VAT", value=True)

# --- MAIN SCREEN ---
if selected_client:
    # MODE 1: THE SURVEY FORM (Ladder work)
    if st.session_state.view_mode == "Survey":
        st.title(f"Surveying: {selected_client}")
        # clear_on_submit ensures the form wipes clean instantly
        with st.form(key=f"window_form_{st.session_state.form_count}", clear_on_submit=True):
            col_data, col_draw = st.columns([1, 1])
            with col_data:
                room = st.text_input("Room Location")
                design = st.selectbox("Style", ["Casement", "Fixed", "T&T", "French", "Bifold", "Slider"])
                w = st.number_input("Width (mm)", min_value=1, value=1200)
                h = st.number_input("Height (mm)", min_value=1, value=1000)
                sashes = st.number_input("Extra Openers", min_value=0, step=1)
                glazing = st.selectbox("Glazing", ["Double", "Triple"])
                color = st.selectbox("Colour", ["White", "Anthracite", "Black", "Oak", "Cream"])
                notes = st.text_area("Notes")
            
            with col_draw:
                st.write("**Sketch Elevation**")
                canvas_result = st_canvas(
                    stroke_width=3, stroke_color="#000000", background_color="#ffffff",
                    height=350, width=350, drawing_mode="freedraw", key=f"canvas_{st.session_state.form_count}"
                )

            if st.form_submit_button("Save & Clear Form"):
                price = get_pricing(w, h, sashes, vat_mode)
                st.session_state.db[selected_client].append({
                    "Room": room, "Design": design, "Size": f"{w}x{h}",
                    "Colour": color, "Specs": f"{glazing}, {color}", 
                    "Notes": notes, "Price": price,
                    "Sketch": canvas_result.image_data, "Type": job_type
                })
                # Increment counter to force a fresh canvas key
                st.session_state.form_count += 1
                st.rerun()

    # MODE 2: THE QUOTE & VERIFICATION (Client facing)
    else:
        st.title(f"Formal Quote: {selected_client}")
        st.write(f"**Job Type:** {job_type} | **VAT:** {'Inc 13.5%' if vat_mode else 'Excluded'}")
        st.divider()

        if st.session_state.db[selected_client]:
            # 1. The Verification Image Section
            st.subheader("Design Verification Image")
            st.caption("Click below to generate a single image of all sketches to send to the client for approval.")
            
            if st.button("Generate Sendable Image"):
                # Run the complex image generation function
                final_img = create_verification_image(selected_client, st.session_state.db[selected_client])
                
                # Convert the image to bytes so it can be downloaded
                buf = io.BytesIO()
                final_img.save(buf, format="JPEG")
                byte_im = buf.getvalue()

                # Show the result and offer download
                st.image(byte_im, caption="Final Verification Sheet")
                st.download_button(
                    label="Download Image to Phone",
                    data=byte_im,
                    file_name=f"{selected_client}_designs.jpg",
                    mime="image/jpeg"
                )
            
            st.divider()
            
            # 2. The Pricing Summary Section
            st.subheader("Pricing Summary")
            total_price = 0
            for i, item in enumerate(st.session_state.db[selected_client]):
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 2, 1])
                    with c1:
                        if item["Sketch"] is not None: st.image(item["Sketch"], width=100)
                    with c2:
                        st.write(f"**{item['Room']}** - {item['Size']}")
                    with c3:
                        st.write(f"**€{item['Price']:,}**")
                    total_price += item['Price']
            
            st.header(f"Total Project: €{total_price:,.2f}")
            
        else:
            st.warning("No windows added to this survey yet.")

else:
    st.info("👈 Enter a client name in the sidebar to start a new survey folder.")
