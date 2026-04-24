"""
debug_thumbnails.py
Run in your project folder:
    python debug_thumbnails.py
"""
import os, json, sys, time
os.environ["CUDA_VISIBLE_DEVICES"]  = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"]  = "3"

print("=" * 50)
print("THUMBNAIL DEBUG")
print("=" * 50)

# ── 1. Check groups.json ──────────────────────────────────
gf = "data/groups.json"
if not os.path.exists(gf):
    print("❌ data/groups.json not found"); sys.exit(1)

with open(gf) as f:
    groups = json.load(f)

print(f"\n✅ groups.json: {len(groups)} groups")
for name, faces in groups.items():
    photos = set(f["filename"] for f in faces)
    face   = faces[0]
    print(f"  {name}: {len(photos)} photos")
    print(f"    file_id : {str(face.get('file_id',''))[:25]}")
    print(f"    filename: {face.get('filename','')}")
    print(f"    bbox    : {face.get('bbox','MISSING')}")

# ── 2. Test download for EACH person ─────────────────────
print("\n" + "=" * 50)
print("TESTING DOWNLOAD FOR EACH PERSON")
print("=" * 50)

try:
    from cors.downloader import download_one_image
    print("✅ import cors.downloader OK")
except Exception as e:
    print(f"❌ import cors.downloader FAILED: {e}")
    sys.exit(1)

try:
    from PIL import Image
    print("✅ Pillow available")
except ImportError:
    print("❌ Pillow not installed — run: pip install Pillow --break-system-packages")
    sys.exit(1)

ok_count   = 0
fail_count = 0

for name, faces in groups.items():
    face     = faces[0]
    filename = face.get("filename", "")
    file_id  = face.get("file_id", "")
    bbox     = face.get("bbox")

    print(f"\n  [{name}] {filename}")
    t = time.time()

    try:
        tmp = download_one_image(file_id, filename)
        elapsed = time.time() - t

        if tmp and os.path.exists(tmp):
            size = os.path.getsize(tmp)
            try:
                img = Image.open(tmp).convert("RGB")
                print(f"    ✅ downloaded {size//1024}KB  "
                      f"image={img.size}  time={elapsed:.1f}s")
                ok_count += 1
                # test bbox crop
                if bbox:
                    try:
                        if isinstance(bbox, dict):
                            x,y,w,h = int(bbox['x']),int(bbox['y']),int(bbox['w']),int(bbox['h'])
                        else:
                            x,y,w,h = [int(v) for v in bbox[:4]]
                        pad  = int(max(w,h)*0.45)
                        crop = img.crop((max(0,x-pad),max(0,y-pad),
                                         min(img.width,x+w+pad),
                                         min(img.height,y+h+pad)))
                        print(f"    ✅ bbox crop OK: {crop.size}")
                    except Exception as e:
                        print(f"    ⚠️  bbox crop failed: {e}")
            except Exception as e:
                print(f"    ❌ PIL open failed: {e}")
                fail_count += 1
            try: os.remove(tmp)
            except: pass
        else:
            print(f"    ❌ download returned None  time={elapsed:.1f}s")
            fail_count += 1

    except Exception as e:
        print(f"    ❌ exception: {e}")
        fail_count += 1

print(f"\n{'='*50}")
print(f"RESULT: {ok_count} OK,  {fail_count} FAILED")
if fail_count > 0:
    print("→ Failed downloads = no thumbnail shown in UI")
    print("→ Most likely cause: Google Drive rate limiting")
    print("→ Fix: reduce max_workers in _load_avatars to 2")