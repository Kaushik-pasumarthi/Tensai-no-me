import faiss
import numpy as np


class VideoMatcher:
    def __init__(self, vector_dimension=2048):
        self.dimension = vector_dimension

        # We use IndexFlatIP (Inner Product).
        # When we normalize our vectors, Inner Product becomes exactly Cosine Similarity.
        self.index = faiss.IndexFlatIP(self.dimension)

        # A dictionary to map the FAISS internal ID back to our actual video and frame data
        self.metadata = {}
        self.current_id = 0

    def _normalize(self, vector):
        """Normalizes a vector so its magnitude is 1. Crucial for Cosine Similarity."""
        # Ensure it's a 2D numpy array for FAISS
        vec = np.array(vector, dtype='float32')
        if len(vec.shape) == 1:
            vec = np.expand_dims(vec, axis=0)
        faiss.normalize_L2(vec)
        return vec

    def add_official_video(self, video_name, frame_embeddings):
        """Loads the official 'Vault' vectors into the FAISS database."""
        for frame_number, embedding in enumerate(frame_embeddings):
            norm_embedding = self._normalize(embedding)

            # Add to FAISS index
            self.index.add(norm_embedding)

            # Store metadata so we know exactly which video/frame this vector belongs to
            self.metadata[self.current_id] = {
                "video_name": video_name,
                "frame_number": frame_number
            }
            self.current_id += 1

        print(f"Added {len(frame_embeddings)} frames from '{video_name}' to the vault.")

    def query_suspect_frame(self, suspect_embedding, threshold=0.85):
        """Checks a single suspect frame against the entire official vault."""
        norm_embedding = self._normalize(suspect_embedding)

        # Search for the top 1 closest match (k=1)
        distances, indices = self.index.search(norm_embedding, k=1)

        best_score = distances[0][0]
        best_match_id = indices[0][0]

        # If the closest match is above our confidence threshold
        if best_score > threshold and best_match_id != -1:
            match_info = self.metadata[best_match_id]
            return {
                "match_found": True,
                "confidence": float(best_score),  # e.g., 0.92 = 92% match
                "matched_video": match_info["video_name"],
                "matched_frame_number": match_info["frame_number"]
            }

        return {"match_found": False}

    def temporal_sequence_alignment(self, suspect_embeddings, reference_embeddings):
        """
        The 'Secret Sauce': A dynamic programming approach to find the longest
        continuous sequence of matched frames, defeating temporal pirate attacks.
        """
        n = len(suspect_embeddings)
        m = len(reference_embeddings)

        # Create a DP table to track the longest matching sequence
        dp = np.zeros((n + 1, m + 1), dtype=int)

        max_len = 0
        end_idx = 0

        # Standard LCS-style traversal optimized for vector similarity
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                # Calculate similarity between suspect frame i-1 and reference frame j-1
                vec1 = self._normalize(suspect_embeddings[i - 1])
                vec2 = self._normalize(reference_embeddings[j - 1])

                # Manual inner product for the DP comparison
                similarity = np.dot(vec1[0], vec2[0])

                if similarity > 0.85:  # If frames match
                    dp[i][j] = dp[i - 1][j - 1] + 1
                    if dp[i][j] > max_len:
                        max_len = dp[i][j]
                        end_idx = i
                else:
                    dp[i][j] = 0

        return max_len, end_idx