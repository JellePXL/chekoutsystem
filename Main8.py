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

if 'view' not in st.session_state:
    st.session_state.view = "pos"

if 'editing_idx' not in st.session_state:
    st.session_state.editing_idx = None 
if 'edit_val' not in st.session_state:
    st.session_state.edit_val = ""     

if 'pending_choice' not in st.session_state:
    st.session_state.pending_choice = None 

if 'last_upload_id' not in st.session_state:
    st.session_state.last_upload_id = None
if 'last_cam_hash' not in st.session_state:
    st.session_state.last_cam_hash = None

# --- FUNCTIONS ---

def get_price(item_name):
    try:
        conn = sqlite3.connect('prices.db')
        cursor = conn.cursor()
        cursor.execute("SELECT price FROM products WHERE item_name=?", (item_name,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0.00
    except:
        return 0.00

def add_to_cart(item_name):
    price = get_price(item_name)
    st.session_state.cart.insert(0, {
        "name": item_name, 
        "price": price, 
        "qty": 1
    })
    st.session_state.editing_idx = None
    st.session_state.pending_choice = None

def remove_item(index):
    del st.session_state.cart[index]
    if st.session_state.editing_idx == index:
        st.session_state.editing_idx = None

def cancel_choice():
    st.session_state.pending_choice = None

def start_editing(index):
    st.session_state.editing_idx = index
    st.session_state.edit_val = ""

def keypad_input(digit):
    st.session_state.edit_val += str(digit)

def keypad_backspace():
    st.session_state.edit_val = st.session_state.edit_val[:-1]

def keypad_confirm():
    idx = st.session_state.editing_idx
    if idx is not None:
        try:
            new_qty = int(st.session_state.edit_val)
            if new_qty > 0:
                st.session_state.cart[idx]['qty'] = new_qty
        except ValueError:
            pass
    st.session_state.editing_idx = None
    st.session_state.edit_val = ""

@st.cache_resource
def load_model():
    try:
        model = tf.keras.models.load_model("trained_model5.h5")
        return model
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None

def model_prediction_smart(image_source):
    model = load_model()
    if model is None: return True, 0

    try:
        img = Image.open(image_source)
        img = img.convert('RGB')
        img = img.resize((224, 224))
        input_arr = tf.keras.preprocessing.image.img_to_array(img)
        input_arr = np.array([input_arr]) 
        
        predictions = model.predict(input_arr)[0]
        top_indices = np.argsort(predictions)[::-1]
        
        idx1 = top_indices[0]
        idx2 = top_indices[1]
        score1 = predictions[idx1]
        score2 = predictions[idx2]
        
        threshold_diff = 0.40
        min_confidence = 0.75
        
        if (score1 - score2 < threshold_diff) or (score1 < min_confidence):
            return False, [idx1, idx2]
        else:
            return True, idx1
    except Exception as e:
        st.error(f"Prediction Error: {e}")
        return True, 0 

try:
    with open("labels.txt") as f:
        all_labels = [line.strip() for line in f.readlines() if line.strip()]
except FileNotFoundError:
    all_labels = ["Apple", "Banana", "Orange", "Pear", "Peach"]

# =========================================================
#  PAGE LOGIC
# =========================================================

if st.session_state.view == "pos":
    col_left, col_right = st.columns([1.5, 1], gap="large")

    with col_left:
        st.title("Checkout Station")
        
        if st.session_state.pending_choice is not None:
            option_a = st.session_state.pending_choice[0]
            option_b = st.session_state.pending_choice[1]
            st.warning("⚠️ **Twijfelgeval!**")
            c1, c2, c3 = st.columns(3)
            with c1: st.button(f"{option_a}", type="primary", use_container_width=True, on_click=add_to_cart, args=(option_a,))
            with c2: st.button(f"{option_b}", type="primary", use_container_width=True, on_click=add_to_cart, args=(option_b,))
            with c3: st.button("🚫 Annuleer", use_container_width=True, on_click=cancel_choice)
            
        else:
            # --- SCANNER LOGICA (GECORRIGEERD) ---
            tab_upload, tab_cam = st.tabs(["📁 Upload File", "📷 Live Camera"])
            
            def handle_scan(source_img):
                is_sure, result_data = model_prediction_smart(source_img)
                if is_sure:
                    idx = result_data
                    if idx < len(all_labels):
                        add_to_cart(all_labels[idx])
                else:
                    idx1, idx2 = result_data
                    label1 = all_labels[idx1] if idx1 < len(all_labels) else "Unknown"
                    label2 = all_labels[idx2] if idx2 < len(all_labels) else "Unknown"
                    st.session_state.pending_choice = [label1, label2]
                st.rerun()

            with tab_upload:
                test_image = st.file_uploader("Choose an Image:", label_visibility="collapsed")
                if test_image is not None:
                    # FIX: Eerst checken, DAN opslaan, DAN pas scannen
                    if test_image.file_id != st.session_state.last_upload_id:
                        st.session_state.last_upload_id = test_image.file_id # <--- HIER OPSLAAN VOOR RERUN
                        st.image(test_image, caption="Scanning...", width=300)
                        handle_scan(test_image)
                    else:
                        st.image(test_image, caption="Scanned ✅", width=300)

            with tab_cam:
                cam_image = st.camera_input("Take a photo")
                if cam_image is not None:
                    current_hash = hash(cam_image.getvalue())
                    # FIX: Eerst checken, DAN opslaan, DAN pas scannen
                    if current_hash != st.session_state.last_cam_hash:
                        st.session_state.last_cam_hash = current_hash # <--- HIER OPSLAAN VOOR RERUN
                        handle_scan(cam_image)

            st.markdown("---") 
            c_fruit, c_veg = st.columns(2)
            with c_fruit:
                with st.popover("🍎 Fruits", use_container_width=True):
                    for item in all_labels: st.button(item, key=f"f_{item}", on_click=add_to_cart, args=(item,))
            with c_veg:
                with st.popover("🥦 Veggies", use_container_width=True):
                    st.write("Not available yet")

    with col_right:
        st.subheader("🧾 Receipt")
        with st.container(border=True, height=600):
            if st.session_state.editing_idx is not None:
                idx = st.session_state.editing_idx
                if idx < len(st.session_state.cart):
                    item = st.session_state.cart[idx]
                    st.markdown(f"### Editing: {item['name']}")
                    st.write("Type new quantity:")
                    disp_val = st.session_state.edit_val if st.session_state.edit_val else "0"
                    st.markdown(f"""<div style="background-color: #eee; color: #333; padding: 10px; font-size: 40px; text-align: center; border-radius: 5px; font-weight: bold; margin-bottom: 10px;">{disp_val}</div>""", unsafe_allow_html=True)
                    k1, k2, k3 = st.columns(3)
                    k1.button("1", key="k1", use_container_width=True, on_click=keypad_input, args=(1,))
                    k2.button("2", key="k2", use_container_width=True, on_click=keypad_input, args=(2,))
                    k3.button("3", key="k3", use_container_width=True, on_click=keypad_input, args=(3,))
                    k4, k5, k6 = st.columns(3)
                    k4.button("4", key="k4", use_container_width=True, on_click=keypad_input, args=(4,))
                    k5.button("5", key="k5", use_container_width=True, on_click=keypad_input, args=(5,))
                    k6.button("6", key="k6", use_container_width=True, on_click=keypad_input, args=(6,))
                    k7, k8, k9 = st.columns(3)
                    k7.button("7", key="k7", use_container_width=True, on_click=keypad_input, args=(7,))
                    k8.button("8", key="k8", use_container_width=True, on_click=keypad_input, args=(8,))
                    k9.button("9", key="k9", use_container_width=True, on_click=keypad_input, args=(9,))
                    k0, kb, kok = st.columns(3)
                    k0.button("0", key="k0", use_container_width=True, on_click=keypad_input, args=(0,))
                    kb.button("🔙", key="kb", use_container_width=True, on_click=keypad_backspace)
                    kok.button("✅", key="kok", type="primary", use_container_width=True, on_click=keypad_confirm)
                else:
                    st.session_state.editing_idx = None
                    st.rerun()
            else:
                if not st.session_state.cart:
                    st.info("Cart is empty.")
                else:
                    total_bill = 0.0
                    for i, item in enumerate(st.session_state.cart):
                        line_total = item['price'] * item['qty']
                        total_bill += line_total
                        c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 1])
                        with c1:
                            st.write(f"**{item['name']}**")
                            st.caption(f"€{item['price']:.2f}/st")
                        with c2:
                            st.button(f"{item['qty']}", key=f"qty_{i}", on_click=start_editing, args=(i,))
                        with c3:
                            st.write(f"€{line_total:.2f}")
                        with c4:
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
        consolidated_cart = {}
        for item in st.session_state.cart:
            name = item['name']
            if name in consolidated_cart:
                consolidated_cart[name]['qty'] += item['qty']
            else:
                consolidated_cart[name] = item.copy()
        final_total = 0.0
        for item in consolidated_cart.values():
            line_total = item['price'] * item['qty']
            final_total += line_total
            c1, c2 = st.columns([3, 1])
            c1.write(f"{item['name']} (x{item['qty']})")
            c2.write(f"**€{line_total:.2f}**")
        st.markdown("---")
        st.markdown(f"## Total Paid: €{final_total:.2f}")
        st.markdown("---")
        st.success("Payment Successful!")
        if st.button("Start New Customer Order", type="primary", use_container_width=True):
            st.session_state.cart = []
            st.session_state.editing_idx = None
            st.session_state.edit_val = ""
            st.session_state.pending_choice = None
            st.session_state.last_upload_id = None
            st.session_state.last_cam_hash = None
            st.session_state.view = "pos" 
            st.rerun()