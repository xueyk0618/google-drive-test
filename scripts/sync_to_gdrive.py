import os
import json
import base64
import zipfile
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def main():
    print("🔍 [诊断 1/4] 正在检查环境变量注入...")
    raw_key = os.environ.get('GCP_SA_KEY', '').strip()
    folder_id = os.environ.get('GDRIVE_FOLDER_ID', '').strip()

    if not raw_key:
        print("\n❌ 严重错误：GCP_SA_KEY 环境变量为空字符串！")
        print("💡 导致此问题的唯一原因：GitHub Secrets 配置不正确。")
        print("请检查：")
        print(" 1. 进入 GitHub 仓库 -> Settings -> Secrets and variables -> Actions")
        print(" 2. 确认 Secret 属于 'Repository secrets'（仓库级机密），而非上方的 'Environment secrets'。")
        print(" 3. 确认 Secret 的名称为 GCP_SA_KEY（无额外空格，区分大小写）。\n")
        raise ValueError("GCP_SA_KEY 环境变量为空")

    print(f"✅ GCP_SA_KEY 读取成功（长度: {len(raw_key)} 字符）")

    if not folder_id:
        raise ValueError("❌ 错误：GDRIVE_FOLDER_ID 环境变量为空！请检查 GitHub Secrets 配置。")

    print("🔍 [诊断 2/4] 解析 JSON 凭据...")
    key_info = None

    # 尝试直接 JSON 解析
    try:
        key_info = json.loads(raw_key)
        print("✅ JSON 直接解析成功")
    except json.JSONDecodeError:
        # 尝试 Base64 解码后解析（应对特殊换行符处理）
        try:
            decoded = base64.b64decode(raw_key).decode('utf-8')
            key_info = json.loads(decoded)
            print("✅ Base64 解码并解析 JSON 成功")
        except Exception as e:
            print(f"❌ 解析凭据失败！前 15 个字符为: '{raw_key[:15]}...'")
            print("💡 排查建议：请使用代码编辑器（如 VS Code）全选复制 .json 文件原文，重新粘贴到 GCP_SA_KEY 中。")
            raise e

    scopes = ['[https://www.googleapis.com/auth/drive.file](https://www.googleapis.com/auth/drive.file)']
    creds = service_account.Credentials.from_service_account_info(key_info, scopes=scopes)
    service = build('drive', 'v3', credentials=creds)

    # 打包仓库代码
    print("📦 [诊断 3/4] 正在压缩代码库...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"backup_{timestamp}.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            if '.git' in root or '.github' in root or '__pycache__' in root:
                continue
            for file in files:
                if file == zip_filename:
                    continue
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, '.'))

    # 上传至 Google Drive
    print("🚀 [诊断 4/4] 开始上传至 Google Drive...")
    file_metadata = {
        'name': zip_filename,
        'parents': [folder_id]
    }
    media = MediaFileUpload(zip_filename, mimetype='application/zip', resumable=True)
    
    uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id, name').execute()
    print(f"🎉 上传成功！文件名称: {uploaded_file.get('name')}, File ID: {uploaded_file.get('id')}")

    if os.path.exists(zip_filename):
        os.remove(zip_filename)

if __name__ == '__main__':
    main()
