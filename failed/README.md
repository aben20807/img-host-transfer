# Img Host Transfer

## Prerequisites

+ Online setting in [Google Cloud](https://console.cloud.google.com/):
  + New a project and switch on Photos Library API.
  + In the Credentials tab, create an API Keys and then create an OAuth 2.0 Client IDs (Application type: Desktop app). In this step, you will download a JSON file, e.g., `client_secret_640133986447-7mtpptingh5fgriar65n5erjjsqebup3.apps.googleusercontent.com.json`, please keep it secret.
+ Local environment:

```bash
$ virtualenv -p python3.8 .venv
$ source .venv/bin/activate
$ pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Run for a markdown file

+ A `token.json` will be generated, please keep it secret.

```bash
$ python python/img_host_transfer.py ../blog-post/content/posts/20190212-zeuzera-coffeae-nietner.md client_secret_640133986447-7mtpptingh5fgriar65n5erjjsqebup3.apps.googleusercontent.com.json
```
