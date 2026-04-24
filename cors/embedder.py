# import json
# import os
# import numpy as np
# from deepface import DeepFace

# FINGERPRINT_FILE="data/fingerprints.json"

# def load_existing_fingerprints(filepath=FINGERPRINT_FILE):
#     """Load fingerprints and deduplicate automatically."""
    
#     # if file doesn't exist, return empty list
#     if not os.path.exists(filepath):
#         print("Starting fresh")
#         return []   # ← must return [] not None

#     try:
#         with open(filepath, "r") as f:
#             data = json.load(f)

#         # if file is empty or corrupt, return empty list
#         if not data:
#             print("Empty fingerprints file, starting fresh")
#             return []   # ← must return [] not None

#         # deduplicate
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
#         print(f"Error loading fingerprints: {e}")
#         return []   # ← always return [] on any error
    
    
# def save_fingerprints(fingerprints, filepath=FINGERPRINT_FILE):

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
#     print(f"Saved {len(unique)} fingerprints to {filepath}")
    
#     return unique 
    
# def get_already_processed(fingerprints):
    
#     return set(f["filename"] for f in fingerprints)


# def process_one_image(image_path,file_id):
#     filename=os.path.basename(image_path)
#     print(filename )
#     print(f" Processing:{filename}")
    
#     try:
#         results = DeepFace.represent(
#             img_path=image_path,
#             model_name="ArcFace",
#             detector_backend="retinaface",
#             enforce_detection=False,
#         )
        
#         if not results:
#             print(f" No face found in {filename}")
#             return []
#         faces = []
#         for i, result in enumerate(results):
#             embedding = result["embedding"]
#             norm = np.linalg.norm(embedding)
#             if norm>0:
#                 embedding=embedding/norm
#             embedding=embedding.tolist()
            
#             bbox=result.get("facial_area",{})
            
#             face_data={
#                 "file_id":file_id,
#                 "filename":filename,
#                 "face_index":i,
#                 "embeddings":embedding,
#                 "bbox":{
#                     "x":bbox.get("x",0),
#                     "y":bbox.get("y",0),
#                     "w":bbox.get("w",0),
#                     "h":bbox.get("h",0),
#                 }
#             }
#             faces.append(face_data)
#         print(f" Found {len(faces)} faces in {filename}")
#         return faces
    
#     except Exception as e:
#         print(f" Error processing {filename}:{e}")    
#         return []
    
# import concurrent.futures

# def process_batch(batch_paths, batch_file_ids, max_workers=2):
#     batch_fingerprints = []
#     print(f"  Processing {len(batch_paths)} photos with {max_workers} workers...")

#     with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
#         futures = {
#             executor.submit(process_one_image, path, file_id): path
#             for path, file_id in zip(batch_paths, batch_file_ids)
#         }
#         for future in concurrent.futures.as_completed(futures):
#             try:
#                 faces = future.result()
#                 if faces:
#                     batch_fingerprints.extend(faces)
#             except Exception as e:
#                 print(f"  Error: {e}")

#     print(f"  Batch done: {len(batch_fingerprints)} faces found")
#     return batch_fingerprints


# .......................................................
import json
import os
import time
import concurrent.futures
import numpy as np
from deepface import DeepFace

FINGERPRINT_FILE = "data/fingerprints.json"

# ── Speed settings (only new lines added) ─────────────────
DETECTOR    = "mtcnn"   # was hardcoded "retinaface" — change here to tune
                        # "opencv"     = fastest  (~1s/photo)
                        # "mtcnn"      = balanced (~3s/photo)  ← recommended
                        # "retinaface" = slowest  (~15s/photo)
MAX_DIM     = 640       # resize photos larger than this before processing
                        # faces look the same at 640px, detection is 4x faster
                        # set to None to disable resizing
MIN_FACE_PX = 20        # skip faces smaller than this (your original value)

# model warm-up flag — loaded once, shared across all workers
_model_ready = False

def _warmup():
    """Load AI model weights once at startup.
    Without this, the first batch wastes ~5s loading weights."""
    global _model_ready
    if _model_ready:
        return
    try:
        print("  Loading AI model (one time)...")
        t = time.time()
        dummy = np.zeros((112, 112, 3), dtype=np.uint8)
        DeepFace.represent(
            img_path=dummy,
            model_name="ArcFace",
            detector_backend="skip",
            enforce_detection=False,
        )
        _model_ready = True
        print(f"  ✅ Model ready ({time.time()-t:.1f}s)")
    except Exception:
        _model_ready = True  # continue even if warmup fails


def _resize_if_needed(image_path):
    """Resize large photos before processing.
    A 4K photo takes 4x longer than a 640px photo.
    Returns (path_to_use, scale_factor)."""
    if MAX_DIM is None:
        return image_path, 1.0
    try:
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            return image_path, 1.0
        h, w = img.shape[:2]
        if max(h, w) <= MAX_DIM:
            return image_path, 1.0
        scale   = MAX_DIM / max(h, w)
        resized = cv2.resize(img, (int(w*scale), int(h*scale)),
                             interpolation=cv2.INTER_AREA)
        import tempfile
        ext = os.path.splitext(image_path)[1] or ".jpg"
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        cv2.imwrite(tmp.name, resized)
        tmp.close()
        return tmp.name, 1.0 / scale
    except Exception:
        return image_path, 1.0


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


def process_one_image(image_path, file_id):
    filename  = os.path.basename(image_path)
    tmp_path  = None
    print(f" Processing:{filename}")
    
    try:
        # resize large photos before processing (faster)
        process_path, bbox_scale = _resize_if_needed(image_path)
        if process_path != image_path:
            tmp_path = process_path

        results = DeepFace.represent(
            img_path=process_path,
            model_name="ArcFace",
            detector_backend=DETECTOR,      # ← uses variable, not hardcoded
            enforce_detection=False,
        )
        
        if not results:
            print(f" No face found in {filename}")
            return []

        faces = []
        for i, result in enumerate(results):
            embedding = result["embedding"]
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            embedding = embedding.tolist()
            
            bbox = result.get("facial_area", {})
            w    = bbox.get("w", 0)
            h    = bbox.get("h", 0)

            # skip tiny faces
            if w < MIN_FACE_PX or h < MIN_FACE_PX:
                continue

            face_data = {
                "file_id":    file_id,
                "filename":   filename,
                "face_index": i,
                "embeddings": embedding,    # ← kept your key name "embeddings"
                "bbox": {
                    "x": int(bbox.get("x", 0) * bbox_scale),
                    "y": int(bbox.get("y", 0) * bbox_scale),
                    "w": int(w * bbox_scale),
                    "h": int(h * bbox_scale),
                }
            }
            faces.append(face_data)

        print(f" Found {len(faces)} faces in {filename}")
        return faces
    
    except Exception as e:
        print(f" Error processing {filename}:{e}")    
        return []

    finally:
        # clean up temp resized file
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass


def process_batch(batch_paths, batch_file_ids, max_workers=2):
    # warm up model ONCE before parallel workers start
    # (stops each worker trying to load the model at the same time)
    _warmup()

    batch_fingerprints = []
    total = len(batch_paths)
    t_start = time.time()
    print(f"  Processing {total} photos with {max_workers} workers...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_one_image, path, file_id): path
            for path, file_id in zip(batch_paths, batch_file_ids)
        }
        done = 0
        for future in concurrent.futures.as_completed(futures):
            done += 1
            try:
                faces = future.result()
                if faces:
                    batch_fingerprints.extend(faces)
            except Exception as e:
                print(f"  Error: {e}")
            # show live progress + ETA
            elapsed = time.time() - t_start
            rate    = done / elapsed if elapsed > 0 else 0
            eta     = int((total - done) / rate) if rate > 0 else 0
            print(f"  [{done}/{total}]  {rate:.1f} photos/s  ETA {eta}s", end="\r")

    print(f"\n  Batch done: {len(batch_fingerprints)} faces found  "
          f"({time.time()-t_start:.0f}s total)")
    return batch_fingerprints
