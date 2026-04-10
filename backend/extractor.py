import cv2
import os


def extract_frames(video_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    vidcap = cv2.VideoCapture(video_path)

    fps = int(vidcap.get(cv2.CAP_PROP_FPS))
    success, image = vidcap.read()
    count = 0
    frame_paths = []

    while success:
        # Extract exactly one frame per second
        if count % fps == 0:
            frame_name = os.path.join(output_folder, f"frame_{count}.jpg")
            cv2.imwrite(frame_name, image)
            frame_paths.append(frame_name)
        success, image = vidcap.read()
        count += 1

    return frame_paths


# --- ADD THIS BLOCK TO RUN IT DIRECTLY ---
if __name__ == "__main__":
    # 1. Define where your clean video is
    input_video = "official_source.mp4"

    # 2. Define where you want the images to go for training
    output_directory = "training_data"

    if not os.path.exists(input_video):
        print(f"Error: Could not find '{input_video}'. Please put a video file in the project folder.")
    else:
        print(f"Extracting frames from {input_video}...")
        extracted_files = extract_frames(input_video, output_directory)
        print(f"Success! Extracted {len(extracted_files)} frames into the '{output_directory}' folder.")