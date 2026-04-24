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

def group_faces(fingerprints,eps=0.55,min_samples=2):
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
    os.makedirs("data", exist_ok=True)
 
    # ✅ FIX: flush + fsync so file is fully written before UI reads it
    with open(filepath, "w") as f:
        json.dump(groups, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
 
    total_faces = sum(len(faces) for faces in groups.values())
    print(f"\n💾 Saved {len(groups)} groups ({total_faces} faces) to {filepath}")
    
def load_groups(filepath="data/groups.json"):
    with open(filepath,"r") as f:
        groups=json.load(f)
    print(f"Loaded {len(groups)} groups")
    return groups
        
    # --------------------------------------------------------------
