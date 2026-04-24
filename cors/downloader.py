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
