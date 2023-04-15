# Img Host Transfer

A Python script for changing image hosting service to google drive. It will download all images from markdown files and upload them to a specific google drive folder. After that, the shared links for newly uploaded images are used to replace old links in the original markdown files.

## Prerequisites

+ Online setting in [Google Cloud](https://console.cloud.google.com/):
  + New a project and switch on Google Drive API.
  + In the Credentials tab, create a Service Account. In this step, you will download a JSON file and name it `credentials.json`, please keep it secret.
  + Add the email of the Service Account as an editor to your root folder in google drive.
+ Local environment:
  + New a `.env` file, `root_id="<ROOT_ID>"`, where <ROOT_ID> is the root folder ID you want to place generated folders for markdown files. You can access it in your google drive from the folder URL
  + Open a terminal, clone this repo and cd in, then type:

    ```bash
    $ virtualenv -p python3.8 .venv
    $ source .venv/bin/activate
    $ pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib python-dotenv
    ```

## Run for a markdown file

Single file:

```bash
$ python python/img_host_transfer.py credentials.json --md-file ../blog-post/content/posts/20220729-weekly-collection.md
$ python python/img_host_transfer.py credentials.json -f ../blog-post/content/posts/gallery-demo.md
```

Apply all markdown files in a directory

```bash
$ python python/img_host_transfer.py credentials.json -r ../blog-post/content/posts/
```

## Disclaimer

This tool works for me, but it might not work for you. Always make a backup first. I am not responsible for any loss or corruption of data.
