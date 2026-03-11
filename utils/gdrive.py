import requests

API_KEY="AIzaSyCjVsbLzGx7bmuWkAFlQSLA_rpq-KqZDhI"

IMAGE_EXT =(".jpg",".jpeg",'.png',".webp",".bmp")

def get_folder_link(link):
    if "/folders/" in link:
        folder_id = link.split("/folders/")[1]
        folder_id=folder_id.split("?")[0]
        folder_id=folder_id.strip()
        folder_id=folder_id.strip("/")
        folder_id = folder_id.strip("\\")
        print(f"Cleaned folder ID: '{folder_id}'")
        return folder_id
    else:
        print("ERROR: not valid google drive folder link")
        return None
    
def get_all_file_ids(folder_id):
    print(f"Connecting to Google Drive...")
    print(f"Folder ID: {folder_id}")
    
    url = "https://www.googleapis.com/drive/v3/files"

    all_files = []
    next_page=None
    
    while True:
        params={
            "q":f" '{folder_id}' in parents and trashed =false",
            "key":API_KEY,
            "fields":"nextPageToken, files(id,name)",
            "pageSize":1000,
        }
        print(f"Query being sent: {params['q']}")

        if next_page:
            params["pageToken"]=next_page
        response =requests.get(url,params=params)
        
        if response.status_code!=200:
            print(f"ERROR: {response.status_code}")
            print(response.json())
            return []
        
        data=response.json()
        files = data.get("files",[])
        
        print(f"Found {len(files)} files in this page..")
        
        for file in files:
            name=file["name"]
            file_id = file["id"]
            
            if name.lower().endswith(IMAGE_EXT):
                all_files.append((file_id,name))
        
        next_page=data.get("nextPageToken")
        if not next_page:
            break
    
    print(f"Total image found: {len(all_files)}")
    return all_files


def make_download_url(file_id):
    return f"https://drive.google.com/uc?export=download&id={file_id}"