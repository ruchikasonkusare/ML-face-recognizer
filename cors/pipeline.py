import os
from utils.gdrive import get_folder_link,get_all_file_ids
from cors.embedder import load_existing_fingerprints,process_batch,save_fingerprints,get_already_processed
from cors.downloader import delete_batch,download_batch,split_into_batches
from cors.clusterer import group_faces,load_fingerprints,save_groups
from cors.organizer import load_groups,organize_results

def run_pipeline(drive_link,output_dir="output",batch_size=50,eps=0.6,min_samples=2):
    print("\n"+"="*50)
    print("FACE ORGANIZER")
    print("\n"+"="*50)

# ......STEP 1................
    print("\nStep 1:Reading Google Drive folder..")
    folder_id=get_folder_link(drive_link)
    if not folder_id:
        print("Invalid Google drive link")
        return False
    
    file_list=get_all_file_ids(folder_id)
    if not file_list:
        print("No image found in folder")
        return False
    
    total_photos=len(file_list)
    print(f"Found {total_photos} in folder..")
    

# ......STEP 2................
    print(f"Step 2: Processing photos in batches of {batch_size}...")
    
    batches=split_into_batches(file_list,batch_size)
    total_batches=len(batches)
    print(f"Total batches:{total_batches}")
    
    all_fingerprints=load_existing_fingerprints()
    already_done=get_already_processed(all_fingerprints)
    
    if already_done:
        print(f"Resuming-{len(already_done)} photos already processed..")
    
    for i, batch in enumerate(batches):
        print(f"\n  Batch {i+1}/{total_batches}")

        new_batch = [(fid, fname) for fid, fname in batch
                     if fname not in already_done]

        if not new_batch:
            print("  ✅ Already done, skipping")
            continue

        print(f"  {len(new_batch)} new photos")

        # ✅ only ONE call to download_batch
        results  = download_batch(new_batch)
        print(results)
        if not results:
            print("  No photos downloaded, skipping...")
            continue

        paths    = [path for path, fid in results]
        file_ids = [fid  for path, fid in results]
        new_fps  = process_batch(paths, file_ids)

        all_fingerprints.extend(new_fps)
        already_done     = get_already_processed(all_fingerprints)
        all_fingerprints = save_fingerprints(all_fingerprints)

        delete_batch(paths)

        pct = int((i + 1) / total_batches * 100)
        print(f"  Progress: {pct}% | "
              f"Fingerprints: {len(all_fingerprints)}")

        print("\nALL photos processed..!")
        print(f"Total fingerprints:{len(all_fingerprints)}")
    
    # ...............Step 3........
    print(f"Step 3: Grouping faces by person..")
    
    fingerprints=load_fingerprints()
    if not fingerprints:
        print("No fingerprints found..!!")
        return False
    groups=group_faces(fingerprints,eps=0.5,min_samples=2)
    save_groups(groups)
    
    total_people=len([p for p in groups if p!="Unknown"])
    print(f"FOund {total_photos} peoples")
    
    
    # # ..........Step 4.....
    # print(f"Step 4: Organizing groups in folder..")
    # group=load_groups()
    # organize_results(group,output_dir=output_dir)
    
    # print("\n" + "=" * 50)
    # print("✅ DONE!")
    # print("=" * 50)
    # print(f"📸 Total photos processed : {total_photos}")
    # print(f"👥 Total people found     : {total_people}")
    # print(f"📂 Output folder          : {output_dir}/")
    # print("\nPeople found:")
    # for person, faces in sorted(groups.items()):
    #     photos = set(f["filename"] for f in faces)
    #     print(f"  {person:12s} → {len(photos):3d} photos")

    # print(f"\n✅ Check your '{output_dir}/' folder!")
    # return True



