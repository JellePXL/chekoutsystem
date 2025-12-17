import streamlit as st
import tensorflow as tf
import numpy as np
import sqlite3
from PIL import Image

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="POS Checkout", layout="wide")

# --- 1. INITIALIZE SESSION STATE ---
if 'cart' not in st.session_state:
    st.session_state.cart = []

if 'display_text' not in st.session_state:
    st.session_state.display_text = "" 

if 'view' not in st.session_state:
    st.session_state.view = "pos"

if 'last_upload_id' not in st.session_state:
    st.session_state.last_upload_id = None
if 'last_cam_hash' not in st.session_state:
    st.session_state.last_cam_hash = None

# --- HELPER FUNCTIONS ---

def get_price(item_name):
    """Fetch price from DB."""
    conn = sqlite3.connect('prices.db')
    cursor = conn.cursor()
    cursor.execute("SELECT price FROM products WHERE item_name=?", (item_name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0.00

def add_to_cart(item_name):
    """Adds item to cart and IMMEDIATELY resets display."""
    price = get_price(item_name)
    
    qty = 1
    current_disp = st.session_state.display_text
    
    if 'x' in current_disp:
        try:
            number_part = current_disp.split('x')[0]
            qty = int(number_part)
        except ValueError:
            qty = 1
            
    st.session_state.cart.insert(0, {
        "name": item_name, 
        "price": price, 
        "qty": qty
    })
    
    # CLEAR DISPLAY IMMEDIATELY
    st.session_state.display_text = ""

def remove_item(index):
    del st.session_state.cart[index]

# --- KEYPAD LOGIC FUNCTIONS ---
def press_num(digit):
    if 'x' not in st.session_state.display_text:
        st.session_state.display_text += str(digit)

def press_back():
    st.session_state.display_text = st.session_state.display_text[:-1]

def press_multiply():
    if st.session_state.display_text and 'x' not in st.session_state.display_text:
        st.session_state.display_text += "x"

# --- TENSORFLOW MODEL PREDICTION ---
def model_prediction(image_source):
    model = tf.keras.models.load_model("trained_model_new.h5")
    img = Image.open(image_source)
    img = img.convert('RGB')
    img = img.resize((64, 64))
    input_arr = tf.keras.preprocessing.image.img_to_array(img)
    input_arr = np.array([input_arr]) 
    predictions = model.predict(input_arr)
    return np.argmax(predictions)

# --- LOAD LABELS ---
try:
    with open("labels.txt") as f:
        all_labels = [line.strip() for line in f.readlines() if line.strip()]
except FileNotFoundError:
    all_labels = []


# =========================================================
#  PAGE LOGIC
# =========================================================

if st.session_state.view == "pos":
    col_left, col_right = st.columns([1.5, 1], gap="large")

    with col_left:
        st.title("Checkout Station")
        
        # --- SCANNER ---
        tab_upload, tab_cam = st.tabs(["📁 Upload File", "📷 Live Camera"])
        
        with tab_upload:
            test_image = st.file_uploader("Choose an Image:", label_visibility="collapsed")
            if test_image is not None:
                if test_image.file_id != st.session_state.last_upload_id:
                    st.image(test_image, caption="Scanning...", width=300)
                    result_index = model_prediction(test_image)
                    prediction_name = all_labels[result_index]
                    add_to_cart(prediction_name)
                    st.session_state.last_upload_id = test_image.file_id
                    st.rerun()
                else:
                    st.image(test_image, caption="Scanned ✅", width=300)

        with tab_cam:
            cam_image = st.camera_input("Take a photo")
            if cam_image is not None:
                current_hash = hash(cam_image.getvalue())
                if current_hash != st.session_state.last_cam_hash:
                    result_index = model_prediction(cam_image)
                    prediction_name = all_labels[result_index]
                    add_to_cart(prediction_name)
                    st.session_state.last_cam_hash = current_hash
                    st.rerun()

        st.markdown("---") 

        # --- DIGITAL DISPLAY ---
        display_content = st.session_state.display_text if st.session_state.display_text else "0"
        
        st.markdown(f"""
            <div style="background-color: #000; color: #0f0; padding: 15px; 
            font-family: 'Courier New', monospace; font-size: 30px; text-align: right; 
            border: 4px solid #333; border-radius: 5px; margin-bottom: 15px; font-weight: bold;">
            {display_content}
            </div>
        """, unsafe_allow_html=True)

        # --- CATEGORY BUTTONS (FIXED: Uses on_click now) ---
        c_fruit, c_veg = st.columns(2)
        with c_fruit:
            with st.popover("🍎 Fruits", use_container_width=True):
                for item in all_labels: 
                    # FIX: on_click ensures logic runs BEFORE redraw, fixing lag
                    st.button(item, key=f"f_{item}", on_click=add_to_cart, args=(item,))
        with c_veg:
            with st.popover("🥦 Veggies", use_container_width=True):
                for item in all_labels: 
                    # FIX: on_click ensures logic runs BEFORE redraw, fixing lag
                    st.button(item, key=f"v_{item}", on_click=add_to_cart, args=(item,))

        # --- KEYPAD ---
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        r1c1.button("1", use_container_width=True, on_click=press_num, args=(1,))
        r1c2.button("2", use_container_width=True, on_click=press_num, args=(2,))
        r1c3.button("3", use_container_width=True, on_click=press_num, args=(3,))
        r1c4.button("⬅️", use_container_width=True, on_click=press_back)

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        r2c1.button("4", use_container_width=True, on_click=press_num, args=(4,))
        r2c2.button("5", use_container_width=True, on_click=press_num, args=(5,))
        r2c3.button("6", use_container_width=True, on_click=press_num, args=(6,))
        r2c4.write("") 

        r3c1, r3c2, r3c3, r3c4 = st.columns(4)
        r3c1.button("7", use_container_width=True, on_click=press_num, args=(7,))
        r3c2.button("8", use_container_width=True, on_click=press_num, args=(8,))
        r3c3.button("9", use_container_width=True, on_click=press_num, args=(9,))
        r3c4.write("") 

        r4c1, r4c2, r4c3, r4c4 = st.columns(4)
        r4c1.write("") 
        r4c2.button("0", use_container_width=True, on_click=press_num, args=(0,))
        r4c3.button("X", use_container_width=True, on_click=press_multiply)
        r4c4.write("") 

    # RIGHT: RECEIPT
    with col_right:
        st.subheader("🧾 Receipt")
        with st.container(border=True, height=600):
            if not st.session_state.cart:
                st.info("Cart is empty.")
            else:
                total_bill = 0.0
                for i, item in enumerate(st.session_state.cart):
                    c1, c2, c3 = st.columns([3, 2, 1])
                    line_total = item['price'] * item['qty']
                    total_bill += line_total
                    
                    with c1:
                        if item['qty'] > 1:
                            st.write(f"**{item['name']}** (x{item['qty']})")
                        else:
                            st.write(f"**{item['name']}**")
                    with c2:
                        st.write(f"€{line_total:.2f}")
                    with c3:
                        st.button("❌", key=f"del_{i}", on_click=remove_item, args=(i,))
                
                st.markdown("---")
                st.markdown(f"### Total: €{total_bill:.2f}")

        if st.button("💳 PAY NOW", type="primary", use_container_width=True):
            if st.session_state.cart:
                st.session_state.view = "bill"
                st.rerun()
            else:
                st.toast("Cart is empty!")

elif st.session_state.view == "bill":
    c_left, c_center, c_right = st.columns([1, 2, 1])
    
    with c_center:
        st.title("🛒 Final Receipt")
        st.markdown("---")
        
        final_total = 0.0
        for item in st.session_state.cart:
            line_total = item['price'] * item['qty']
            final_total += line_total
            c1, c2 = st.columns([3, 1])
            c1.write(f"{item['name']} (x{item['qty']})")
            c2.write(f"**€{line_total:.2f}**")
        
        st.markdown("---")
        st.markdown(f"## Total Paid: €{final_total:.2f}")
        st.markdown("---")
        st.success("Payment Successful! Thank you for shopping.")
        st.write("") 
        
        if st.button("Start New Customer Order", type="primary", use_container_width=True):
            st.session_state.cart = []
            st.session_state.display_text = ""
            st.session_state.last_upload_id = None
            st.session_state.last_cam_hash = None
            st.session_state.view = "pos" 
            st.rerun()