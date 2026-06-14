import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import cv2
import numpy as np

# Import our new U-Net cleaner
from cleaner import SimpleUNetDenoiser

class VideoFingerprinter:
    def __init__(self, use_cleaner=True):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Running ML on: {self.device}")

        # 1. Load the core ResNet Extractor
        base_model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        self.model = torch.nn.Sequential(*list(base_model.children())[:-1])
        self.model = self.model.to(self.device)
        self.model.eval()

        # 2. Load our Selective Enhancer (U-Net)
        self.use_cleaner = use_cleaner
        if self.use_cleaner:
            self.cleaner = SimpleUNetDenoiser().to(self.device)
            self.cleaner.eval()
            self.cleaner.load_state_dict(torch.load("unet_denoiser_weights.pth"))
            print("Selective Enhancement U-Net Loaded.")

        # 3. Preprocessing steps
        self.preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
        ])
        self.normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

    def get_embedding(self, frame_path):
        raw_image = cv2.imread(frame_path)

        # --- LAYER 1: VISUAL SANITIZER (CLAHE) ---
        # Strip color and normalize lighting, but KEEP the full spatial geometry!
        gray = cv2.cvtColor(raw_image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced_gray = clahe.apply(gray)
        image_rgb = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2RGB)
        # -----------------------------------------

        pil_image = Image.fromarray(image_rgb)
        #this layer helps process the tensors, so if u face problems in frame getting unobserved of-sorts..look herre
        # Preprocess to tensor
        input_tensor = self.preprocess(pil_image)
        input_batch = input_tensor.unsqueeze(0).to(self.device)

        with torch.no_grad():
            if self.use_cleaner:
                cleaned_batch = self.cleaner(input_batch)
                final_input = self.normalize(cleaned_batch)
            else:
                final_input = self.normalize(input_batch)

            output = self.model(final_input)

        embedding = output.squeeze().cpu().numpy()
        return embedding
