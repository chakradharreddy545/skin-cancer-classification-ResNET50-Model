import streamlit as st
import numpy as np
import cv2
import matplotlib.pyplot as plt
from PIL import Image
from fpdf import FPDF
import tempfile
import os
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.applications.resnet50 import preprocess_input

# Cache the model loading
@st.cache_resource
def load_classification_models():
    try:
        model = load_model("skin_cancer_model.h5")
        return model
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None

# Preprocessing function
def preprocess_image(image: Image.Image):
    img = image.convert("RGB").resize((224, 224))
    img_array = np.array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)
    return img_array

# Grad-CAM implementation
def make_gradcam_heatmap(img_array, model, last_conv_layer_name, pred_index=None):
    grad_model = tf.keras.models.Model(
        [model.inputs], [model.get_layer(last_conv_layer_name).output, model.output]
    )

    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_array)
        if pred_index is None:
            pred_index = tf.argmax(predictions[0])
        class_channel = predictions[:, pred_index]

    grads = tape.gradient(class_channel, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    conv_outputs = conv_outputs[0]
    heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)
    return heatmap.numpy()

# PDF Report generator
def generate_pdf(original_image, prediction, heatmap_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Skin Cancer Classification Report", ln=True, align='C')

    # Add prediction
    pdf.ln(10)
    pdf.multi_cell(0, 10, f"Prediction: {prediction}")

    # Save temporary original image
    tmp_original = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    original_image.save(tmp_original.name)
    pdf.image(tmp_original.name, x=10, y=None, w=100)
    os.unlink(tmp_original.name)

    # Add Grad-CAM heatmap
    pdf.ln(10)
    pdf.image(heatmap_path, x=10, y=None, w=100)

    # Save PDF
    tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp_pdf.name)
    return tmp_pdf.name

# Streamlit UI
st.title("Skin Cancer Classification App with Grad-CAM and PDF Report")

uploaded_file = st.file_uploader("Upload a skin lesion image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    model = load_classification_models()
    if model is not None:
        img_array = preprocess_image(image)
        preds = model.predict(img_array)
        pred_class = np.argmax(preds[0])
        pred_conf = np.max(preds[0])

        st.write(f"Prediction class: {pred_class}, Confidence: {pred_conf:.2f}")

        # Grad-CAM
        try:
            last_conv_layer_name = "conv5_block3_out"  # For ResNet50
            heatmap = make_gradcam_heatmap(img_array, model, last_conv_layer_name)

            # Overlay heatmap on image
            img = np.array(image.convert("RGB").resize((224, 224)))
            heatmap_resized = cv2.resize(heatmap, (img.shape[1], img.shape[0]))
            heatmap_resized = np.uint8(255 * heatmap_resized)
            heatmap_color = cv2.applyColorMap(heatmap_resized, cv2.COLORMAP_JET)
            superimposed_img = cv2.addWeighted(img, 0.6, heatmap_color, 0.4, 0)

            st.image(superimposed_img, caption="Grad-CAM Heatmap", use_column_width=True)

            # Save heatmap for PDF
            tmp_heatmap = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            cv2.imwrite(tmp_heatmap.name, superimposed_img)

            # Generate PDF
            pdf_path = generate_pdf(image, f"Class: {pred_class}, Confidence: {pred_conf:.2f}", tmp_heatmap.name)

            with open(pdf_path, "rb") as pdf_file:
                st.download_button("Download PDF Report", pdf_file, file_name="skin_cancer_report.pdf")

            os.unlink(tmp_heatmap.name)
            os.unlink(pdf_path)
        except Exception as e:
            st.error(f"Error generating Grad-CAM: {e}")
