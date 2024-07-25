import ftplib
import os
import hashlib
import json

def calculate_sha256(file_path):
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def generate_file_hashes(directory, exclude_files=None):
    """Generate SHA-256 hashes for all files in the given directory, excluding specified files."""
    file_hashes = {}
    exclude_files = exclude_files or []
    for root, dirs, files in os.walk(directory):
        for file_name in files:
            # Skip excluded files
            if file_name in exclude_files:
                continue
            file_path = os.path.join(root, file_name)
            relative_path = os.path.relpath(file_path, directory)
            file_hashes[relative_path] = calculate_sha256(file_path)
    return file_hashes

def create_ftp_directory(ftp, directory_path):
    """Create directory structure on FTP server."""
    parts = directory_path.split('/')
    path = ''
    for part in parts:
        if part:
            path = f'{path}/{part}'
            try:
                ftp.mkd(path)
                print(f'Created directory: {path}')
            except ftplib.error_perm as e:
                if not str(e).startswith('550'):  # Directory already exists
                    raise

def upload_file(ftp, file_path, remote_path):
    """Upload a file to the FTP server."""
    remote_dir = os.path.dirname(remote_path)
    create_ftp_directory(ftp, remote_dir)
    print(f'Uploading file: {file_path} to {remote_path}')
    with open(file_path, 'rb') as f:
        ftp.storbinary(f'STOR {remote_path}', f)
    print(f'Uploaded file: {file_path}')

def list_all_files_ftp(ftp, path):
    """Recursively list all files in a given directory on the FTP server."""
    all_files = []
    dirs = [path]
    while dirs:
        current_dir = dirs.pop()
        try:
            items = ftp.nlst(current_dir)
            for item in items:
                if item.endswith('/'):
                    dirs.append(item)
                else:
                    all_files.append(item)
        except ftplib.error_perm as e:
            if not str(e).startswith('550'):  # Directory not found
                raise
    return all_files

def main():
    ftp_server = os.getenv('FTP_HOST')
    ftp_username = os.getenv('FTP_USERNAME')
    ftp_password = os.getenv('FTP_PASSWORD')
    ftp_directory = os.getenv('FTP_DIR', './')
    local_directory = os.getenv('LOCAL_DIR', './')
    hash_file_name = os.getenv('HASH_FILE', '.file_hashes.json')

    # Name of the script file
    script_file_name = os.path.basename(__file__)

    print('Connecting to FTP server...')
    ftp = ftplib.FTP(ftp_server)
    ftp.login(user=ftp_username, passwd=ftp_password)
    ftp.set_pasv(True)
    print('Connected to FTP server.')

    print(f'Changing to directory: {ftp_directory}')
    ftp.cwd(ftp_directory)
    print(f'Changed to directory: {ftp_directory}')

    first_time_upload = False
    try:
        print(f'Checking for existing hash file: {hash_file_name}')
        ftp.retrbinary(f'RETR {hash_file_name}', open(hash_file_name, 'wb').write)
        with open(hash_file_name, 'r') as f:
            server_file_hashes = json.load(f)
        print(f'Found existing hash file: {hash_file_name}')
    except ftplib.error_perm:
        print(f'No existing hash file found. Assuming first-time upload.')
        server_file_hashes = {}
        first_time_upload = True

    print(f'Generating file hashes for local directory: {local_directory}')
    current_file_hashes = generate_file_hashes(local_directory, exclude_files=[script_file_name])
    print('Generated file hashes.')

    files_to_upload = []
    if first_time_upload:
        print('First time upload: Uploading all files.')
        files_to_upload = list(current_file_hashes.keys())
    else:
        print('Determining modified or new files...')
        for file, hash in current_file_hashes.items():
            if current_file_hashes[file] != server_file_hashes.get(file):
                print(f'File modified or new: {file}')
                files_to_upload.append(file)
            else:
                print(f'File unchanged: {file}')
        print(f'Files to upload: {files_to_upload}')

    for file in files_to_upload:
        local_file_path = os.path.join(local_directory, file)
        remote_file_path = os.path.join(ftp_directory, file)
        upload_file(ftp, local_file_path, remote_file_path)

    with open(hash_file_name, 'w') as f:
        json.dump(current_file_hashes, f)
    print(f'Uploading hash file: {hash_file_name}')
    upload_file(ftp, hash_file_name, os.path.join(ftp_directory, hash_file_name))
    print(f'Uploaded hash file: {hash_file_name}')

    print('Closing FTP connection...')
    ftp.quit()
    print('FTP connection closed.')

if __name__ == '__main__':
    main()
