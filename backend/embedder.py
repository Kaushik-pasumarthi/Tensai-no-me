import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import cv2

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
            # Activate the trained brain!
            self.cleaner.load_state_dict(torch.load("unet_denoiser_weights.pth"))
            print("Selective Enhancement U-Net Loaded.")

        # 3. Preprocessing steps
        self.preprocess = transforms.Compose([
            transforms.Resize((224, 224)),  # Force strict dimensions for U-Net
            transforms.ToTensor(),
        ])

        # ResNet expects specific normalization
        self.normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

    def get_embedding(self, frame_path):
        image = cv2.imread(frame_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image)

        # Preprocess to tensor
        input_tensor = self.preprocess(pil_image)
        input_batch = input_tensor.unsqueeze(0).to(self.device)

        with torch.no_grad():
            # Apply the U-Net Cleaner if enabled
            if self.use_cleaner:
                # The U-Net strips away the noise and returns a clean tensor
                cleaned_batch = self.cleaner(input_batch)
                # Normalize the cleaned output for ResNet
                final_input = self.normalize(cleaned_batch)
            else:
                final_input = self.normalize(input_batch)

            # Generate the fingerprint
            output = self.model(final_input)

        embedding = output.squeeze().cpu().numpy()
        return embedding