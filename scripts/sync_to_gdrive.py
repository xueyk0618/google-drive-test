import os
import json
import zipfile
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def main():
    # 1. 从环境变量获取 Secrets
    raw_key = os.environ.get('GCP_SA_KEY')
    folder_id = os.environ.get('GDRIVE_FOLDER_ID')

    if not raw_key or not folder_id:
        raise ValueError("缺少必须的环境变量：GCP_SA_KEY 或 GDRIVE_FOLDER_ID")

    # 2. 验证凭据
    scopes = ['https://www.googleapis.com/auth/drive.file']
    key_info = json.loads(raw_key)
    creds = service_account.Credentials.from_service_account_info(key_info, scopes=scopes)
    service = build('drive', 'v3', credentials=creds)

    # 3. 将当前项目打包为 Zip 文件（排除 .git 文件夹）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"backup_{timestamp}.zip"
    
    print(f"正在压缩代码库为 {zip_filename}...")
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            if '.git' in root or '.github' in root or '__pycache__' in root:
                continue
            for file in files:
                if file == zip_filename:
                    continue
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, '.'))

    # 4. 上传到 Google Drive
    print("开始上传至 Google Drive...")
    file_metadata = {
        'name': zip_filename,
        'parents': [folder_id]
    }
    media = MediaFileUpload(zip_filename, mimetype='application/zip', resumable=True)
    
    file = service.files().create(body=file_metadata, media_body=media, fields='id, name').execute()
    print(f"✅ 上传成功！文件名称: {file.get('name')}, File ID: {file.get('id')}")

    # 清理本地临时压缩包
    if os.path.exists(zip_filename):
        os.remove(zip_filename)

if __name__ == '__main__':
    main()
