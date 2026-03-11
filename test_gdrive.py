# test_all.py

from utils.gdrive import get_folder_link, get_all_file_ids
from cors.downloader import split_into_batches, download_batch, delete_batch
from cors.embedder import (process_batch, save_fingerprints,
                           load_existing_fingerprints,
                           get_already_processed)
from cors.clusterer import load_fingerprints, group_faces, save_groups
from cors.organizer import load_groups, organize_results

# ─────────────────────────────────────────
# STEP 1: Get file list from Google Drive
# ─────────────────────────────────────────
print("=" * 40)
print("STEP 1: Getting file list")
print("=" * 40)

link = "https://drive.google.com/drive/folders/1PWE9Y3zyUBf8nePyoucckuE8o7DH_2C_?usp=drive_link"
folder_id = get_folder_link(link)
file_list = get_all_file_ids(folder_id)
print(f"Total images in Drive: {len(file_list)}")

# ─────────────────────────────────────────
# STEP 2: Split into batches
# ─────────────────────────────────────────
print("\n" + "=" * 40)
print("STEP 2: Splitting into batches")
print("=" * 40)

batches = split_into_batches(file_list, batch_size=5)
print(f"Total batches: {len(batches)}")

# ─────────────────────────────────────────
# STEP 3: Process each batch
# ─────────────────────────────────────────
print("\n" + "=" * 40)
print("STEP 3: Processing batches")
print("=" * 40)

# load existing fingerprints (resume support)
all_fingerprints = load_existing_fingerprints()
already_done = get_already_processed(all_fingerprints)
print(f"Already processed: {len(already_done)} files")

for i, batch in enumerate(batches):
    print(f"\n--- Batch {i+1}/{len(batches)} ---")

    # skip already processed files
    new_batch = [(fid, fname) for fid, fname in batch
                 if fname not in already_done]

    if not new_batch:
        print("Already done, skipping...")
        continue

    # download
    paths = download_batch(new_batch)

    # get file IDs
    file_ids = [fid for fid, fname in new_batch]

    # detect faces and get fingerprints
    new_fingerprints = process_batch(paths, file_ids)

    # add to collection
    all_fingerprints.extend(new_fingerprints)

    # update already done list
    already_done = get_already_processed(all_fingerprints)

    # save after every batch (crash protection)
    all_fingerprints = save_fingerprints(all_fingerprints)

    # delete photos to save disk space
    delete_batch(paths)

print(f"\nTotal unique fingerprints: {len(all_fingerprints)}")

# ─────────────────────────────────────────
# STEP 4: Group faces by person
# ─────────────────────────────────────────
print("\n" + "=" * 40)
print("STEP 4: Grouping faces by person")
print("=" * 40)

fingerprints = load_fingerprints()
groups = group_faces(fingerprints, eps=0.5, min_sample=2)
save_groups(groups)

# ─────────────────────────────────────────
# STEP 5: Organize into folders
# ─────────────────────────────────────────
print("\n" + "=" * 40)
print("STEP 5: Organizing into folders")
print("=" * 40)

groups = load_groups()
organize_results(groups, output_dir="output")

# ─────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────
print("\n" + "=" * 40)
print("DONE!")
print("=" * 40)
print(f"Total fingerprints: {len(all_fingerprints)}")
print(f"Total people found: {len(groups)}")
print(f"\nCheck your output/ folder!")

# show photos per person
print("\nPeople found:")
for person, faces in sorted(groups.items()):
    photos = set(f["filename"] for f in faces)
    print(f"  {person:12s} → {len(photos)} photos")