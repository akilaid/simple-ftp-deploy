import ftplib
import os
import hashlib
import json

def calculate_md5(file_path):
    """Calculate MD5 hash of a file."""
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()

def generate_file_hashes(directory, exclude_files=None, exclude_dirs=None):
    """Generate MD5 hashes for all files in the given directory, excluding specified files and directories."""
    file_hashes = {}
    exclude_files = exclude_files or []
    exclude_dirs = exclude_dirs or []
    for root, dirs, files in os.walk(directory):
        # Exclude specified directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file_name in files:
            # Skip excluded files
            if file_name in exclude_files:
                print(f"Skipping excluded file: {file_name}")
                continue
            file_path = os.path.join(root, file_name)
            relative_path = os.path.relpath(file_path, directory)
            file_hashes[relative_path] = calculate_md5(file_path)
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

def delete_extra_files_on_ftp(ftp, server_file_hashes, local_file_hashes):
    """Delete files from the FTP server that do not exist in the local files."""
    files_deleted = []
    for file in list(server_file_hashes.keys()):
        if file not in local_file_hashes:
            print(f'Deleting extra file on server: {file}')
            try:
                ftp.delete(file)
                print(f'Deleted file: {file}')
                files_deleted.append(file)
            except ftplib.error_perm as e:
                if 'No such file or directory' in str(e):
                    print(f'File already deleted: {file}')
                else:
                    print(f'Error deleting file {file}: {e}')
    # Remove deleted files from server_file_hashes
    for file in files_deleted:
        del server_file_hashes[file]

def list_files_in_directory(directory):
    """List all files in the given directory and its subdirectories."""
    file_paths = []
    for root, dirs, files in os.walk(directory):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            file_paths.append(file_path)
            print(file_path)
    return file_paths

def main():
    # Retrieve values from environment variables
    ftp_server = os.getenv('FTP_HOST')
    ftp_username = os.getenv('FTP_USERNAME')
    ftp_password = os.getenv('FTP_PASSWORD')
    ftp_directory = os.getenv('FTP_DIR', './')
    local_directory = os.getenv('LOCAL_DIR', './')
    hash_file_name = os.getenv('HASH_FILE', '.file_hashes.json')

    # Print environment variable values
    print(f'FTP Server: {ftp_server}')
    print(f'FTP Username: {ftp_username}')
    print(f'FTP Password: {ftp_password}')
    print(f'FTP Directory: {ftp_directory}')
    print(f'Local Directory: {local_directory}')
    print(f'Hash File Name: {hash_file_name}')

    # Generate current file hashes, excluding the script file and specified directories
    script_file_name = 'ftp_upload.py'  # Assuming the script is named ftp_upload.py
    print(f'Generating file hashes for local directory: {local_directory}')
    current_file_hashes = generate_file_hashes(local_directory, exclude_files=[script_file_name], exclude_dirs=['.git', '.github'])
    print(f'Generated file hashes: {current_file_hashes}')

    print('Connecting to FTP server...')
    # Connect to the FTP server
    ftp = ftplib.FTP(ftp_server)
    ftp.login(user=ftp_username, passwd=ftp_password)
    ftp.set_pasv(True)
    print('Connected to FTP server.')

    # Change to the desired directory
    print(f'Changing to directory: {ftp_directory}')
    ftp.cwd(ftp_directory)
    print(f'Changed to directory: {ftp_directory}')

    # Check for existing hash file on the server
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

    # Determine files to upload
    files_to_upload = []

    if first_time_upload:
        print('First time upload: Uploading all files.')
        files_to_upload = list(current_file_hashes.keys())
    else:
        print('Determining modified or new files...')
        for file, hash in current_file_hashes.items():
            if file not in server_file_hashes:
                print(f'New file: {file}')
                files_to_upload.append(file)
            elif current_file_hashes[file] != server_file_hashes.get(file):
                print(f'Modified file: {file}')
                files_to_upload.append(file)

    print(f'Files to upload: {files_to_upload}')

    # Upload files
    for file in files_to_upload:
        local_file_path = os.path.join(local_directory, file)
        remote_file_path = os.path.join(ftp_directory, file)
        upload_file(ftp, local_file_path, remote_file_path)

    # Delete extra files on the server
    print('Deleting extra files on the server...')
    delete_extra_files_on_ftp(ftp, server_file_hashes, current_file_hashes)
    print('Deleted extra files on the server.')

    # Update the server_file_hashes with current_file_hashes after file operations
    server_file_hashes.update(current_file_hashes)

    # Save the updated hash file locally again to reflect any changes made by delete_extra_files_on_ftp
    with open(hash_file_name, 'w') as f:
        json.dump(server_file_hashes, f)

    # Upload the updated hash file to the server
    print(f'Uploading hash file: {hash_file_name}')
    upload_file(ftp, hash_file_name, os.path.join(ftp_directory, hash_file_name))
    print(f'Uploaded hash file: {hash_file_name}')

    # Close the connection
    print('Closing FTP connection...')
    ftp.quit()
    print('FTP connection closed.')

if __name__ == '__main__':
    main()
