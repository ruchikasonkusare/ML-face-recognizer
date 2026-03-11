import requests
import os
import concurrent.futures


TEMP_FOLDER = "data/temp_batch"

def create_temp_folder():
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
        print(f"Created folder:{TEMP_FOLDER}")
        

def download_one_image(file_id, filename):
    """Download one image from Google Drive."""
    save_path = os.path.join(TEMP_FOLDER, filename)

    # skip if already downloaded AND correct size
    if os.path.exists(save_path):
        size = os.path.getsize(save_path)
        if size > 100000:  # bigger than 100KB = real photo
            print(f"  Already downloaded: {filename}")
            return save_path
        else:
            # too small = wrong file, delete and re-download
            print(f"  ⚠️  Wrong size ({size} bytes), re-downloading...")
            os.remove(save_path)

    print(f"  Downloading: {filename}")

    try:
        session = requests.Session()

        # ── Step 1: get download URL with token ──
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = session.get(url, timeout=60, stream=True)
        content_type = response.headers.get("Content-Type", "")

        # ── Step 2: handle confirmation page ──
        if "text/html" in content_type:
            # try confirm=t
            response = session.get(
                url + "&confirm=t",
                timeout=60,
                stream=True,
            )
            content_type = response.headers.get("Content-Type", "")

            # still html? extract token from page
            if "text/html" in content_type:
                html = response.text

                # try uuid token (newer Google Drive)
                import re
                uuid_token = re.search(
                    r'name="uuid"\s+value="([^"]+)"', html)
                confirm_token = re.search(
                    r'confirm=([0-9A-Za-z_\-]+)', html)

                if uuid_token:
                    # newer Drive uses uuid + confirm
                    response = session.get(
                        url + f"&confirm=t&uuid={uuid_token.group(1)}",
                        timeout=120,
                        stream=True,
                    )
                elif confirm_token:
                    response = session.get(
                        url + f"&confirm={confirm_token.group(1)}",
                        timeout=120,
                        stream=True,
                    )

        # ── Step 3: if still html try direct export ──
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type:
            # try direct API download
            api_url = (f"https://www.googleapis.com/drive/v3/files/"
                      f"{file_id}?alt=media&key=YOUR_API_KEY")
            response = session.get(
                api_url, timeout=120, stream=True)

        # ── Step 4: save file ──
        if response.status_code == 200:
            os.makedirs(TEMP_FOLDER, exist_ok=True)

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(
                        chunk_size=1024*1024):  # 1MB chunks
                    if chunk:
                        f.write(chunk)

            size = os.path.getsize(save_path)
            if size < 1000:
                print(f"  ❌ Failed: {filename} (too small: {size})")
                os.remove(save_path)
                return None

            print(f"  ✅ {filename} ({size:,} bytes)")
            return save_path

        print(f"  ❌ Failed: {filename} "
              f"(status {response.status_code})")
        return None

    except Exception as e:
        print(f"  ❌ {filename} → {e}")
        return None
        
# def download_one_image(file_id,file_name):
#     url=f"https://drive.google.com/uc?export=download&id={file_id}"
    
#     save_path = os.path.join(TEMP_FOLDER, file_name)

#     if os.path.exists(save_path):
#         size = os.path.getsize(save_path)
#         if size > 100:
#             print(f"  Already downloaded: {file_name}")
#             return save_path
        
#     print(f"Downloading file: {file_name}")
#     try:
#         session = requests.Session()
#         response = session.get(url, timeout=60, stream=True)
#         content_type = response.headers.get("Content-Type", "")

#         # handle google warning page
#         if "text/html" in content_type:
#             confirm_url = url + "&confirm=t"
#             response = session.get(confirm_url, timeout=60, stream=True)
#             content_type = response.headers.get("Content-Type", "")

#             if "text/html" in content_type:
#                 html = response.text
#                 token = re.search(r'confirm=([0-9A-Za-z_\-]+)', html)
#                 if token:
#                     confirm_url = url + f"&confirm={token.group(1)}"
#                     response = session.get(confirm_url, timeout=60, stream=True)

#         if response.status_code == 200:
#             os.makedirs(TEMP_FOLDER, exist_ok=True)
#             with open(save_path, "wb") as f:
#                 for chunk in response.iter_content(chunk_size=8192):
#                     if chunk:
#                         f.write(chunk)

#             size = os.path.getsize(save_path)
#             if size < 100:
#                 print(f"  ❌ Failed: {file_name} (too small)")
#                 os.remove(save_path)
#                 return None

#             print(f"  ✅ Saved: {file_name} ({size} bytes)")
#             return save_path
#         else:
#             print(f"  ❌ Failed: {file_name} (status {response.status_code})")
#             return None

#     except Exception as e:
#         print(f"  ❌ Error: {file_name} → {e}")
#         return None
    
def download_batch(batch, max_workers=10):
    """Download all images and return (path, file_id) pairs."""
    create_temp_folder()
    results = []

    print(f"  Downloading {len(batch)} photos...")

    with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers) as executor:

        futures = {
            executor.submit(
                download_one_image,
                file_id,
                filename): (file_id, filename)
            for file_id, filename in batch
        }

        for future in concurrent.futures.as_completed(futures):
            file_id, filename = futures[future]
            try:
                path = future.result()
                if path:
                    results.append((path, file_id))  # ← tuple pair
                    print(f"  ✅ {filename}")
                else:
                    print(f"  ❌ {filename}")
            except Exception as e:
                print(f"  ❌ {filename} → {e}")

    print(f"  Downloaded: {len(results)}/{len(batch)}")
    return results  # ← list of (path, file_id) tuples
    
def delete_batch(paths):
    print(f"Cleaning up {len(paths)} file")
    for path in paths:
        if os.path.exists(path):
            os.remove(path)
            print(f"Deleted:{os.path.basename(path)}")
    print("Cleanup done..!")
    
def split_into_batches(file_list,batch_size=50):
    batches=[]
    for i in range(0,len(file_list),batch_size):
        batch=file_list[i:i+batch_size]
        batches.append(batch)
    print(f"Split:{len(file_list)} files into {len(batches)} batches of {batch_size}")
    return batches

# -------------------
# core/downloader.py

# import os
# import re
# import requests
# import concurrent.futures

# TEMP_FOLDER = "data/temp_batch"


# def create_temp_folder():
#     """Create temp folder if it doesn't exist."""
#     if not os.path.exists(TEMP_FOLDER):
#         os.makedirs(TEMP_FOLDER)


# def download_one_image(file_id, filename):
#     """Download a single image from Google Drive."""
#     url = f"https://drive.google.com/uc?export=download&id={file_id}"
#     save_path = os.path.join(TEMP_FOLDER, filename)

#     # skip if already downloaded
#     if os.path.exists(save_path):
#         size = os.path.getsize(save_path)
#         if size > 100:
#             print(f"  Already downloaded: {filename}")
#             return save_path

#     print(f"  Downloading: {filename}")

#     try:
#         session = requests.Session()
#         response = session.get(url, timeout=60, stream=True)
#         content_type = response.headers.get("Content-Type", "")

#         # handle google confirmation page
#         if "text/html" in content_type:
#             # try confirm=t first
#             confirm_url = url + "&confirm=t"
#             response = session.get(confirm_url, timeout=60, stream=True)
#             content_type = response.headers.get("Content-Type", "")

#             # still html? extract token
#             if "text/html" in content_type:
#                 html = response.text
#                 token = re.search(r'confirm=([0-9A-Za-z_\-]+)', html)
#                 if token:
#                     confirm_url = url + f"&confirm={token.group(1)}"
#                     response = session.get(confirm_url, timeout=60, stream=True)

#         if response.status_code == 200:
#             os.makedirs(TEMP_FOLDER, exist_ok=True)

#             with open(save_path, "wb") as f:
#                 for chunk in response.iter_content(chunk_size=8192):
#                     if chunk:
#                         f.write(chunk)

#             size = os.path.getsize(save_path)
#             if size < 100:
#                 print(f"  ❌ Failed: {filename} (too small)")
#                 os.remove(save_path)
#                 return None

#             print(f"  ✅ Saved: {filename} ({size} bytes)")
#             return save_path
#         else:
#             print(f"  ❌ Failed: {filename} (status {response.status_code})")
#             return None

#     except Exception as e:
#         print(f"  ❌ Error: {filename} → {e}")
#         return None


# def download_batch(batch, max_workers=10):
#     """Download multiple images simultaneously."""
#     create_temp_folder()
#     saved_paths = []

#     print(f"  Downloading {len(batch)} photos simultaneously...")

#     with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
#         futures = {
#             executor.submit(download_one_image, file_id, filename): filename
#             for file_id, filename in batch
#         }
#         for future in concurrent.futures.as_completed(futures):
#             filename = futures[future]
#             try:
#                 path = future.result()
#                 if path:
#                     saved_paths.append(path)
#             except Exception as e:
#                 print(f"  ❌ Failed: {filename} → {e}")

#     print(f"  Batch complete: {len(saved_paths)}/{len(batch)} downloaded")
#     return saved_paths


# def delete_batch(paths):
#     """Delete all downloaded images after processing."""
#     print(f"  Cleaning up {len(paths)} files...")
#     for path in paths:
#         if os.path.exists(path):
#             os.remove(path)
#     print(f"  ✅ Cleanup done!")


# def split_into_batches(file_list, batch_size=50):
#     """Split file list into batches."""
#     batches = []
#     for i in range(0, len(file_list), batch_size):
#         batch = file_list[i: i + batch_size]
#         batches.append(batch)
#     print(f"Split {len(file_list)} files into "
#           f"{len(batches)} batches of {batch_size}")
#     return batches


# # core/downloader.py

# # import os
# # import re
# # import requests
# # import concurrent.futures

# # TEMP_FOLDER  = "data/temp_batch"
# # MAX_WORKERS  = 20   # download 20 photos at same time
# # CHUNK_SIZE   = 1024 * 1024  # 1MB chunks


# # def create_temp_folder():
# #     os.makedirs(TEMP_FOLDER, exist_ok=True)


# # def download_one_image(file_id, filename):
# #     """Download one image from Google Drive."""
# #     save_path = os.path.join(TEMP_FOLDER, filename)

# #     # skip if already downloaded
# #     if os.path.exists(save_path):
# #         if os.path.getsize(save_path) > 100:
# #             return save_path

# #     url = (f"https://drive.google.com/uc"
# #            f"?export=download&id={file_id}")

# #     try:
# #         session = requests.Session()
# #         response = session.get(url, timeout=60, stream=True)
# #         content_type = response.headers.get(
# #             "Content-Type", "")

# #         # handle google confirmation page
# #         if "text/html" in content_type:
# #             response = session.get(
# #                 url + "&confirm=t",
# #                 timeout=60,
# #                 stream=True,
# #             )
# #             content_type = response.headers.get(
# #                 "Content-Type", "")

# #             if "text/html" in content_type:
# #                 token = re.search(
# #                     r'confirm=([0-9A-Za-z_\-]+)',
# #                     response.text,
# #                 )
# #                 if token:
# #                     response = session.get(
# #                         url + f"&confirm={token.group(1)}",
# #                         timeout=60,
# #                         stream=True,
# #                     )

# #         if response.status_code == 200:
# #             with open(save_path, "wb") as f:
# #                 for chunk in response.iter_content(
# #                         chunk_size=CHUNK_SIZE):
# #                     if chunk:
# #                         f.write(chunk)

# #             if os.path.getsize(save_path) < 100:
# #                 os.remove(save_path)
# #                 return None

# #             return save_path

# #         return None

# #     except Exception:
# #         return None


# # def download_batch(batch, max_workers=MAX_WORKERS):
# #     """Download all images simultaneously."""
# #     create_temp_folder()
# #     saved_paths = []

# #     print(f"  Downloading {len(batch)} photos "
# #           f"({max_workers} at a time)...")

# #     with concurrent.futures.ThreadPoolExecutor(
# #             max_workers=max_workers) as executor:

# #         futures = {
# #             executor.submit(
# #                 download_one_image,
# #                 file_id,
# #                 filename): filename
# #             for file_id, filename in batch
# #         }

# #         for future in concurrent.futures.as_completed(
# #                 futures):
# #             try:
# #                 path = future.result()
# #                 if path:
# #                     saved_paths.append(path)
# #                     print(f"  ✅ {futures[future]}")
# #                 else:
# #                     print(f"  ❌ {futures[future]}")
# #             except Exception as e:
# #                 print(f"  ❌ Error: {e}")

# #     print(f"  Downloaded: "
# #           f"{len(saved_paths)}/{len(batch)}")
# #     return saved_paths


# # def delete_batch(paths):
# #     """Delete photos after processing."""
# #     for path in paths:
# #         if os.path.exists(path):
# #             os.remove(path)
# #     print(f"  🗑  Deleted {len(paths)} photos")


# # def split_into_batches(file_list, batch_size=100):
# #     """Split into batches."""
# #     batches = []
# #     for i in range(0, len(file_list), batch_size):
# #         batches.append(file_list[i: i + batch_size])
# #     print(f"Split {len(file_list)} files into "
# #           f"{len(batches)} batches of {batch_size}")
# #     return batches