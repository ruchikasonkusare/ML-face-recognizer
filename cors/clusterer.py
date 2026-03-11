import json
import os
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import normalize

def load_fingerprints(filepath="data/fingerprints.json"):
    
    with open(filepath,"r") as f:
        fingerprints=json.load(f)
    print(f"Loaded {len(fingerprints)} fingerprints")
    return fingerprints

def group_faces(fingerprints,eps=0.6,min_samples=2):
    if not fingerprints:
        print(f"No fingerprints to cluster")
        return {}
    
    print(f"Clustering {len(fingerprints)} fingerprints...")
    embeddings=np.array([f["embeddings"] for f in fingerprints])
    embeddings=normalize(embeddings,norm="l2")
    
    db=DBSCAN(
        eps=eps,
        min_samples=min_samples,
        metric="cosine",
        algorithm="brute",
        n_jobs=-1
    )
    
    labels=db.fit_predict(embeddings)
    unique_labels=set(labels)
    n_clusters=len(unique_labels)-(1 if -1 in unique_labels else 0)
    n_unknown=int((labels==-1).sum())
    
    print(f"Found {n_clusters} peopple")
    print(f"Unknown faces:{n_unknown}")
    
    groups={}
    for fingerprint,label in zip(fingerprints,labels):
        if label ==-1:
            person = "Unknown"
        else:
            person =f"Person_{label+1:02d}"
        fingerprint["person"]=person
        
        face_with_label = {
            "file_id":    fingerprint["file_id"],
            "filename":   fingerprint["filename"],
            "face_index": fingerprint["face_index"],
            "embedding":  fingerprint["embeddings"],
            "bbox":       fingerprint["bbox"],
            "person":     person,
        }

        # add to groups dict
        if person not in groups:
            groups[person] = []
        groups[person].append(face_with_label)
        
        
    
    print("\n----Clustering Results------")
    
    for person,faces in sorted(groups.items()):
        photos=set(f["filename"] for f in faces)
        print(f"{person}:{len(faces)} faces in {len(photos)} photos")
    return groups


def save_groups(groups, filepath="data/groups.json"):
    """Save clustering results to file."""
    with open(filepath, "w") as f:
        json.dump(groups, f, indent=2)

    total_faces = sum(len(faces) for faces in groups.values())
    print(f"\n💾 Saved {len(groups)} groups ({total_faces} faces) to {filepath}")
    
def load_groups(filepath="data/groups.json"):
    with open(filepath,"r") as f:
        groups=json.load(f)
    print(f"Loaded {len(groups)} groups")
    return groups
        
    # --------------------------------------------------------------
# # core/clusterer.py

# import json
# import numpy as np
# from sklearn.cluster import DBSCAN
# from sklearn.preprocessing import normalize

# GROUPS_FILE = "data/groups.json"


# def load_fingerprints(filepath="data/fingerprints.json"):
#     """Load all saved fingerprints from file."""
#     with open(filepath, "r") as f:
#         fingerprints = json.load(f)
#     print(f"Loaded {len(fingerprints)} fingerprints")
#     return fingerprints


# def group_faces(fingerprints, eps=0.4, min_samples=2):
#     """
#     Group faces by person using DBSCAN clustering.

#     eps:
#         0.2 = very strict (more Unknowns)
#         0.4 = balanced (recommended)
#         0.6 = very loose (may merge people)

#     min_samples:
#         2 = even 2 photos of same person = group
#         3 = need at least 3 photos to form group
#     """
#     if not fingerprints:
#         print("No fingerprints to cluster!")
#         return {}

#     print(f"\nClustering {len(fingerprints)} faces...")
#     print(f"Settings: eps={eps}, min_samples={min_samples}")

#     # Step 1: stack all embeddings into matrix
#     embeddings = np.array([f["embedding"] for f in fingerprints])

#     # Step 2: normalize
#     embeddings = normalize(embeddings, norm="l2")

#     # Step 3: run DBSCAN
#     db = DBSCAN(
#         eps=eps,
#         min_samples=min_samples,
#         metric="cosine",
#         algorithm="brute",
#         n_jobs=-1,
#     )
#     labels = db.fit_predict(embeddings)

#     # Step 4: count results
#     unique_labels = set(labels)
#     n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
#     n_unknown  = int((labels == -1).sum())
#     print(f"Found {n_clusters} people")
#     print(f"Unknown faces: {n_unknown}")

#     # Step 5: assign labels
#     groups = {}
#     for fingerprint, label in zip(fingerprints, labels):
#         if label == -1:
#             person = "Unknown"
#         else:
#             person = f"Person_{label + 1:02d}"

#         # create copy with person label
#         face = {
#             "file_id":    fingerprint["file_id"],
#             "filename":   fingerprint["filename"],
#             "face_index": fingerprint["face_index"],
#             "embedding":  fingerprint["embedding"],
#             "bbox":       fingerprint["bbox"],
#             "person":     person,
#         }

#         if person not in groups:
#             groups[person] = []
#         groups[person].append(face)

#     # Step 6: print summary
#     print("\n--- Clustering Results ---")
#     for person, faces in sorted(groups.items()):
#         photos = set(f["filename"] for f in faces)
#         print(f"  {person:12s}: {len(faces):3d} faces in {len(photos):3d} photos")

#     return groups


# def save_groups(groups, filepath=GROUPS_FILE):
#     """Save clustering results to file."""
#     with open(filepath, "w") as f:
#         json.dump(groups, f, indent=2)

#     total = sum(len(faces) for faces in groups.values())
#     print(f"\n💾 Saved {len(groups)} groups ({total} faces) to {filepath}")


# def load_groups(filepath=GROUPS_FILE):
#     """Load saved groups from file."""
#     with open(filepath, "r") as f:
#         groups = json.load(f)
#     print(f"Loaded {len(groups)} groups")
#     return groups


# def find_best_eps(fingerprints):
#     """
#     Test different eps values to find the best one.
#     Run this to tune clustering for your photos.
#     """
#     print("\n--- Testing eps values ---")
#     print(f"{'eps':>6} | {'people':>8} | {'unknown':>8}")
#     print("-" * 30)

#     for eps in [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]:
#         groups = group_faces(fingerprints, eps=eps, min_samples=2)
#         people  = len([p for p in groups if p != "Unknown"])
#         unknown = len(groups.get("Unknown", []))
#         print(f"  {eps:>4} | {people:>8} | {unknown:>8}")

#     print("\nPick the eps where people count looks right for your photos")