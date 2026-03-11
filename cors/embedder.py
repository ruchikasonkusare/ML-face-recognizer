import json
import os
import numpy as np
from deepface import DeepFace

FINGERPRINT_FILE="data/fingerprints.json"

def load_existing_fingerprints(filepath=FINGERPRINT_FILE):
    """Load fingerprints and deduplicate automatically."""
    
    # if file doesn't exist, return empty list
    if not os.path.exists(filepath):
        print("Starting fresh")
        return []   # ← must return [] not None

    try:
        with open(filepath, "r") as f:
            data = json.load(f)

        # if file is empty or corrupt, return empty list
        if not data:
            print("Empty fingerprints file, starting fresh")
            return []   # ← must return [] not None

        # deduplicate
        seen = set()
        unique = []
        for f in data:
            key = f"{f['filename']}_{f['face_index']}"
            if key not in seen:
                seen.add(key)
                unique.append(f)

        removed = len(data) - len(unique)
        if removed > 0:
            print(f"Removed {removed} duplicates")

        print(f"Loaded {len(unique)} fingerprints")
        return unique

    except Exception as e:
        print(f"Error loading fingerprints: {e}")
        return []   # ← always return [] on any error
    
    
def save_fingerprints(fingerprints, filepath=FINGERPRINT_FILE):

    seen = set()
    unique = []
    for f in fingerprints:
        key = f"{f['filename']}_{f['face_index']}"
        if key not in seen:
            seen.add(key)
            unique.append(f)

    os.makedirs("data", exist_ok=True)
    
    with open(filepath, "w") as f:
        json.dump(unique, f)
    print(f"Saved {len(unique)} fingerprints to {filepath}")
    
    return unique 
    
def get_already_processed(fingerprints):
    
    return set(f["filename"] for f in fingerprints)


def process_one_image(image_path,file_id):
    filename=os.path.basename(image_path)
    print(filename )
    print(f" Processing:{filename}")
    
    try:
        results = DeepFace.represent(
            img_path=image_path,
            model_name="ArcFace",
            detector_backend="retinaface",
            enforce_detection=False,
        )
        
        if not results:
            print(f" No face found in {filename}")
            return []
        faces = []
        for i, result in enumerate(results):
            embedding = result["embedding"]
            norm = np.linalg.norm(embedding)
            if norm>0:
                embedding=embedding/norm
            embedding=embedding.tolist()
            
            bbox=result.get("facial_area",{})
            
            face_data={
                "file_id":file_id,
                "filename":filename,
                "face_index":i,
                "embeddings":embedding,
                "bbox":{
                    "x":bbox.get("x",0),
                    "y":bbox.get("y",0),
                    "w":bbox.get("w",0),
                    "h":bbox.get("h",0),
                }
            }
            faces.append(face_data)
        print(f" Found {len(faces)} faces in {filename}")
        return faces
    
    except Exception as e:
        print(f" Error processing {filename}:{e}")    
        return []
    
def process_batch(batch_path,batch_file_ids):
    batch_fingerprints = []
    
    for path,file_id in zip(batch_path,batch_file_ids):
        faces = process_one_image(path,file_id)
        batch_fingerprints.extend(faces)
    
    print(f"\n Batch done:{len(batch_fingerprints)} faces found")
    return batch_fingerprints

# --------------------------
# # core/embedder.py

# import json
# import os
# import concurrent.futures
# import numpy as np
# from deepface import DeepFace

# FINGERPRINTS_FILE = "data/fingerprints.json"


# def process_one_image(image_path, file_id):
#     """Detect all faces in one image and return fingerprints."""
#     filename = os.path.basename(image_path)

#     try:
#         results = DeepFace.represent(
#             img_path=image_path,
#             model_name="ArcFace",
#             detector_backend="retinaface",
#             enforce_detection=False,
#         )

#         if not results:
#             print(f"  ⚠️  No faces in {filename}")
#             return []

#         faces = []
#         for i, result in enumerate(results):
#             bbox = result.get("facial_area", {})
#             w = bbox.get("w", 0)
#             h = bbox.get("h", 0)

#             # skip tiny faces
#             if w < 50 or h < 50:
#                 print(f"  ⚠️  Skipping tiny face "
#                       f"({w}x{h}px) in {filename}")
#                 continue

#             # get embedding
#             embedding = np.array(result["embedding"])
#             norm = np.linalg.norm(embedding)
#             if norm > 0:
#                 embedding = embedding / norm
#             embedding = embedding.tolist()

#             face_data = {
#                 "file_id":    file_id,
#                 "filename":   filename,
#                 "face_index": i,
#                 "embedding":  embedding,
#                 "bbox": {
#                     "x": bbox.get("x", 0),
#                     "y": bbox.get("y", 0),
#                     "w": w,
#                     "h": h,
#                 }
#             }
#             faces.append(face_data)

#         if faces:
#             print(f"  ✅ {len(faces)} face(s) in {filename}")
#         else:
#             print(f"  ⚠️  No valid faces in {filename}")

#         return faces

#     except Exception as e:
#         print(f"  ❌ Error: {filename} → {e}")
#         return []


# def process_batch(batch_paths, batch_file_ids, max_workers=4):
#     """
#     Process multiple images simultaneously.
#     max_workers:
#         2 = safe for any laptop
#         4 = good for 8GB RAM
#         8 = good for 16GB RAM
#     """
#     batch_fingerprints = []

#     print(f"  Processing {len(batch_paths)} photos "
#           f"with {max_workers} workers...")

#     with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
#         futures = {
#             executor.submit(process_one_image, path, file_id): path
#             for path, file_id in zip(batch_paths, batch_file_ids)
#         }
#         for future in concurrent.futures.as_completed(futures):
#             path = futures[future]
#             try:
#                 faces = future.result()
#                 if faces:
#                     batch_fingerprints.extend(faces)
#             except Exception as e:
#                 print(f"  ❌ Failed: {path} → {e}")

#     print(f"  Batch done: {len(batch_fingerprints)} faces found")
#     return batch_fingerprints


# def load_existing_fingerprints(filepath=FINGERPRINTS_FILE):
#     """Load fingerprints and deduplicate automatically."""
#     if not os.path.exists(filepath):
#         print("Starting fresh")
#         return []

#     try:
#         with open(filepath, "r") as f:
#             data = json.load(f)

#         if not data:
#             return []

#         # deduplicate by filename + face_index
#         seen = set()
#         unique = []
#         for f in data:
#             key = f"{f['filename']}_{f['face_index']}"
#             if key not in seen:
#                 seen.add(key)
#                 unique.append(f)

#         removed = len(data) - len(unique)
#         if removed > 0:
#             print(f"Removed {removed} duplicates")

#         print(f"Loaded {len(unique)} fingerprints")
#         return unique

#     except Exception as e:
#         print(f"Error loading: {e}")
#         return []


# def save_fingerprints(fingerprints, filepath=FINGERPRINTS_FILE):
#     """Deduplicate and save fingerprints."""
#     seen = set()
#     unique = []
#     for f in fingerprints:
#         key = f"{f['filename']}_{f['face_index']}"
#         if key not in seen:
#             seen.add(key)
#             unique.append(f)

#     os.makedirs("data", exist_ok=True)
#     with open(filepath, "w") as f:
#         json.dump(unique, f)

#     print(f"💾 Saved {len(unique)} fingerprints to {filepath}")
#     return unique


# def get_already_processed(fingerprints):
#     """Get set of already processed filenames."""
#     return set(f["filename"] for f in fingerprints)


# core/embedder.py

# import json
# import os
# import concurrent.futures
# import numpy as np
# from deepface import DeepFace

# FINGERPRINTS_FILE = "data/fingerprints.json"

# # ── Speed settings ────────────────────────────────────────
# DETECTOR     = "opencv"   # fastest detector
# MODEL        = "ArcFace"  # best accuracy
# MIN_FACE_SIZE = 20        # skip faces smaller than 20x20px
# MAX_WORKERS   = 4         # parallel processing
# # ─────────────────────────────────────────────────────────


# def _load_model():
#     """
#     Pre-load the AI model once at startup.
#     This saves 3-5 seconds per batch because the model
#     is loaded once instead of once per photo.
#     """
#     print("  Loading AI model (one time only)...")
#     try:
#         # load model by running on a blank image
#         import numpy as np
#         blank = np.zeros((224, 224, 3), dtype=np.uint8)
#         DeepFace.represent(
#             img_path=blank,
#             model_name=MODEL,
#             detector_backend=DETECTOR,
#             enforce_detection=False,
#         )
#         print("  ✅ AI model loaded!")
#     except Exception:
#         pass  # ignore errors on blank image


# def process_one_image(image_path, file_id):
#     """
#     Detect all faces in one image.
#     Returns list of face fingerprints.
#     """
#     filename = os.path.basename(image_path)

#     try:
#         results = DeepFace.represent(
#             img_path=image_path,
#             model_name=MODEL,
#             detector_backend=DETECTOR,
#             enforce_detection=False,
#             align=True,
#         )

#         if not results:
#             print(f"  ⚠️  No faces: {filename}")
#             return []

#         faces = []
#         for i, result in enumerate(results):
#             bbox = result.get("facial_area", {})
#             w = bbox.get("w", 0)
#             h = bbox.get("h", 0)

#             # skip very tiny faces only
#             if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
#                 continue

#             # get embedding
#             embedding = np.array(result["embedding"])
#             norm = np.linalg.norm(embedding)
#             if norm > 0:
#                 embedding = embedding / norm
#             embedding = embedding.tolist()

#             faces.append({
#                 "file_id":    file_id,
#                 "filename":   filename,
#                 "face_index": i,
#                 "embedding":  embedding,
#                 "bbox": {
#                     "x": bbox.get("x", 0),
#                     "y": bbox.get("y", 0),
#                     "w": w,
#                     "h": h,
#                 }
#             })

#         print(f"  ✅ {len(faces)} face(s) → {filename}")
#         return faces

#     except Exception as e:
#         print(f"  ❌ {filename} → {e}")
#         return []


# def process_batch(batch_paths, batch_file_ids,
#                   max_workers=MAX_WORKERS):
#     """
#     Process multiple images in parallel.
#     """
#     print(f"\n  Processing {len(batch_paths)} photos "
#           f"with {max_workers} workers...")

#     batch_fingerprints = []

#     with concurrent.futures.ThreadPoolExecutor(
#             max_workers=max_workers) as executor:

#         futures = {
#             executor.submit(
#                 process_one_image, path, file_id): path
#             for path, file_id
#             in zip(batch_paths, batch_file_ids)
#         }

#         for future in concurrent.futures.as_completed(futures):
#             try:
#                 faces = future.result()
#                 if faces:
#                     batch_fingerprints.extend(faces)
#             except Exception as e:
#                 print(f"  ❌ Error: {e}")

#     print(f"  Batch done: "
#           f"{len(batch_fingerprints)} faces found")
#     return batch_fingerprints


# def load_existing_fingerprints(filepath=FINGERPRINTS_FILE):
#     """Load and deduplicate fingerprints."""
#     if not os.path.exists(filepath):
#         print("Starting fresh")
#         return []

#     try:
#         with open(filepath, "r") as f:
#             data = json.load(f)

#         if not data:
#             return []

#         seen = set()
#         unique = []
#         for f in data:
#             key = f"{f['filename']}_{f['face_index']}"
#             if key not in seen:
#                 seen.add(key)
#                 unique.append(f)

#         removed = len(data) - len(unique)
#         if removed > 0:
#             print(f"Removed {removed} duplicates")

#         print(f"Loaded {len(unique)} fingerprints")
#         return unique

#     except Exception as e:
#         print(f"Error loading: {e}")
#         return []


# def save_fingerprints(fingerprints,
#                       filepath=FINGERPRINTS_FILE):
#     """Deduplicate and save."""
#     seen = set()
#     unique = []
#     for f in fingerprints:
#         key = f"{f['filename']}_{f['face_index']}"
#         if key not in seen:
#             seen.add(key)
#             unique.append(f)

#     os.makedirs("data", exist_ok=True)
#     with open(filepath, "w") as f:
#         json.dump(unique, f)

#     print(f"💾 Saved {len(unique)} fingerprints")
#     return unique


# def get_already_processed(fingerprints):
#     """Get set of already processed filenames."""
#     return set(f["filename"] for f in fingerprints)