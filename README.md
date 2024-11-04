# Simple FTP Deploy Action

This GitHub Action uploads files and directories to an FTP server. It computes the SHA-256 hash of each file to determine which files have changed and only uploads modified or new files.

## Features

- Upload files and directories to an FTP server
- Compute SHA-256 hashes to detect changes
- Only upload modified or new files
- Maintain a hash file on the server to track file changes

## Usage

### Inputs

- `host`: The FTP server hostname (required)
- `username`: The FTP server username (required)
- `password`: The FTP server password (required)
- `ftpdir`: The directory on the FTP server to upload files to (default: `./`)
- `localdir`: The local directory to upload (default: `./`)
- `hashfile`: The name of the hash file to track changes (default: `.file_hashes.json`)

### Example Workflow

Create a workflow file (e.g., `.github/workflows/ftp_upload.yml`) in your repository with the following content:

```yaml
name: FTP Upload

on: [push]

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.x'

      - name: Upload files to FTP
        uses: akilaid/simple-ftp-deploy@v1
        with:
          host: ${{ secrets.FTP_HOST }}
          username: ${{ secrets.FTP_USERNAME }}
          password: ${{ secrets.FTP_PASSWORD }}
          ftpdir: '/path/on/ftp/server'
          localdir: './path/to/local/files'
          hashfile: '.file_hashes.json'
