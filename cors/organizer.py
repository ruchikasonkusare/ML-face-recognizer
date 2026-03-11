import os
import shutil
import json
from cors.downloader import download_one_image,TEMP_FOLDER

def load_groups(filepath="data/groups.json"):
    with open(filepath,"r") as f:
        groups=json.load(f)
    print(f"Loaded {len(groups)} groups")
    return groups

# def organize_results(groups,output_dir="output"):
#     os.makedirs(output_dir, exist_ok=True)
#     os.makedirs(TEMP_FOLDER, exist_ok=True)
#     downloaded_cache = {}

#     total_people = len(groups)
#     print(f"\nOrganizing {total_people} people into folders...")
#     print(groups)

#     for person, faces in groups.items():
#         print(f"\n--- {person} ---")

#         # create folder for this person
#         person_folder = os.path.join(output_dir, person)
#         os.makedirs(person_folder, exist_ok=True)

#         # get unique photos for this person
#         # (same photo might have multiple faces)
#         unique_photos = {}
#         for face in faces:
#             filename = face["filename"]
#             file_id  = face["file_id"]
#             if filename not in unique_photos:
#                 unique_photos[filename] = file_id

#         print(f"  Needs {len(unique_photos)} photos")

#         # download and copy each photo
#         for filename, file_id in unique_photos.items():

#             # check if already downloaded in cache
#             if filename in downloaded_cache:
#                 cached_path = downloaded_cache[filename]
#                 print(f"  Using cached: {filename}")
#             else:
#                 # download fresh
#                 path = download_one_image(file_id, filename)
#                 if path:
#                     downloaded_cache[filename] = path
#                     cached_path = path
#                 else:
#                     print(f"  ❌ Could not download: {filename}")
#                     continue

#             # copy to person folder
#             dest = os.path.join(person_folder, filename)
#             if not os.path.exists(dest):
#                 shutil.copy2(cached_path, dest)
#                 print(f"  ✅ Copied to {person}/{filename}")
#             else:
#                 print(f"  Already exists: {filename}")

#     # clean up temp folder
#     print(f"\nCleaning up temp files...")
#     for filename in os.listdir(TEMP_FOLDER):
#         path = os.path.join(TEMP_FOLDER, filename)
#         os.remove(path)
#     print(f"✅ Cleanup done!")

#     # print final summary
#     print(f"\n=== FINAL OUTPUT ===")
#     for person in groups.keys():
#         person_folder = os.path.join(output_dir, person)
#         files = os.listdir(person_folder)
#         print(f"  {person:12s} → {len(files)} photos → {person_folder}")



def organize_results(groups, output_dir="output"):
    os.makedirs(output_dir,  exist_ok=True)
    os.makedirs(TEMP_FOLDER, exist_ok=True)

    downloaded_cache = {}
    print(f"\nOrganizing {len(groups)} people...")

    for person, faces in groups.items():
        print(f"\n--- {person} ---")

        person_folder = os.path.join(output_dir, person)
        os.makedirs(person_folder, exist_ok=True)

        unique_photos = {}
        for face in faces:
            filename = face["filename"]
            file_id  = face["file_id"]
            if filename not in unique_photos:
                unique_photos[filename] = file_id

        print(f"  Needs {len(unique_photos)} photos")

        for filename, file_id in unique_photos.items():

            if filename in downloaded_cache:
                cached_path = downloaded_cache[filename]
            else:
                # ── DELETE any existing small/corrupt file ──
                temp_path = os.path.join(TEMP_FOLDER, filename)
                if os.path.exists(temp_path):
                    size = os.path.getsize(temp_path)
                    if size < 50000:  # less than 50KB = wrong file
                        print(f"  🗑  Removing corrupt: "
                              f"{filename} ({size} bytes)")
                        os.remove(temp_path)

                # ── download fresh ──
                path = download_one_image(file_id, filename)
                if not path:
                    print(f"  ❌ Failed: {filename}")
                    continue

                # ── verify size is reasonable ──
                size = os.path.getsize(path)
                if size < 50000:  # still too small?
                    print(f"  ⚠️  Suspicious file size: "
                          f"{filename} ({size} bytes)")

                downloaded_cache[filename] = path
                cached_path = path

            dest = os.path.join(person_folder, filename)
            if os.path.exists(dest):
                os.remove(dest)  # remove old wrong copy
            shutil.copy2(cached_path, dest)
            print(f"  ✅ {person}/{filename}")

    # cleanup
    print(f"\n  Cleaning up temp files...")
    for filename in os.listdir(TEMP_FOLDER):
        path = os.path.join(TEMP_FOLDER, filename)
        os.remove(path)
    print(f"  ✅ Cleanup done!")

    print(f"\n=== FINAL OUTPUT ===")
    for person in groups.keys():
        folder = os.path.join(output_dir, person)
        count  = len(os.listdir(folder))
        print(f"  {person:12s} → "
              f"{count} photos → {folder}")