import os
import json
import base64
import re
import zipfile
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def get_credentials():
    # 优先读取 Base64 编码的密钥
    b64_key = os.environ.get('GCP_SA_KEY_BASE64', '').strip()
    raw_key = os.environ.get('GCP_SA_KEY', '').strip()

    if b64_key:
        print(f"🔍 检测到 GCP_SA_KEY_BASE64，长度: {len(b64_key)} 字符")
        # 仅保留合法的 ASCII 字符，剔除意外粘贴的不可见字符
        clean_b64 = re.sub(r'[^\x00-\x7F]+', '', b64_key)
        try:
            decoded_bytes = base64.b64decode(clean_b64)
            key_info = json.loads(decoded_bytes.decode('utf-8'))
            print("✅ 成功从 Base64 解码并解析 GCP 凭据")
            return key_info
        except Exception as e:
            print(f"❌ Base64 解码失败: {e}")
            raise

    if raw_key:
        print("🔍 检测到 GCP_SA_KEY (明文 JSON)，尝试解析...")
        try:
            return json.loads(raw_key)
        except Exception as e:
            print(f"❌ 明文 JSON 解析失败: {e}")
            raise

    raise ValueError("❌ 未找到有效的 GCP 凭据！请检查 GitHub Secrets 中的 GCP_SA_KEY_BASE64 配置。")

def main():
    folder_id = os.environ.get('GDRIVE_FOLDER_ID', '').strip()
    if not folder_id:
        raise ValueError("❌ GDRIVE_FOLDER_ID 环境变量为空！请检查 GitHub Secrets。")

    # 1. 认证并连接 Google Drive
    key_info = get_credentials()
    scopes = ['https://www.googleapis.com/auth/drive.file']
    creds = service_account.Credentials.from_service_account_info(key_info, scopes=scopes)
    service = build('drive', 'v3', credentials=creds)

    # 2. 将当前代码库打包为 zip
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"backup_{timestamp}.zip"
    exclude_dirs = {'.git', '.github', '__pycache__', 'venv'}

    print(f"📦 正在打包仓库代码为 {zip_filename}...")
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file == zip_filename:
                    continue
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, '.'))

    # 3. 上传到 Google Drive
    print(f"🚀 正在上传至 Google Drive 目标目录...")
    file_metadata = {
        'name': zip_filename,
        'parents': [folder_id]
    }
    media = MediaFileUpload(zip_filename, mimetype='application/zip', resumable=True)
    
    file = service.files().create(body=file_metadata, media_body=media, fields='id, name').execute()
    print(f"🎉 上传成功！文件名: {file.get('name')}, File ID: {file.get('id')}")

    # 4. 清理本地打包文件
    if os.path.exists(zip_filename):
        os.remove(zip_filename)

if __name__ == '__main__':
    main()
