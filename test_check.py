# test_check.py
import json

with open("data/fingerprints.json", "r") as f:
    data = json.load(f)

print(f"Total fingerprints: {len(data)}")
print(f"\nFaces per photo:")

# group by filename
photos = {}
for f in data:
    name = f["filename"]
    if name not in photos:
        photos[name] = []
    photos[name].append(f["face_index"])

for filename, faces in sorted(photos.items()):
    print(f"  {filename}: {len(faces)} faces → {faces}")