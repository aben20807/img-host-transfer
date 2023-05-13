# Img Host Transfer

A Python script for changing image hosting service to google drive. It will download all images from markdown files and upload them to a specific google drive folder. After that, the shared links for newly uploaded images are used to replace old links in the original markdown files.

## Prerequisites

+ Online setting in [Google Cloud](https://console.cloud.google.com/):
  + New a project and switch on Google Drive API.
  + In the Credentials tab, create a Service Account. In this step, you will download a JSON file and name it `credentials.json`, please keep it secret.
  + Add the email of the Service Account as an editor to your root folder in google drive, i.e., share the Service Account the permission to modify
  + Open the permission to read for anybody to make everyone can access the image via the new links from your google drive
+ Local environment:
  + New a `.env` file, `root_id="<ROOT_ID>"`, where <ROOT_ID> is the root folder ID you want to place generated folders for markdown files. You can access it in your google drive from the folder URL; for example, `https://drive.google.com/drive/u/0/folders/XXXXXXXXXXXXXXXXXXXXXXX`, the `XXXXXXXXXXXXXXXXXXXXXXX` is the folder ID
  + Open a terminal, clone this repo and cd in, then type:

    ```bash
    $ virtualenv -p python3.8 .venv
    $ source .venv/bin/activate
    $ pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib python-dotenv
    ```

## Usage

### Single file

```bash
$ python python/img_host_transfer.py credentials.json --md-file ../blog-post/content/posts/20220729-weekly-collection.md
$ python python/img_host_transfer.py credentials.json -f ../blog-post/content/posts/gallery-demo.md
```

### Apply all markdown files in a directory

```bash
$ python python/img_host_transfer.py credentials.json -r ../blog-post/content/posts/
```

### Backup Imgur images for HackMD

Note: no HackMD API

Recommended steps after the above prerequisites:

1. Download all markdown files from the note setting `HackMD_User_00000000000/` from the web GUI
2. In the `HackMD_User_00000000000/`, use `git init`, `git add .`, and `git commit -m "init"` sequentially so that you can find which files are updated easily
3. Use the following command to backup your Imgur images to your Google Drive, this command will replace the old Imgur URL with a new Google Drive URL after being uploaded

```bash
$ python python/img_host_transfer.py credentials.json --hackmd -r ../HackMD_User_00000000000/
```

4. Depends on how much time you want to spend
   1. Upload the folder (`HackMD_User_00000000000/`) which contains the updated markdown files to your Google Drive folder which contains uploaded images (or a Github repo). When you find the image in HackMD is disappear, go to your Google Drive folder (or the Github repo) to find the image
   2. Replace the local updated markdown files to your HackMD account

## Disclaimer

This tool works for me, but it might not work for you. Always make a backup first. I am not responsible for any loss or corruption of data.

## License

MIT
