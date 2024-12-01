# -*- coding: utf-8 -*-
"""PREPROCESSING_MEDICAL_WASTE.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1nng3XlyHQ547PZgT1a9SuQlTc-svTyBU
"""

# LIBRARIES

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tensorflow.keras.utils import to_categorical
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import seaborn as sns
from tqdm import tqdm
from scipy.ndimage import rotate, zoom
from PIL import Image, ImageEnhance

# IMPORTATION OF THE DATA

from google.colab import drive
drive.mount('/content/drive')

#loading the data

file_dir = "/content/drive/MyDrive/THESIS/"
data = np.load(file_dir + "imagesII.npy")
labels = np.load(file_dir + "labelsII.npy", allow_pickle=True)
print(labels)

integer_labels = LabelEncoder().fit_transform(labels)
y_set = to_categorical(integer_labels)

# PLOTTING THE IMAGES

random_numbers = np.random.randint(0, 18956, size=15)
fig, axes = plt.subplots(3, 5, figsize=(10, 6))
flattened_axes = axes.flatten()

for i, pt in enumerate(flattened_axes):
    pt.imshow(data[random_numbers[i]], cmap=plt.get_cmap('gray'))
    pt.axis('off')
    pt.set_title(labels[random_numbers[i]], fontsize=6)

plt.show()

# PLOTTING THE DATA PRIOR TO DATA AUGMENTATION

unique_labels, label_counts = np.unique(labels, return_counts=True)

sns.set_theme(style="white")
bar_color = "#87CEEB"

plt.figure(figsize=(8, 6))
bars = plt.bar(unique_labels, label_counts, color=bar_color)

for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width() / 2, height + 1,
             f'{height}', ha='center', va='bottom', fontsize=10)

plt.ylabel('Number of Samples', fontsize=12)
plt.xlabel('Classes', fontsize=12)
plt.title('Distribution of the Classes', fontsize=14, fontweight='bold')
plt.xticks(rotation=45, ha='right', fontsize=10)
plt.yticks(fontsize=10)

plt.grid(axis='y', linestyle='--', alpha=0.7)

plt.tight_layout()
plt.show()

plt.savefig('class_distribution.png', format='png', dpi=300)

# SPLITTING THE DATA

X_trainval, X_test, y_trainval, y_test = train_test_split(data, y_set, test_size = 0.15, stratify= y_set, random_state = 42)
X_train, X_val, y_train, y_val = train_test_split(X_trainval, y_trainval, test_size = 0.1765, stratify=y_trainval, random_state = 42)

print(X_train.shape)
print(X_test.shape)
print(X_val.shape)
print(y_train.shape)
print(y_test.shape)
print(y_val.shape)

# DATA AUGMENTATION

def augment_specific_classes(dataset: list, target_classes: dict, augment_factors: dict, rotation_angles: list = None, scaling_factors: list = None, brightness_range: tuple = None, contrast_range: tuple = None):
    augmented = []

    for image, label in tqdm(dataset, desc="Augmenting Specific Classes"):
        class_index = np.argmax(label)
        if class_index in target_classes:
            factor = augment_factors[class_index]

            for _ in range(factor):
                augmented_image = np.copy(image)
                augmented_image = np.fliplr(augmented_image)
                if rotation_angles:
                    angle = np.random.choice(rotation_angles)
                    augmented_image = rotate(augmented_image, angle, reshape=False)
                if scaling_factors:
                    scale_factor = np.random.choice(scaling_factors)
                    height, width = augmented_image.shape[:2]
                    scaled_image = zoom(augmented_image, (scale_factor, scale_factor, 1))

                    if scale_factor > 1:
                        start_h = (scaled_image.shape[0] - height) // 2
                        start_w = (scaled_image.shape[1] - width) // 2
                        augmented_image = scaled_image[start_h:start_h + height, start_w:start_w + width]
                    else:
                        padded_image = np.zeros_like(augmented_image)
                        start_h = (height - scaled_image.shape[0]) // 2
                        start_w = (width - scaled_image.shape[1]) // 2
                        padded_image[start_h:start_h + scaled_image.shape[0], start_w:start_w + scaled_image.shape[1]] = scaled_image
                        augmented_image = padded_image
                new_label = np.zeros_like(label)
                new_label[class_index] = 1

                augmented.append((augmented_image, new_label))
    return augmented

target_classes = [1, 2]
augment_factors = {1: 1, 2: 2}
rotation_angles = [15, -15]   # ROTATE WITH -15% ANGLE OR 15% ANGLE
scaling_factors = [0.8, 1.2]  # RESIZE TO 80% AND 120%

dataset_with_labels = list(zip(X_train, y_train))

augmented_dataset = augment_specific_classes(dataset_with_labels, target_classes, augment_factors, rotation_angles, scaling_factors)

X_train_augmented = np.concatenate((X_train, [img[0] for img in augmented_dataset]), axis=0)
y_train_augmented = np.concatenate((y_train, [img[1] for img in augmented_dataset]), axis=0)
print(X_train_augmented.shape)
print(y_train_augmented.shape)

# PLOT AUGMENTED IMAGES

def show_augmented_images(augmented_dataset, num_images=5):
    fig, axes = plt.subplots(1, num_images, figsize=(15, 5))
    indices = np.random.choice(len(augmented_dataset), num_images, replace=False)

    for i, idx in enumerate(indices):
        image, label = augmented_dataset[idx]
        axes[i].imshow(image)
        axes[i].set_title(f'Class: {np.argmax(label)}')
        axes[i].axis('off')

    plt.show()

show_augmented_images(augmented_dataset, num_images=5)

# PLOTTING THE DATA PRIOR TO DATA AUGMENTATION

unique_labels, label_counts = np.unique(y_train_augmented.argmax(axis=1), return_counts=True)

class_labels = ['Glass', 'Gloves', 'Masks', 'Medicines', 'Metal', 'Organic', 'Paper', 'Plastic', 'Syringes']

bar_color = "#87CEEB"

plt.figure(figsize=(8, 6))
bars = plt.bar(unique_labels, label_counts, color=bar_color)

for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width() / 2, height + 1,
             f'{height}', ha='center', va='bottom', fontsize=10)

plt.ylabel('Number of Samples', fontsize=12)
plt.xlabel('Classes', fontsize=12)
plt.title('Distribution of the Classes in Augmented Training Set', fontsize=14, fontweight='bold')
plt.xticks(unique_labels, class_labels, rotation=45, ha='right', fontsize=10)
plt.yticks(fontsize=10)

plt.grid(axis='y', linestyle='--', alpha=0.7)

plt.tight_layout()
plt.show()

# PLOTTING IMAGES

def show_images(images, labels, title):
    plt.figure(figsize=(15, 5))
    for i in range(len(images)):
        plt.subplot(1, len(images), i + 1)
        plt.imshow(images[i])
        plt.axis('off')

        label_index = np.argmax(labels[i])
        plt.title(f'Class: {label_index}', fontsize=10)

    plt.suptitle(title)
    plt.show()

def show_random_images(images, labels, title, num_images=5):
    random_indices = np.random.choice(len(images), num_images, replace=False)

    random_images = images[random_indices]
    random_labels = labels[random_indices]

    show_images(random_images, random_labels, title)

X_train_augmented_norm = X_train_augmented.astype('float32') / 255.0
X_test_norm = X_test.astype('float32') / 255.0
X_val_norm = X_val.astype('float32') / 255.0

show_random_images(X_train_augmented_norm, y_train_augmented, title="Random Images - After Normalization - Training Set")
show_random_images(X_test_norm, y_test, title="Random Images - After Normalization - Test Set")
show_random_images(X_val_norm, y_val, title="Random Images - After Normalization - Val Set")

# SAVE THE IMAGES

from google.colab import drive
save_path = '/content/drive/MyDrive/THESIS/'
np.save(save_path + 'X_train_augmented_norm.npy', X_train_augmented_norm)
np.save(save_path + 'X_test_norm.npy', X_test_norm)
np.save(save_path + 'X_val_norm.npy', X_val_norm)
np.save(save_path + 'y_train_augmented.npy', y_train_augmented)
np.save(save_path + 'y_test.npy', y_test)
np.save(save_path + 'y_val.npy', y_val)