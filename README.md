# Skin Cancer Classification 

A deep learning project for accurate identification of skin cancer using the powerful RESNET50 model.  
Designed for AI/ML and bioinformatics professionals, researchers, and enthusiasts aiming to advance medical diagnostics with state-of-the-art computer vision.

---

## 📚 Table of Contents

- [About](#about)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Deployment](#deployment)
- [App Demo](#app-demo)
- [Contributing](#contributing)
- [License](#license)

---

## 📝 About

**Skin Cancer Classification** leverages the RESNET50 convolutional neural network to identify skin cancer from image data.  
It integrates advanced techniques like GRAD-CAM for model interpretability and provides rich data visualization for insightful analysis.  
This project is tailored for the AI/ML bioinformatics community, aiming to accelerate research and deployment of accurate diagnostic tools.

---

## ✨ Features

- 🏥 **Skin Cancer Detection** using transfer learning with RESNET50
- 🔍 **Model Explainability** via GRAD-CAM visualizations
- 📊 **Comprehensive Data Visualization** for dataset insights and results analysis
- 🚀 **Deployed Web App** for easy and interactive usage
- 📄 **PDF Reporting** generate and download diagnostic reports
- 🔄 **Test-Time Augmentation** for robust predictions

---

## 📦 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/skin-cancer-classification.git
   cd skin-cancer-classification
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Usage

### 1. Setup Model
You need a trained model file (`skin_cancer_model.h5`) to run the app.

**Option A: Create a Dummy Model (For Testing)**
If you don't have the dataset but want to test the app UI and functionality:
```bash
python create_dummy_model.py
```
This will generate a lightweight `skin_cancer_model.h5` compatible with the app.

**Option B: Train on HAM10000 Dataset**
1. Download the [HAM10000 dataset](https://www.kaggle.com/datasets/kmader/skin-cancer-mnist-ham10000) and extract it to a `ham10000` folder.
2. Run the training script:
   ```bash
   python train.py
   ```

### 2. Run the App
Launch the Streamlit web app:
```bash
streamlit run app.py
```
The app will open in your default browser at `http://localhost:8501`.

---

## ☁️ Deployment

To deploy this app to **Streamlit Community Cloud**:

1. Push this repository to GitHub.
2. Log in to [Streamlit Community Cloud](https://streamlit.io/cloud).
3. Click "New App".
4. Select your repository, branch, and main file path (`app.py`).
5. Click "Deploy".

*Note: Ensure `requirements.txt` is present in the repository so Streamlit Cloud can install the necessary packages.*

---

## 🎬 App Demo

Check out the deployed web application for hands-on testing and exploration!  
[Live App Link](#) <!-- Add your deployed app URL here -->

---

## 🤝 Contributing

Contributions, issues and feature requests are welcome!  
If you'd like to add features, improve documentation, or report bugs, please open an issue or submit a pull request.

> **Note:** By contributing, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 📝 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙌 Acknowledgements

- Inspired by ongoing research in medical imaging and AI for healthcare.
- Built with Python, TensorFlow/Keras, and Streamlit.
- Special thanks to the open-source datasets and contributors to the tools used in this project.
