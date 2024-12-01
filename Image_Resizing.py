from PIL import Image, ImageOps
import os

# Pad naar de map met je afbeeldingen
input_folder = "C:/Users/u309859/Downloads/TrashBox-main/TrashBox_train_dataset_subfolders/glass"
output_folder = "C:/Users/u309859/Downloads/TrashBox-main/TrashBox_train_dataset_subfolders/glassresized"
target_size = (224, 224)  # Gewenste outputgrootte

# Zorg ervoor dat de uitvoermap bestaat
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Doorloop alle afbeeldingen en pas de grootte aan met behoud van aspect ratio en padding
for image_name in os.listdir(input_folder):
    if image_name.endswith(('.png', '.jpg', '.jpeg')):  # Filter alleen afbeeldingen
        image_path = os.path.join(input_folder, image_name)
        with Image.open(image_path) as img:
            # Bepaal de aspect ratio en pas de afbeelding aan
            img.thumbnail(target_size)
            if img.mode in ('RGBA', 'P'):
                img= img.convert('RGB')  # Schaal de afbeelding naar de gewenste grootte terwijl de aspect ratio behouden blijft
            img_padded = ImageOps.pad(img, target_size, color="black")  # Voeg padding toe (zwart)
            img_padded.save(os.path.join(output_folder, image_name))
