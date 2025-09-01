DEPLOY INTO STREAMLIT


!pip install fpdf
     
Requirement already satisfied: fpdf in /usr/local/lib/python3.11/dist-packages (1.7.2)

import streamlit as st
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
import cv2
from PIL import Image
import io
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pandas as pd
from fpdf import FPDF
import base64
from datetime import datetime
import os

# Set page configuration
st.set_page_config(
    page_title="Advanced Skin Cancer Classifier",
    page_icon="🔬",
    layout="wide"
)

# Define class names for HAM10000 dataset
class_names = [
    'Actinic keratoses',
    'Basal cell carcinoma',
    'Benign keratosis',
    'Dermatofibroma',
    'Melanoma',
    'Melanocytic nevi',
    'Vascular lesions'
]

# Class descriptions for educational information
class_descriptions = {
    'Actinic keratoses': "Rough, scaly patches that develop from years of sun exposure. They're considered precancerous and can develop into skin cancer if left untreated.",
    'Basal cell carcinoma': "The most common type of skin cancer. It appears as a pearly or waxy bump, or a flat, flesh-colored or brown scar-like lesion.",
    'Benign keratosis': "Harmless growths that develop on the skin's surface. They appear as waxy, stuck-on growths and are very common in older adults.",
    'Dermatofibroma': "Common, harmless skin growths that often appear as small, firm bumps. They're usually brownish in color and most commonly appear on the legs.",
    'Melanoma': "The most serious form of skin cancer. It develops in melanocytes, the cells that produce melanin. Melanomas often resemble moles and can develop from existing moles.",
    'Melanocytic nevi': "Common skin growths (moles) that develop when pigment cells grow in clusters. Most people have between 10-40 moles, and they can change in appearance over time.",
    'Vascular lesions': "Relatively common abnormalities of the skin and underlying tissues, often present at birth. They're caused by abnormal blood vessels located in or under the skin."
}

# Function to preprocess the image
def preprocess_image(img, target_size=(224, 224)):
    # Convert to RGB if grayscale
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

    # Apply hair removal (simplified DullRazor method)
    grayScale = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    kernel = cv2.getStructuringElement(1, (17, 17))
    blackhat = cv2.morphologyEx(grayScale, cv2.MORPH_BLACKHAT, kernel) # FIX: morphologyEx expects grayscale input - Corrected
    ret, thresh2 = cv2.threshold(blackhat, 10, 255, cv2.THRESH_BINARY)
    dst = cv2.inpaint(img, thresh2, 1, cv2.INPAINT_TELEA)

    # Resize
    dst = cv2.resize(dst, target_size)

    # Normalize to [0,1] range
    dst = dst / 255.0

    # Apply ImageNet normalization
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    dst = (dst - mean) / std

    return dst

# Function to make Grad-CAM heatmap
def make_gradcam_heatmap(img_array, model, last_conv_layer_name, pred_index=None):
    # Create a model that maps the input image to the activations of the last conv layer
    grad_model = tf.keras.models.Model(
        [model.inputs],
        [model.get_layer(last_conv_layer_name).output, model.output]
    )

    # Compute gradient of top predicted class with respect to last conv layer
    with tf.GradientTape() as tape:
        last_conv_layer_output, preds = grad_model(img_array)
        if pred_index is None:
            pred_index = tf.argmax(preds[0])
        class_channel = preds[:, pred_index]

    # Gradient of the output neuron with respect to the output feature map
    grads = tape.gradient(class_channel, last_conv_layer_output)

    # Vector of mean intensity of the gradient over a specific feature map channel
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    # Weight the channels by the computed importance
    last_conv_layer_output = last_conv_layer_output[0]
    heatmap = last_conv_layer_output @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)

    # Normalize the heatmap
    heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)

    return heatmap.numpy()

# Function to display Grad-CAM
def display_gradcam(image, heatmap, alpha=0.4):
    # Convert heatmap to RGB
    heatmap = np.uint8(255 * heatmap)
    jet = cm.get_cmap("jet")
    jet_colors = jet(np.arange(256))[:, :3] * 255 # Multiply by 255 for OpenCV
    jet_heatmap = jet_colors[heatmap]

    # Create superimposed image
    jet_heatmap = cv2.resize(jet_heatmap.astype(np.uint8), (image.shape[1], image.shape[0]))

    # Denormalize image for display
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    image_display = std * image + mean
    image_display = np.clip(image_display, 0, 1) * 255
    image_display = image_display.astype(np.uint8) # Convert to uint8 for OpenCV

    superimposed_img = cv2.addWeighted(image_display, 1 - alpha, jet_heatmap, alpha, 0) # Use 1-alpha for image weight

    return superimposed_img

# Function for test-time augmentation
def test_time_augmentation(model, img, num_augmentations=5):
    """Apply test-time augmentation for more robust predictions"""
    predictions = []

    # Original prediction
    predictions.append(model.predict(np.expand_dims(img, axis=0))[0])

    # Create augmentations
    augmentations = []
    # Horizontal flip
    aug_img_hflip = np.fliplr(img)
    augmentations.append(aug_img_hflip)
    # Vertical flip
    aug_img_vflip = np.flipud(img)
    augmentations.append(aug_img_vflip)
    # 90 degree rotation
    aug_img_rot90 = np.rot90(img)
    augmentations.append(aug_img_rot90)
    # 270 degree rotation
    aug_img_rot270 = np.rot90(img, 3)
    augmentations.append(aug_img_rot270)

    # Random brightness adjustment (apply to normalized image)
    for _ in range(num_augmentations - len(augmentations)):
        bright_img = img.copy()
        bright_img = bright_img + np.random.uniform(-0.1, 0.1)
        bright_img = np.clip(bright_img, -1.0, 1.0)
        augmentations.append(bright_img)

    # Make predictions on augmentations
    for aug_img in augmentations[:num_augmentations-1]:
        pred = model.predict(np.expand_dims(aug_img, axis=0))[0]
        predictions.append(pred)

    # Average predictions
    return np.mean(predictions, axis=0)

# Function to create downloadable PDF report
def create_report(image, gradcam_image, diagnosis, confidence, all_probs, feedback=None):
    pdf = FPDF()
    pdf.add_page()

    # Set up the PDF
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(190, 10, 'Skin Lesion Analysis Report', 0, 1, 'C')
    pdf.set_font('Arial', '', 12)
    pdf.cell(190, 10, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1, 'C')
    pdf.ln(10)

    # Save images to temporary files
    temp_original = 'temp_original.jpg'
    temp_gradcam = 'temp_gradcam.jpg'

    if isinstance(image, np.ndarray):
        Image.fromarray(image).save(temp_original)
    else:
        image.save(temp_original)

    if isinstance(gradcam_image, np.ndarray):
        Image.fromarray(gradcam_image).save(temp_gradcam)
    else:
        gradcam_image.save(temp_gradcam)

    # Add images to PDF
    pdf.cell(190, 10, 'Original Image', 0, 1, 'L')
    pdf.image(temp_original, x=10, y=None, w=90)
    pdf.ln(5)
    pdf.cell(190, 10, 'Model Focus (Grad-CAM)', 0, 1, 'L')
    pdf.image(temp_gradcam, x=10, y=None, w=90)
    pdf.ln(10)

    # Add diagnosis information
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, 'Diagnosis Results:', 0, 1, 'L')
    pdf.set_font('Arial', '', 12)
    pdf.cell(190, 10, f'Predicted condition: {diagnosis}', 0, 1, 'L')
    pdf.cell(190, 10, f'Confidence: {confidence:.2%}', 0, 1, 'L')
    pdf.ln(5)

    # Add description of the condition
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(190, 10, 'About this condition:', 0, 1, 'L')
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(190, 10, class_descriptions.get(diagnosis, "No description available."))
    pdf.ln(5)

    # Add all probabilities
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(190, 10, 'Probability Distribution:', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)

    for i, class_name in enumerate(class_names):
        pdf.cell(190, 8, f'{class_name}: {all_probs[i]:.2%}', 0, 1, 'L')

    # Add feedback if provided
    if feedback:
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(190, 10, 'User Feedback:', 0, 1, 'L')
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(190, 10, feedback)

    # Add disclaimer
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 10)
    pdf.multi_cell(190, 10, 'MEDICAL DISCLAIMER: This tool is for educational purposes only and is not intended to be a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.')

    # Save PDF to a temporary file
    temp_pdf = 'skin_lesion_report.pdf'
    pdf.output(temp_pdf)

    # Read PDF file and encode to base64
    with open(temp_pdf, "rb") as f:
        pdf_data = f.read()

    # Clean up temporary files
    os.remove(temp_original)
    os.remove(temp_gradcam)
    os.remove(temp_pdf)

    return pdf_data

# Function to create download link
def get_download_link(pdf_data, filename="skin_lesion_report.pdf", text="Download PDF Report"):
    b64_pdf = base64.b64encode(pdf_data).decode()
    href = f'{text}'
    return href

# Main app
def main():
    st.title("Advanced Skin Cancer Classification App")
    st.write("Upload an image of a skin lesion for classification")

    # Sidebar for app information and model selection
    st.sidebar.title("About")
    st.sidebar.info(
        "This application uses deep learning to classify skin lesions into 7 different categories. "
        "The model is based on fine-tuned CNN architectures trained on the HAM10000 dataset."
    )

    # FEATURE 1: Multiple Model Support
    st.sidebar.title("Model Selection")
    model_option = st.sidebar.selectbox(
        "Choose a model",
        ["ResNet50", "EfficientNetB3", "Ensemble (Best Performance)"]
    )

    # FEATURE 3: User Feedback Collection
    st.sidebar.title("Feedback")
    st.sidebar.info(
        "After receiving your results, please provide feedback on the prediction accuracy. "
        "This helps us improve the model."
    )

    st.sidebar.title("Instructions")
    st.sidebar.info(
        "1. Upload a skin lesion image\n"
        "2. Select model and options\n"
        "3. View the prediction results and visualization\n"
        "4. Download a detailed report if desired"
    )

    # File uploader
    uploaded_file = st.file_uploader("Choose a skin lesion image...", type=["jpg", "jpeg", "png"])

    # FEATURE 2: Test-Time Augmentation option
    use_tta = st.checkbox("Use Test-Time Augmentation for more robust predictions", value=True)

    # Load models
    @st.cache_resource
    def load_classification_models():
        models = {}
        model_path = 'skin_cancer_model.h5' # Define the model path

        # Check if the model file exists
        if not os.path.exists(model_path):
             st.error(f"Error: Model file '{model_path}' not found.")
             st.stop() # Stop the app if model file is missing

        try:
            models["ResNet50"] = load_model(model_path)
            # Print a success message if loading is successful
            print("ResNet50 model loaded successfully!")
        except Exception as e:
            # Print the specific exception that occurred during loading
            st.error(f"Error loading ResNet50 model from {model_path}: {e}")
            # Do not stop the app here, allow it to continue with placeholder models
            # st.stop() # Stop the app if model loading fails


        # Placeholder for other models - replace with actual model loading
        # Assign placeholder models only if the primary model loading failed
        if "ResNet50" not in models:
             st.warning("ResNet50 model could not be loaded. Using placeholder models.")
             # Create dummy models or assign the base ResNet model if available
             # For simplicity, we can assign the base ResNet model if it was loaded
             # or create a dummy model if needed. Assuming base_model is available if ResNet50 is intended.
             # If base_model is not available, this might need more robust handling.
             # For now, let's assign a dummy model or None if loading fails.
             models["ResNet50"] = None # Indicate failure

        # Assign placeholder models, potentially using the loaded ResNet50 if successful
        models["EfficientNetB3"] = models.get("ResNet50", None)  # Use ResNet50 if loaded, otherwise None
        models["Ensemble (Best Performance)"] = models.get("ResNet50", None) # Use ResNet50 if loaded, otherwise None

        # Check if any models were loaded successfully before returning
        if all(model is None for model in models.values()):
             st.error("All models failed to load. Please check the model file and paths.")
             st.stop() # Stop the app if no models could be loaded


        return models

    models = load_classification_models()

    # Get the selected model
    model = models[model_option]

    # Check if the selected model was loaded successfully
    if model is None:
         st.error(f"The selected model '{model_option}' failed to load. Please try a different model or check the model file.")
         st.stop() # Stop the app if the selected model is None


    # Determine last conv layer name based on model type
    if model_option == "ResNet50":
        last_conv_layer_name = "conv5_block3_out"
    elif model_option == "EfficientNetB3":
        # You need to find the name of the last convolutional layer for EfficientNetB3
        # You can inspect the model summary after loading
        last_conv_layer_name = "top_conv"  # Placeholder - Adjust based on actual layer name
    else:
        last_conv_layer_name = "conv5_block3_out"  # Default for ensemble (assuming ResNet base)


    if uploaded_file is not None:
        # Display original image
        image = Image.open(uploaded_file)
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Original Image")
            st.image(image, caption="Uploaded Image", use_column_width=True)

        # Convert PIL Image to numpy array
        img_array = np.array(image)

        # Preprocess the image
        # The preprocess_image function includes resizing and normalization
        processed_img = preprocess_image(img_array)

        # Make prediction
        input_arr = np.expand_dims(processed_img, axis=0)

        # Apply test-time augmentation if selected
        if use_tta:
            predictions = test_time_augmentation(model, processed_img)
        else:
            predictions = model.predict(input_arr)[0]

        predicted_class_index = np.argmax(predictions)
        predicted_class = class_names[predicted_class_index]
        confidence = predictions[predicted_class_index]

        # Get Grad-CAM heatmap
        # Need to pass the original processed_img (numpy array) to display_gradcam
        heatmap = make_gradcam_heatmap(input_arr, model, last_conv_layer_name, pred_index=predicted_class_index)
        superimposed_img_display = display_gradcam(processed_img, heatmap)


        with col2:
            st.subheader("Model Focus (Grad-CAM)")
            # Ensure the image format is correct for st.image (uint8 numpy array or PIL Image)
            st.image(superimposed_img_display.astype(np.uint8), caption="Areas the model is focusing on", use_column_width=True)


        # Display prediction results
        st.subheader("Prediction Results")
        st.write(f"**Diagnosis:** {predicted_class}")
        st.write(f"**Confidence:** {confidence:.2%}")

        # Display bar chart of all probabilities
        st.subheader("Probability Distribution")
        fig, ax = plt.subplots(figsize=(10, 5))
        y_pos = np.arange(len(class_names))
        ax.barh(y_pos, predictions, align='center')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(class_names)
        ax.invert_yaxis()  # Labels read top-to-bottom
        ax.set_xlabel('Probability')
        ax.set_title('Class Probabilities')

        st.pyplot(fig)
        plt.close(fig) # Close the figure to prevent it from displaying twice

        # FEATURE 3: User Feedback Collection
        st.subheader("Provide Feedback")
        feedback = st.radio(
            "Was this prediction helpful?",
            ["Yes, it seems accurate", "Somewhat helpful", "No, it seems incorrect"],
            key="feedback_radio" # Add a unique key
        )

        additional_feedback = st.text_area("Additional comments (optional):", key="feedback_text") # Add a unique key


        # Combine feedback
        full_feedback = f"Helpfulness: {feedback}\nAdditional comments: {additional_feedback}"

        # FEATURE 4: Educational Information
        st.subheader("About This Condition")
        with st.expander(f"Click to learn more about {predicted_class}"): # Use predicted class in expander title
            st.write(class_descriptions.get(predicted_class, "No description available."))

            # Add example images of this condition
            st.write("**Example images of this condition:**")
            # In a real app, you would load example images for each condition
            st.info("Example images would be displayed here in a production app.")

        # FEATURE 5: Report Generation
        st.subheader("Download Report")
        # Ensure images passed to create_report are in a suitable format (e.g., uint8 numpy array)
        if st.button("Generate PDF Report"):
            # Pass appropriate image data (e.g., denormalized uint8 arrays)
            pdf_data = create_report(
                image_display.astype(np.uint8), # Pass denormalized original image
                superimposed_img_display.astype(np.uint8), # Pass the superimposed image
                predicted_class,
                confidence,
                predictions,
                full_feedback
            )
            st.markdown(get_download_link(pdf_data), unsafe_allow_html=True)

        # Add disclaimer
        st.warning(
            "**Medical Disclaimer:** This tool is for educational purposes only and is not intended to be a substitute "
            "for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other "
            "qualified health provider with any questions you may have regarding a medical condition."
        )

if __name__ == "__main__":
    main()
     
