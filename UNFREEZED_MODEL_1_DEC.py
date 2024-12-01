# -*- coding: utf-8 -*-
"""UNFREEZED_MODEL.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1vwZK-70XrZvVY2Gc7rymp_QgWpGvn1wm
"""

# LIBRARIES

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from tensorflow.keras.utils import to_categorical
from keras.models import Sequential
from keras.layers import Flatten, Dense, Dropout
from keras.optimizers import Adam
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from keras.callbacks import ReduceLROnPlateau
from keras.regularizers import l2
import cv2
from google.colab import drive
import torch
from torch.utils.data import Dataset, DataLoader, TensorDataset
import torch.nn as nn
import torchvision.models as models
import torch.nn.functional as F
import torch.optim as optim
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.preprocessing import LabelBinarizer
from sklearn.metrics import roc_curve, auc
from sklearn.metrics import classification_report
from google.colab import files

# IMPORTATION OF THE DATA

# Mount Google Drive
drive.mount('/content/drive')
file_dir = "/content/drive/MyDrive/THESIS/"

X_train_augmented = np.load(file_dir + "X_train_augmented_norm.npy")
y_train_augmented = np.load(file_dir + "y_train_augmented.npy")
X_val = np.load(file_dir + "X_val_norm.npy")
y_val = np.load(file_dir + "y_val.npy")
X_test = np.load(file_dir + "X_test_norm.npy")
y_test = np.load(file_dir + "y_test.npy")

# CONVERT TO PYTORCH TENSORS

train_data_tensor = torch.tensor(X_train_augmented, dtype=torch.float32)
train_labels_tensor = torch.tensor(y_train_augmented, dtype=torch.long)

val_data_tensor = torch.tensor(X_val, dtype=torch.float32)
val_labels_tensor = torch.tensor(y_val, dtype=torch.long)

test_data_tensor = torch.tensor(X_test, dtype=torch.float32)
test_labels_tensor = torch.tensor(y_test, dtype=torch.long)

# CONVERT ONE-HOT ENCODED LABELS

train_labels_tensor = torch.argmax(train_labels_tensor, dim=1)
val_labels_tensor = torch.argmax(val_labels_tensor, dim=1)
test_labels_tensor = torch.argmax(test_labels_tensor, dim=1)

#CREATE DATA LOADERS

train_dataset = TensorDataset(train_data_tensor, train_labels_tensor)
val_dataset = TensorDataset(val_data_tensor, val_labels_tensor)
test_dataset = TensorDataset(test_data_tensor, test_labels_tensor)

train_loader = DataLoader(train_dataset, batch_size=50, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=50, shuffle=False)
test_loader = DataLoader(test_dataset, batch_size=50, shuffle=False)

# PLOT A BATCH OF IMAGES

dataiter = iter(train_loader)
images, labels = next(dataiter)

images = images.numpy()

fig = plt.figure(figsize=(25, 4))
for idx in np.arange(len(images)):
    ax = fig.add_subplot(2, len(images) // 2, idx + 1, xticks=[], yticks=[])
    ax.imshow(np.squeeze(images[idx]), cmap='gray')
    label = labels[idx]
    if label.dim() > 0:
        label = label.argmax().item()
        label = label.item()
    ax.set_title(str(label))

plt.show()

# SHAPE OF A BATCH

dataiter = iter(train_loader)
images, labels = next(dataiter)

images = images.permute(0, 3, 1, 2)

print("Shape van images:", images.shape)
print("Shape van labels:", labels.shape)

# PRETRAINED DENSENET MODEL

class DenseNet121(nn.Module):
    def __init__(self, num_classes=9):
        super(DenseNet121, self).__init__()
        pretrained_densenet = models.densenet121(pretrained=True)
        self.features = pretrained_densenet.features

        # FREEZING ALL LAYERS
        for param in self.features.parameters():
            param.requires_grad = False

        # LAST 30 LAYERS UNFROZEN
        layers_to_train = list(self.features.children())[-30:]
        for layer in layers_to_train:
            for param in layer.parameters():
                param.requires_grad = True

        # DROPOUT
        self.dropout = nn.Dropout2d(0.4)


    def forward(self, x):
        x = x.permute(0, 3, 1, 2)
        x = self.features(x)
        x = self.dropout(x)

        return x

# DUMMY VARIABLE TO TEST PRETRAINED MODEL OUTPUT

dummy_input = torch.randn(50, 224, 224, 3)
conv_layer = DenseNet121()
output = conv_layer(dummy_input)

print("Output shape:", output.shape)

# PRIMARY CAPS OF THE CAPSULE NETWORK

class PrimaryCaps(nn.Module):
    def __init__(self, num_capsules=8, in_channels=1024, out_channels=64):        # CHANGE BASED ON OUTPUT
        super(PrimaryCaps, self).__init__()                                       # OF PRETRAINED
        self.capsules = nn.ModuleList([
            nn.Conv2d(in_channels=in_channels, out_channels=out_channels,
                      kernel_size=5, stride=2, padding=0)
            for _ in range(num_capsules)])

    def forward(self, x):
        batch_size = x.size(0)
        u = [capsule(x).view(batch_size, 64, 2, 2) for capsule in self.capsules]  # CHANGE BASED ON OUTPUT
        u = torch.stack(u, dim=1)                                                 # OF PRETRAINED
        u = u.reshape(batch_size, -1, 8)
        u_squash = self.squash(u)
        return u_squash

    def squash(self, input_tensor):
        squared_norm = (input_tensor ** 2).sum(dim=-1, keepdim=True)
        scale = squared_norm / (1 + squared_norm)
        output_tensor = scale * input_tensor / torch.sqrt(squared_norm)
        return output_tensor

# DUMMY VARIABLE FOR THE PRIMARY CAPSULES
if __name__ == "__main__":
    input_features = torch.randn(50, 1024, 7, 7)
    primary_caps = PrimaryCaps(num_capsules=8, in_channels=1024, out_channels=64)
    output_capsules = primary_caps(input_features)

    print("Output shape van capsules:", output_capsules.shape)

# HELPERS.PY FOR SOFTMAX FUNCTION

with open('helpers.py', 'w') as f:
    f.write("""import torch
import torch.nn.functional as F

def softmax(input_tensor, dim=1):
    # Transpose input
    transposed_input = input_tensor.transpose(dim, len(input_tensor.size()) - 1)

    # Calculate softmax
    softmaxed_output = F.softmax(transposed_input.contiguous().view(-1, transposed_input.size(-1)), dim=-1)

    # Un-transpose result
    return softmaxed_output.view(*transposed_input.size()).transpose(dim, len(input_tensor.size()) - 1)
""")

import helpers

# DYNAMIC ROUTING

def dynamic_routing(b_ij, u_hat, squash, routing_iterations=3):
    for iteration in range(routing_iterations):
        c_ij = helpers.softmax(b_ij, dim=2)
        s_j = (c_ij * u_hat).sum(dim=2, keepdim=True)
        v_j = squash(s_j)
        if iteration < routing_iterations - 1:
            a_ij = (u_hat * v_j).sum(dim=-1, keepdim=True)
            b_ij = b_ij + a_ij
    return v_j

# TRAIN ON GPU OR CPU

TRAIN_ON_GPU = torch.cuda.is_available()
if(TRAIN_ON_GPU):
    print('Training on GPU!')
else:
    print('Only CPU available')

#DIGITCAPS OF THE CAPSULE NETWORK

class DigitCaps(nn.Module):
    def __init__(self, num_capsules=9, previous_layer_nodes=256,                  # CHANGE BASED ON OUTPUT
                 in_channels=8, out_channels=16):                                 # OF PRIMARY CAPS
        super(DigitCaps, self).__init__()
        self.num_capsules = num_capsules
        self.previous_layer_nodes = previous_layer_nodes
        self.in_channels = in_channels
        self.W = nn.Parameter(torch.randn(num_capsules, previous_layer_nodes,
                                          in_channels, out_channels))

    def forward(self, u):
        u = u[None, :, :, None, :]
        W = self.W[:, None, :, :, :]
        u_hat = torch.matmul(u, W)
        b_ij = torch.zeros(*u_hat.size())
        if TRAIN_ON_GPU:
            b_ij = b_ij.cuda()
        v_j = dynamic_routing(b_ij, u_hat, self.squash, routing_iterations=3)
        return v_j

    def squash(self, input_tensor):
        squared_norm = (input_tensor ** 2).sum(dim=-1, keepdim=True)
        scale = squared_norm / (1 + squared_norm)
        output_tensor = scale * input_tensor / torch.sqrt(squared_norm)
        return output_tensor

#DUMMY VARIABLE FOR THE DIGITCAPS

batch_size = 25
primary_caps_output = torch.randn(batch_size, 256, 8)
digit_caps = DigitCaps(num_capsules=9, previous_layer_nodes=256, in_channels=8, out_channels=16)
if torch.cuda.is_available():
    digit_caps = digit_caps.cuda()
    primary_caps_output = primary_caps_output.cuda()

digit_caps_output = digit_caps(primary_caps_output)

print("Output shape van DigitCaps:", digit_caps_output.shape)

# THE FULL CAPSULE NETWORK

class CapsuleNetwork(nn.Module):
    def __init__(self, num_classes):
        super(CapsuleNetwork, self).__init__()
        self.conv_layer = DenseNet121()
        self.primary_capsules = PrimaryCaps()
        self.digit_capsules = DigitCaps()

    def forward(self, x):
        primary_caps_output = self.primary_capsules(self.conv_layer(x))
        caps_output = self.digit_capsules(primary_caps_output).squeeze().transpose(0, 1)
        return caps_output

# FULL CAPSULE NETWORK ARCHITECTURE
num_classes = 9
capsule_net = CapsuleNetwork(num_classes)

print(capsule_net)

if TRAIN_ON_GPU:
    capsule_net = capsule_net.cuda()

#CAPSULE LOSS FUNCTION

class CapsuleLoss(nn.Module):

    def __init__(self):
        super(CapsuleLoss, self).__init__()

    def forward(self, x, labels):
        batch_size = x.size(0)
        v_c = torch.sqrt((x**2).sum(dim=2, keepdim=True))
        left = F.relu(0.9 - v_c).view(batch_size, -1)
        right = F.relu(v_c - 0.1).view(batch_size, -1)
        margin_loss = labels * left + 0.5 * (1. - labels) * right
        margin_loss = margin_loss.sum()
        return margin_loss / batch_size

# LOSS FUNCTION AND OPTIMIZER FOR TRAINING

criterion = CapsuleLoss()

optimizer = torch.optim.Adam(capsule_net.parameters(), lr=0.0001, weight_decay=0.0001)

# TRAIN AND VALIDATE CAPSULE NETWORK

def train_and_validate(capsule_net, criterion, optimizer, n_epochs, train_loader, val_loader, patience=10, print_every=300):
    train_losses = []
    val_losses = []
    train_accuracies = []
    val_accuracies = []
    best_val_loss = float('inf')
    no_improvement = 0

    for epoch in range(1, n_epochs + 1):
        train_loss = 0.0
        correct = 0
        total = 0
        capsule_net.train()

        for batch_i, (images, target) in enumerate(train_loader):
            one_hot_target = torch.eye(9)[target]
            if TRAIN_ON_GPU:
                images, target = images.cuda(), target.cuda()
                one_hot_target = one_hot_target.cuda()

            optimizer.zero_grad()
            caps_output = capsule_net(images)
            loss = criterion(caps_output, one_hot_target)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

            # ACCURACY
            caps_output_magnitudes = torch.sqrt((caps_output**2).sum(dim=2))
            _, predicted = torch.max(caps_output_magnitudes, 1)
            total += target.size(0)
            correct += (predicted == target).sum().item()

            if (batch_i + 1) % print_every == 0:
                avg_train_loss = train_loss / print_every
                print(f'Epoch: {epoch} \tTraining Loss: {avg_train_loss:.8f}')
                train_loss = 0
                correct = 0
                total = 0

        epoch_train_loss = train_loss / len(train_loader)
        train_losses.append(epoch_train_loss)
        epoch_train_accuracy = 100 * correct / total
        train_accuracies.append(epoch_train_accuracy)
        print(f"Epoch {epoch} Accuracy: {epoch_train_accuracy:.2f}%")

        avg_val_loss, val_accuracy = validate(capsule_net, criterion, val_loader)
        val_losses.append(avg_val_loss)
        val_accuracies.append(val_accuracy)

        # EARLY STOPPING
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            no_improvement = 0
            torch.save(capsule_net.state_dict(), 'best_model.pth')
            print(f'Best model saved with validation loss: {best_val_loss:.8f} and accuracy: {val_accuracy:.2f}%')
        else:
            no_improvement += 1

        if no_improvement >= patience:
            print(f"Early stopping triggered at epoch {epoch}. No improvement in validation loss for {patience} epochs.")
            break

    return train_losses, train_accuracies, val_losses, val_accuracies

# VALIDATE CAPSULE NETWORK

def validate(capsule_net, criterion, val_loader):
    capsule_net.eval()
    val_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for images, target in val_loader:
            one_hot_target = torch.eye(9)[target]
            if TRAIN_ON_GPU:
                images, target = images.cuda(), target.cuda()
                one_hot_target = one_hot_target.cuda()

            caps_output = capsule_net(images)
            loss = criterion(caps_output, one_hot_target)
            val_loss += loss.item()

            caps_output_magnitudes = torch.sqrt((caps_output**2).sum(dim=2))
            _, predicted = torch.max(caps_output_magnitudes, 1)
            total += target.size(0)
            correct += (predicted == target).sum().item()

    avg_val_loss = val_loss / len(val_loader)
    val_accuracy = 100 * correct / total
    print(f'Validation Loss: {avg_val_loss:.8f} \tValidation Accuracy: {val_accuracy:.2f}%')

    return avg_val_loss, val_accuracy

# TRAIN AND VALIDATE THE CAPSULE NETWORK

n_epochs = 100
train_losses, train_accuracies, val_losses, val_accuracies = train_and_validate(capsule_net, criterion, optimizer, n_epochs, train_loader, val_loader)

# CONFUSION MATRIX FOR THE VALIDATION SET

def generate_confusion_matrix(capsule_net, val_loader):
    capsule_net.eval()
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for images, targets in val_loader:
            if TRAIN_ON_GPU:
                images, targets = images.cuda(), targets.cuda()
            outputs = capsule_net(images)
            caps_output_magnitudes = torch.sqrt((outputs**2).sum(dim=2))
            _, preds = torch.max(caps_output_magnitudes, 1)
            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(targets.cpu().numpy())

    cm = confusion_matrix(all_targets, all_preds)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=range(9), yticklabels=range(9))
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title("Confusion Matrix")
    plt.show()

generate_confusion_matrix(capsule_net, val_loader)

# TRAINING AND VALIDATION ACCURACY/LOSS

def plot_training_validation_graphs(train_losses, train_accuracies, val_losses, val_accuracies):
    plt.figure(figsize=(12, 6))

    # Loss Plot
    plt.subplot(1, 2, 1)
    plt.plot(train_losses, label='Training Loss')
    plt.plot(val_losses, label='Validation Loss')
    plt.title('Training and Validation Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()

    # Accuracy Plot
    plt.subplot(1, 2, 2)
    plt.plot(train_accuracies, label='Training Accuracy')
    plt.plot(val_accuracies, label='Validation Accuracy')
    plt.title('Training and Validation Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy (%)')
    plt.legend()

    plt.tight_layout()
    plt.show()

plot_training_validation_graphs(train_losses, train_accuracies, val_losses, val_accuracies)

# CLASSIFICATION REPORT FOR THE TEST SET

def generate_classification_report(capsule_net, test_loader):
    capsule_net.eval()
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for images, targets in test_loader:
            if TRAIN_ON_GPU:
                images, targets = images.cuda(), targets.cuda()
            outputs = capsule_net(images)
            caps_output_magnitudes = torch.sqrt((outputs**2).sum(dim=2))
            _, preds = torch.max(caps_output_magnitudes, 1)
            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(targets.cpu().numpy())

    report = classification_report(all_targets, all_preds, target_names=[str(i) for i in range(9)], digits=4)
    print("Classification Report:\n", report)

generate_classification_report(capsule_net, test_loader)

# EXTRA METRICS FOR THE TEST SET

def calculate_metrics(y_true, y_pred):
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, average='weighted', zero_division=1)
    recall = recall_score(y_true, y_pred, average='weighted', zero_division=1)
    f1 = f1_score(y_true, y_pred, average='weighted', zero_division=1)
    return accuracy, precision, recall, f1

# CONFUSION MATRIX
def plot_confusion_matrix(y_true, y_pred, class_labels):
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=class_labels, yticklabels=class_labels)
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.title('Confusion Matrix')
    plt.show()

# MULTI-CLASS ROC CURVE
def plot_multi_class_roc_curves(y_true, y_pred, n_classes):
    lb = LabelBinarizer()
    y_true_bin = lb.fit_transform(y_true)

    fpr, tpr, roc_auc = {}, {}, {}
    for i in range(n_classes):
        fpr[i], tpr[i], _ = roc_curve(y_true_bin[:, i], y_pred[:, i])
        roc_auc[i] = auc(fpr[i], tpr[i])

    plt.figure(figsize=(10, 8))
    for i in range(n_classes):
        plt.plot(fpr[i], tpr[i], label=f'Class {i+1} (AUC = {roc_auc[i]:.2f})')

    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Multi-Class ROC Curve')
    plt.legend(loc='lower right')
    plt.show()

# TEST SET EVALUATION
def evaluate_test_set(capsule_net, test_loader):
    capsule_net.eval()
    y_true_classes = []
    y_pred_classes = []
    y_pred_probabilities = []

    with torch.no_grad():
        for images, targets in test_loader:
            one_hot_target = torch.eye(9)[targets]
            if TRAIN_ON_GPU:
                images, targets = images.cuda(), targets.cuda()
                one_hot_target = one_hot_target.cuda()

            outputs = capsule_net(images)

            caps_output_magnitudes = torch.sqrt((outputs**2).sum(dim=2))
            probs = torch.nn.functional.softmax(caps_output_magnitudes, dim=1)

            _, predicted = torch.max(caps_output_magnitudes, 1)
            y_true_classes.extend(targets.cpu().numpy())
            y_pred_classes.extend(predicted.cpu().numpy())
            y_pred_probabilities.extend(probs.cpu().numpy())

    accuracy, precision, recall, f1 = calculate_metrics(y_true_classes, y_pred_classes)

    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1 Score: {f1:.4f}")

    class_labels = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
    plot_confusion_matrix(y_true_classes, y_pred_classes, class_labels)

    plot_multi_class_roc_curves(y_true_classes, np.array(y_pred_probabilities), n_classes=9)

evaluate_test_set(capsule_net, test_loader)

# SAVING THE RESULTS

def save_classification_report(capsule_net, test_loader, model_name, file_path):
    capsule_net.eval()
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for images, targets in test_loader:
            if TRAIN_ON_GPU:
                images, targets = images.cuda(), targets.cuda()
            outputs = capsule_net(images)
            caps_output_magnitudes = torch.sqrt((outputs**2).sum(dim=2))
            _, preds = torch.max(caps_output_magnitudes, 1)
            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(targets.cpu().numpy())

    report = classification_report(all_targets, all_preds, target_names=[str(i) for i in range(9)], digits=4, output_dict=True)

    report_data = []
    for label, metrics in report.items():
        if label not in ['accuracy', 'macro avg', 'weighted avg']:
            report_data.append({
                'model': model_name,
                'label': label,
                'precision': metrics['precision'],
                'recall': metrics['recall'],
                'f1-score': metrics['f1-score'],
                'support': metrics['support']
            })

    df = pd.DataFrame(report_data)
    df.to_csv(file_path, mode='a', header=not pd.io.common.file_exists(file_path), index=False)
    files.download(file_path)

save_classification_report(capsule_net, test_loader, 'CapsNet_Model_3', '/content/classification_reports.csv')