import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Conv2D, GlobalAveragePooling2D, Dense
import numpy as np
import os

def create_dummy_model():
    print("Creating dummy model...")
    # Create a simple model that matches the expected input/output
    input_shape = (224, 224, 3)
    num_classes = 7

    inputs = Input(shape=input_shape)
    # A few conv layers to make it look like a CNN, but very small
    x = Conv2D(16, (3, 3), activation='relu', padding='same')(inputs)
    x = Conv2D(32, (3, 3), activation='relu', padding='same')(x)

    # We need a layer named "conv5_block3_out" for Grad-CAM to work in app.py
    # This is the standard name in ResNet50. We'll name our last conv layer this.
    x = Conv2D(64, (3, 3), activation='relu', padding='same', name='conv5_block3_out')(x)

    x = GlobalAveragePooling2D()(x)
    outputs = Dense(num_classes, activation='softmax')(x)

    model = Model(inputs=inputs, outputs=outputs)
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

    model.summary()

    # Save the model
    model.save('skin_cancer_model.h5')
    print("Dummy model saved to 'skin_cancer_model.h5'")

if __name__ == "__main__":
    create_dummy_model()
