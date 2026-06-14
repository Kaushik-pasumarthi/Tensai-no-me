import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
import os
from PIL import Image
import random

# Import our U-Net model
from cleaner import SimpleUNetDenoiser


class SyntheticPirateDataset(Dataset):
    """
    This dataset loads clean images and programmatically 'ruins' them
    to simulate pirate attacks (watermarks, compression, noise).
    """

    def __init__(self, clean_image_dir):
        self.image_paths = [os.path.join(clean_image_dir, f) for f in os.listdir(clean_image_dir) if f.endswith('.jpg')]

        # Standardize size for the U-Net
        self.resize = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor()
        ])

    def add_pirate_noise(self, tensor_image):
        """Simulates heavy compression and pirate watermarks."""
        noisy_image = tensor_image.clone()

        # 1. Simulate a pirate watermark (Add a random black box)
        if random.random() > 0.3:  # 70% chance to add a watermark
            c, h, w = noisy_image.shape
            box_h, box_w = 40, 60
            top = random.randint(0, h - box_h)
            left = random.randint(0, w - box_w)
            noisy_image[:, top:top + box_h, left:left + box_w] = 0.0  # Black out a section

        # 2. Simulate random compression noise
        noise = torch.randn_like(noisy_image) * 0.1
        noisy_image = noisy_image + noise
        noisy_image = torch.clamp(noisy_image, 0., 1.)  # Keep pixel values valid

        return noisy_image
#check noisy_image for understanding the parallel tensor split
    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        # Load the clean image
        img_path = self.image_paths[idx]
        clean_img = Image.open(img_path).convert('RGB')
        clean_tensor = self.resize(clean_img)

        # Generate the 'stolen' noisy version
        noisy_tensor = self.add_pirate_noise(clean_tensor)

        return noisy_tensor, clean_tensor


def train_model():
    # 1. Setup the GPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device}")

    # 2. Initialize Model, Loss Function, and Optimizer
    model = SimpleUNetDenoiser().to(device)
    criterion = nn.MSELoss()  # Mean Squared Error (compares pixels)
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    # 3. Load Data
    # IMPORTANT: Create a folder named 'training_data' and put ~50-100 clean sports frames in it
    os.makedirs("training_data", exist_ok=True)
    dataset = SyntheticPirateDataset("training_data")

    if len(dataset) == 0:
        print("Please put some clean .jpg images in the 'training_data' folder to train!")
        return

    dataloader = DataLoader(dataset, batch_size=8, shuffle=True)

    # 4. The Training Loop (Run for 10 epochs for a quick hackathon test)
    epochs = 10
    print("Starting Training Loop...")
    for epoch in range(epochs):
        epoch_loss = 0.0

        for noisy_imgs, clean_imgs in dataloader:
            noisy_imgs = noisy_imgs.to(device)
            clean_imgs = clean_imgs.to(device)

            # Zero the gradients
            optimizer.zero_grad()

            # Forward pass: U-Net tries to clean the noisy image
            outputs = model(noisy_imgs)

            # Calculate how far off the U-Net's guess was from the actual clean image
            loss = criterion(outputs, clean_imgs)

            # Backward pass: Update the weights to learn from the mistake
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()

        print(f"Epoch [{epoch + 1}/{epochs}], Loss: {epoch_loss / len(dataloader):.4f}")

    # 5. Save the trained brain!
    torch.save(model.state_dict(), "unet_denoiser_weights.pth")
    print("Training Complete! Saved weights to 'unet_denoiser_weights.pth'")


if __name__ == "__main__":
    train_model()
