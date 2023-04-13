from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests
import re
import os.path
import argparse
import requests
import uuid
import shutil


def download_image(file_name, url):
    """Downloads an image from a URL and saves it to a file."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(file_name, "wb") as f:
                f.write(response.content)
                print("Downloaded", file_name)
        else:
            raise SystemError("Failed to download", url)
    except Exception as e:
        raise SystemError("Error downloading", url, ":", str(e))


def upload_image(album_id, file_path):
    """Uploads an image file to the specified Google Photos album."""
    # Ref: https://stackoverflow.com/a/52021690
    # Ref: https://github.com/googleapis/google-api-python-client/issues/651#issuecomment-487398468
    # Ref: https://developers.google.com/photos/library/guides/upload-media?hl=en
    try:
        # Upload the image file to Google Photos
        headers = {
            "Content-Type": "application/octet-stream",
            "X-Goog-Upload-File-Name": file_path.encode("utf-8"),
            "X-Goog-Upload-Protocol": "raw",
            "Authorization": "Bearer " + creds.token,
        }
        data = open(file_path, "rb").read()
        response = requests.post(
            "https://photoslibrary.googleapis.com/v1/uploads",
            headers=headers,
            data=data,
        )
        upload_token = response.text

        # Add the uploaded image to the album
        request_body = {
            "albumId": album_id,
            "newMediaItems": [
                {
                    "simpleMediaItem": {
                        "fileName": os.path.basename(file_path),
                        "uploadToken": upload_token,
                    }
                }
            ],
        }
        response = photos_service.mediaItems().batchCreate(body=request_body).execute()
        items = response.get("newMediaItemResults", [])
        image_id = items[0]["mediaItem"]["id"]
        media_item = photos_service.mediaItems().get(mediaItemId=image_id).execute()
        # Get the URL of the uploaded image
        if len(items) == 1:
            print(media_item)
            # ERROR: the link expire after approximately 60 minutes.
            # https://developers.google.com/photos/library/guides/best-practices?hl=en#caching
            image_url = media_item["baseUrl"] + "=w2048-h1024"
            print(f"Image '{file_path}' uploaded to album and URL is: {image_url}")
            return image_url
        else:
            raise SystemError(
                f"An error occurred while uploading image '{file_path}' to album"
            )

    except HttpError as error:
        raise SystemError(
            f"An error occurred while uploading image '{file_path}' to album: {error}"
        )


def create_album_if_not_exists(album_name):
    """Creates a new album in Google Photos with the given name if it doesn't already exist."""
    results = photos_service.albums().list().execute()
    albums = results.get("albums", [])
    from pprint import pprint

    # pprint(albums)
    for album in albums:
        if "title" in album.keys():
            print(album["title"])
        if "title" in album.keys() and album["title"] == album_name:
            print(f"Album '{album_name}' already exists with ID {album['id']}.")
            return album["id"]
    print(f"Creating album '{album_name}'...")
    new_album = (
        photos_service.albums().create(body={"album": {"title": album_name}}).execute()
    )
    album_id = new_album["id"]
    print(f"Album '{album_name}' created with ID {album_id}.")
    return album_id


def upload_to_album(album_title, file_names):
    """Uploads all images from a markdown file to a shared album on Google Photos."""
    try:
        # Create the album with the same name as the markdown file, if it doesn't exist
        album_id = create_album_if_not_exists(album_title)
        print(f"send images to album '{album_title}' ({album_id})")

        # Upload images to album and get new URLs
        new_urls = []
        for file_name in file_names:
            new_url = upload_image(album_id, file_name)
            if new_url:
                new_urls.append(new_url)
        return new_urls
    except Exception as e:
        raise SystemError("Error uploading to album:", str(e))


# Replace old URLs with new URLs in Markdown file
def replace_urls_in_md(old_urls, new_urls, md_file):
    with open(md_file, "r") as f:
        md_content = f.read()

    for old_url, new_url in zip(old_urls, new_urls):
        md_content = md_content.replace(old_url, new_url)

    with open(md_file, "w") as f:
        f.write(md_content)
        print(f"Markdown file {md_file} updated with new URLs.")


def get_image_data_list_from_md(md_file):
    """Extracts image URLs and their captions from a Markdown file."""
    with open(md_file, "r") as f:
        md_content = f.read()

    pattern = r"!\[(.*)\]\(((?!https://drive.google.com).*?)( \".*\")?\)"
    matches = re.findall(pattern, md_content)

    image_data_list = []
    for match in matches:
        image_caption = match[0]
        image_caption = (
            "".join([x if x.isalnum() else "_" for x in image_caption])
            if image_caption.strip() != ""
            else str(uuid.uuid4())
        )
        print(image_caption)
        image_url = match[1]
        image_data_list.append(
            {"caption": image_caption, "url": image_url, "old_url": image_url}
        )

    # Special case for google drive images
    pattern = r"!\[(.*)\]\((https://drive.google.com/open.+id=([^\"]+?))( \".*\")?\)"
    matches = re.findall(pattern, md_content)
    for match in matches:
        image_caption = match[0]
        image_caption = (
            "".join([x if x.isalnum() else "_" for x in image_caption])
            if image_caption.strip() != ""
            else str(uuid.uuid4())
        )
        print(image_caption)
        image_old_url = match[1]
        image_url = "https://lh3.googleusercontent.com/d/" + match[2]
        image_data_list.append(
            {"caption": image_caption, "url": image_url, "old_url": image_old_url}
        )

    return image_data_list


def setup(credentials_json):
    # Ref: https://ithelp.ithome.com.tw/articles/10282837
    SCOPES = ["https://www.googleapis.com/auth/photoslibrary"]
    # Set up the credentials object using the OAuth 2.0 flow

    global creds
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_json, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    # Build the service object
    try:
        global photos_service
        photos_service = build(
            "photoslibrary", "v1", credentials=creds, static_discovery=False
        )
        print("Google Photos API service created.")

    except HttpError as error:
        photos_service = None
        raise SystemError(f"An error occurred: {error}")


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("md_file", help="path to Markdown file")
    parser.add_argument("cred", help="path to Markdown file")
    args = parser.parse_args()

    setup(args.cred)

    # Get image URLs from Markdown file
    image_data_list = get_image_data_list_from_md(args.md_file)
    print(image_data_list)

    # Download images and get file names
    os.makedirs("tmp", exist_ok=True)
    file_names = []
    for image_data in image_data_list:
        file_name = os.path.join("tmp/", image_data["caption"])
        file_names.append(file_name)
        download_image(file_name, image_data["url"])

    # Create new album and upload images
    album_title = (
        "aben20807.github.io:" + os.path.splitext(os.path.basename(args.md_file))[0]
    )
    new_urls = upload_to_album(album_title, file_names)

    # Replace old URLs with new URLs in Markdown file
    img_urls = [image_data["old_url"] for image_data in image_data_list]
    replace_urls_in_md(img_urls, new_urls, args.md_file)
    shutil.rmtree("tmp")


if __name__ == "__main__":
    main()
