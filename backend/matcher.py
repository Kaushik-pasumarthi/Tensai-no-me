import faiss
import numpy as np

class VideoMatcher:
    def __init__(self, vector_dimension=2048):
        self.dimension = vector_dimension
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = {}
        self.current_id = 0

    def _normalize(self, vector):
        vec = np.array(vector, dtype='float32')
        if len(vec.shape) == 1:
            vec = np.expand_dims(vec, axis=0)
        faiss.normalize_L2(vec)
        return vec

    def add_official_video(self, video_name, frame_embeddings):
        for frame_number, embedding in enumerate(frame_embeddings):
            norm_embedding = self._normalize(embedding)
            self.index.add(norm_embedding)
            self.metadata[self.current_id] = {
                "video_name": video_name,
                "frame_number": frame_number
            }
            self.current_id += 1
        print(f"Added {len(frame_embeddings)} frames from '{video_name}' to the vault.")

    def query_suspect_frame(self, suspect_embedding, threshold=0.65):
        norm_embedding = self._normalize(suspect_embedding)
        distances, indices = self.index.search(norm_embedding, k=1)

        best_score = float(distances[0][0])
        best_match_id = int(indices[0][0])

        if best_score > threshold and best_match_id != -1:
            match_info = self.metadata[best_match_id]
            return {
                "match_found": True,
                "confidence": best_score,
                "matched_video": match_info["video_name"],
                "matched_frame_number": match_info["frame_number"]
            }

        return {
            "match_found": False,
            "confidence": best_score if best_match_id != -1 else 0.0
        }

    def temporal_sequence_alignment(self, suspect_embeddings, reference_embeddings):
        n = len(suspect_embeddings)
        m = len(reference_embeddings)
        dp = np.zeros((n + 1, m + 1), dtype=int)
        max_len = 0
        end_idx = 0

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                vec1 = self._normalize(suspect_embeddings[i - 1])
                vec2 = self._normalize(reference_embeddings[j - 1])
                similarity = np.dot(vec1[0], vec2[0])

                if similarity > 0.85:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                    if dp[i][j] > max_len:
                        max_len = dp[i][j]
                        end_idx = i
                else:
                    dp[i][j] = 0

        return max_len, end_idx