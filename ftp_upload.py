import ftplib
import os
import json
import time

def get_file_mod_times(directory, exclude_files=None, exclude_dirs=None):
    """Get modification times for all files in the given directory, excluding specified files and directories."""
    file_mod_times = {}
    exclude_files = exclude_files or []
    exclude_dirs = exclude_dirs or []
    for root, dirs, files in os.walk(directory):
        # Exclude specified directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file_name in files:
            # Skip excluded files
            if file_name in exclude_files:
                continue
            file_path = os.path.join(root, file_name)
            relative_path = os.path.relpath(file_path, directory)
            file_mod_times[relative_path] = os.path.getmtime(file_path)
    return file_mod_times

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

def list_files_ftp(ftp, path):
    """List all files in a given directory on the FTP server."""
    file_list = []
    try:
        ftp.retrlines(f'LIST {path}', file_list.append)
    except ftplib.error_perm as e:
        print(f'Error listing files: {e}')
    return file_list

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
    mod_times_file_name = os.getenv('MOD_TIMES_FILE', '.file_mod_times.json')

    # Print environment variable values
    print(f'FTP Server: {ftp_server}')
    print(f'FTP Username: {ftp_username}')
    print(f'FTP Password: {ftp_password}')
    print(f'FTP Directory: {ftp_directory}')
    print(f'Local Directory: {local_directory}')
    print(f'Modification Times File Name: {mod_times_file_name}')

    # List files in the local directory
    print(f'Listing files in local directory: {local_directory}')
    list_files_in_directory(local_directory)

    print('Connecting to FTP server...')
    # Connect to the FTP server
    ftp = ftplib.FTP(ftp_server)
    ftp.login(user=ftp_username, passwd=ftp_password)
    ftp.set_pasv(True)
    print('Connected to FTP server.')

    # List all files and folders on the FTP server before changing the directory
    print('Listing all files and folders on the FTP server after authentication:')
    all_files_on_ftp = list_files_ftp(ftp, '/')
    for file in all_files_on_ftp:
        print(file)

    # Change to the desired directory
    print(f'Changing to directory: {ftp_directory}')
    ftp.cwd(ftp_directory)
    print(f'Changed to directory: {ftp_directory}')

    # Check for existing modification times file on the server
    first_time_upload = False
    try:
        print(f'Checking for existing modification times file: {mod_times_file_name}')
        ftp.retrbinary(f'RETR {mod_times_file_name}', open(mod_times_file_name, 'wb').write)
        with open(mod_times_file_name, 'r') as f:
            server_file_mod_times = json.load(f)
        print(f'Found existing modification times file: {mod_times_file_name}')
    except ftplib.error_perm:
        print(f'No existing modification times file found. Assuming first-time upload.')
        server_file_mod_times = {}
        first_time_upload = True

    # Get current file modification times, excluding the script file and specified directories
    script_file_name = 'ftp_upload.py'  # Assuming the script is named ftp_upload.py
    print(f'Getting file modification times for local directory: {local_directory}')
    current_file_mod_times = get_file_mod_times(local_directory, exclude_files=[script_file_name], exclude_dirs=['.git', '.github'])
    print(f'Got file modification times: {current_file_mod_times}')

    # Determine files to upload
    files_to_upload = []
    if first_time_upload:
        print('First time upload: Uploading all files.')
        files_to_upload = list(current_file_mod_times.keys())
    else:
        print('Determining modified or new files...')
        for file, mod_time in current_file_mod_times.items():
            if current_file_mod_times[file] != server_file_mod_times.get(file):
                print(f'File modified or new: {file}')
                files_to_upload.append(file)
            else:
                print(f'File unchanged: {file}')
        print(f'Files to upload: {files_to_upload}')

    # Upload files
    for file in files_to_upload:
        local_file_path = os.path.join(local_directory, file)
        remote_file_path = os.path.join(ftp_directory, file)
        upload_file(ftp, local_file_path, remote_file_path)

    # Upload the modification times file
    with open(mod_times_file_name, 'w') as f:
        json.dump(current_file_mod_times, f)
    print(f'Uploading modification times file: {mod_times_file_name}')
    upload_file(ftp, mod_times_file_name, os.path.join(ftp_directory, mod_times_file_name))
    print(f'Uploaded modification times file: {mod_times_file_name}')

    # Close the connection
    print('Closing FTP connection...')
    ftp.quit()
    print('FTP connection closed.')

if __name__ == '__main__':
    main()
