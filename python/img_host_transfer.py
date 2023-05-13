"""
The MIT License (MIT)

Copyright (c) 2023 Huang, Po-Hsuan (aben20807@gmail.com)

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
import glob
import os
import re
import shutil
import requests
import argparse
import json
import hashlib
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


def get_image_data_list_from_md(md_file):
    """Extracts image URLs and their captions from a Markdown file."""
    with open(md_file, "r") as f:
        md_content = f.read()

    pattern = r"!\[(.*)\]\(((?!https://drive.google.com).*?)( \".*\")?\)"
    matches = re.findall(pattern, md_content)

    cnt = 0  # for anonymous images and avoid images with same caption
    image_data_list = []
    for match in matches:
        image_caption = match[0]
        if image_caption.strip() != "":
            image_caption = (
                "".join([x if x.isalnum() else "_" for x in image_caption])[:100]
                + f"_{cnt}"
            )
        else:
            image_caption = os.path.splitext(os.path.basename(md_file))[0] + f"_{cnt}"
        cnt += 1

        image_url: str = match[1]
        if not image_url.startswith("http"):
            continue
        image_data = {"caption": image_caption, "url": image_url, "old_url": image_url}
        print(image_data)
        image_data_list.append(image_data)

    # Special case for google drive images
    pattern = r"!\[(.*)\]\((https://drive.google.com/open.+id=([^\"]+?))( \".*\")?\)"
    matches = re.findall(pattern, md_content)
    for match in matches:
        image_caption = match[0]
        if image_caption.strip() != "":
            image_caption = (
                "".join([x if x.isalnum() else "_" for x in image_caption])[:100]
                + f"_{cnt}"
            )
        else:
            image_caption = os.path.splitext(os.path.basename(md_file))[0] + f"_{cnt}"
        cnt += 1
        image_old_url = match[1]
        image_url = "https://lh3.googleusercontent.com/d/" + match[2]
        image_data = {
            "caption": image_caption,
            "url": image_url,
            "old_url": image_old_url,
        }
        print(image_data)
        image_data_list.append(image_data)

    # Special case for title images
    # we do not need to download images hosted on unsplash
    pattern = r"image = \"((?!https://images.unsplash.com).+)\""
    matches = re.findall(pattern, md_content)
    for match in matches:
        image_caption = f"{os.path.splitext(os.path.basename(md_file))[0]}_banner"
        image_url = match
        image_data = {
            "caption": image_caption,
            "url": image_url,
            "old_url": image_url,
        }
        print(image_data)
        image_data_list.append(image_data)

    return image_data_list


def get_imgur_data_list_from_md(md_file):
    """ used for HackMD """
    with open(md_file, "r") as f:
        md_content = f.read()
    
    cnt = 0  # for anonymous images and avoid images with same caption
    image_data_list = []

    pattern = r"(https?://(i.)?imgur.com/[^\ \n)\"]*)"
    matches = re.findall(pattern, md_content)

    cnt = 0  # for anonymous images and avoid images with same caption
    image_data_list = []
    for match in matches:
        image_caption = ""
        if image_caption.strip() != "":
            image_caption = (
                "".join([x if x.isalnum() else "_" for x in image_caption])[:100]
                + f"_{cnt}"
            )
        else:
            image_caption = os.path.splitext(os.path.basename(md_file))[0] + f"_{cnt}"
        cnt += 1

        image_url: str = match[0]
        if not image_url.startswith("http"):
            continue
        image_data = {"caption": image_caption, "url": image_url, "old_url": image_url}
        print(image_data)
        image_data_list.append(image_data)

    return image_data_list

def download_image(file_name, image_url):
    """Downloads an image from a URL and saves it to a file."""
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            with open(file_name, "wb") as f:
                f.write(response.content)
                print("Downloaded", file_name)
        else:
            print(image_url)
            raise HttpError("Failed to download", image_url)

    except HttpError as error:
        print(f"An error occurred: {error}")
        raise


def get_file_id_if_exist(drive_service, folder_id, file_name) -> str:
    # Ref: https://developers.google.com/drive/api/guides/search-files?hl=en#specific
    # we use sha256 Checksum to compare local file and the remote file
    try:
        page_token = None
        while True:
            response = (
                drive_service.files()
                .list(
                    q=f"'{folder_id}' in parents",
                    spaces="drive",
                    fields="nextPageToken, files(id, sha256Checksum)",
                    pageToken=page_token,
                )
                .execute()
            )
            files = response.get("files", [])

            for file in files:
                if hashlib.sha256(open(file_name, "rb").read()).hexdigest() == file.get(
                    "sha256Checksum"
                ):
                    print(
                        f"File '{file_name}' already exists with ID {file.get('id')}."
                    )
                    return file.get("id")
            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken", None)
            if page_token is None:
                break
        return None
    except HttpError as error:
        print(f"An error occurred: {error}")
        raise


def upload_one_to_drive(drive_service, folder_id, file_name) -> str:
    file_metadata = {
        "name": os.path.splitext(os.path.basename(file_name))[0],
        "parents": [folder_id],
    }
    media = MediaFileUpload(file_name, resumable=True)

    file = (
        drive_service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    print(f"File '{file_name}' created with ID {file.get('id')}.")
    return file.get("id")


def upload_all_to_drive(drive_service, folder_id, file_names):
    try:
        new_urls = []
        for file_name in file_names:
            file_id = get_file_id_if_exist(drive_service, folder_id, file_name)
            if file_id is None:
                file_id = upload_one_to_drive(drive_service, folder_id, file_name)
            new_urls.append(f"https://lh3.googleusercontent.com/d/{file_id}")
        return new_urls
    except HttpError as error:
        print(f"An error occurred: {error}")
        raise


# Replace old URLs with new URLs in Markdown file
def replace_urls_in_md(old_urls, new_urls, md_file):
    with open(md_file, "r") as f:
        md_content = f.read()

    for old_url, new_url in zip(old_urls, new_urls):
        md_content = md_content.replace(old_url, new_url)

    with open(md_file, "w") as f:
        f.write(md_content)
        print(f"Markdown file {md_file} updated with new URLs.")


def build_drive_service(credentials_file):
    try:
        with open(credentials_file, "r") as f:
            credentials = json.load(f)
        credentials = service_account.Credentials.from_service_account_info(
            credentials, scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive_service = build("drive", "v3", credentials=credentials)
        return drive_service
    except HttpError as error:
        print(f"An error occurred: {error}")
        raise


def get_folder_id_if_exist(drive_service, folder_name, parent_id):
    # Ref: https://developers.google.com/drive/api/guides/search-files?hl=en#specific
    try:
        page_token = None
        while True:
            response = (
                drive_service.files()
                .list(
                    q=f"mimeType = 'application/vnd.google-apps.folder' and '{parent_id}' in parents",
                    spaces="drive",
                    fields="nextPageToken, files(id, name)",
                    pageToken=page_token,
                )
                .execute()
            )
            folders = response.get("files", [])

            for folder in folders:
                if folder_name == folder.get("name"):
                    print(
                        f"Folder '{folder_name}' already exists with ID {folder.get('id')}."
                    )
                    return folder.get("id")
            folders.extend(response.get("files", []))
            page_token = response.get("nextPageToken", None)
            if page_token is None:
                break
        return None
    except HttpError as error:
        print(f"An error occurred: {error}")
        raise


def get_or_create_folder(drive_service, folder_name, parent_id):
    folder_id = get_folder_id_if_exist(drive_service, folder_name, parent_id)
    if folder_id is not None:
        return folder_id

    try:
        # Create one
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = (
            drive_service.files().create(body=folder_metadata, fields="id").execute()
        )
        print(f"Folder '{folder_name}' created with ID {folder.get('id')}.")
        return folder.get("id")
    except HttpError as error:
        print(f"An error occurred: {error}")
        raise


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Download images from a markdown file and upload them to Google Drive."
    )
    parser.add_argument(
        "credentials", type=str, help="Path to the service account credentials file."
    )
    parser.add_argument("-f", "--md-file", type=str, help="Path to the markdown file.")
    parser.add_argument(
        "-r",
        "--dir",
        type=str,
        help="Path to the directory which contains markdown files.",
    )
    parser.add_argument(
        "--hackmd",
        help="For processing imgur images for HackMD",
        action='store_true'
    )
    args = parser.parse_args()
    # load .env file for root_id
    load_dotenv()
    root_id = os.getenv("root_id")

    md_files = []
    if args.md_file is not None:
        md_files.append(args.md_file)

    if args.dir is not None:
        md_files.extend(glob.glob(os.path.join(args.dir, "*.md"), recursive=True))

    print(f"Totel: {len(md_files)} markdown file(s)")
    for idx, md_file in enumerate(md_files):
        # if idx+1 <= 5: # used to continue process after solving issues during runtime
        #     continue
        # if "ouo" in md_file: # file to be skip
        #     continue
        print(f"\n\nProcess #{idx+1} {md_file}")
        print("> Find all image links and captions in the markdown file")
        if args.hackmd:
            print("> HackMD mode (replace all imgur images)")
            image_data_list = get_imgur_data_list_from_md(md_file)
        else:
            image_data_list = get_image_data_list_from_md(md_file)
        
        if len(image_data_list) == 0:
            print("> No image found in this markdown file; go to next")
            continue
        
        os.makedirs("tmp", exist_ok=True)

        print("> Download all images based on the URLs")
        file_names = []
        for image_data in image_data_list:
            file_name = os.path.join("tmp/", image_data.get("caption"))
            file_names.append(file_name)
            if not os.path.exists(file_name):  # TODO: check if need redownload files
                download_image(file_name, image_data.get("url"))

        print("> Create folder")
        folder_name = os.path.splitext(os.path.basename(md_file))[0]
        drive_service = build_drive_service(args.credentials)
        folder_id = get_or_create_folder(drive_service, folder_name, root_id)

        print("> Upload the downloaded images to Google Drive")
        new_urls = upload_all_to_drive(drive_service, folder_id, file_names)

        print("> Replace old URLs with new URLs in Markdown file")
        old_urls = [image_data.get("old_url") for image_data in image_data_list]
        replace_urls_in_md(old_urls, new_urls, md_file)

        # Delete all temporary files
        # shutil.rmtree("tmp") # TODO: delete downloaded files


if __name__ == "__main__":
    main()
