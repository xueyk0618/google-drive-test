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
    """读取 Google Service Account 凭据"""

    b64_key = os.environ.get('GCP_SA_KEY_BASE64', '').strip()
    raw_key = os.environ.get('GCP_SA_KEY', '').strip()

    if b64_key:
        print(f"🔍 检测到 GCP_SA_KEY_BASE64，长度: {len(b64_key)} 字符")

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
        print("🔍 检测到 GCP_SA_KEY，尝试解析...")

        try:
            return json.loads(raw_key)

        except Exception as e:
            print(f"❌ 明文 JSON 解析失败: {e}")
            raise

    raise ValueError(
        "❌ 未找到有效的 GCP 凭据！"
        "请检查 GitHub Secrets 中的 GCP_SA_KEY_BASE64 配置。"
    )


def test_folder_access(service, folder_id):
    """检查 Service Account 是否能够访问目标文件夹"""

    print("🔎 正在检查 Google Drive 目标文件夹...")

    try:
        folder = service.files().get(
            fileId=folder_id,
            fields="id,name,mimeType,driveId",
            supportsAllDrives=True
        ).execute()

        print("✅ Google Drive 文件夹访问成功")
        print(f"📁 Folder Name: {folder.get('name')}")
        print(f"🆔 Folder ID: {folder.get('id')}")

        drive_id = folder.get("driveId")

        if drive_id:
            print(f"🗂️ Shared Drive ID: {drive_id}")
        else:
            print("⚠️ 当前文件夹没有 driveId，可能仍然位于 My Drive")

        return folder

    except Exception as e:
        print("❌ 无法访问目标 Google Drive 文件夹")
        raise


def main():

    # ==========================================================
    # 1. 获取 Google Drive Folder ID
    # ==========================================================

    folder_id = os.environ.get('GDRIVE_FOLDER_ID', '').strip()

    if not folder_id:
        raise ValueError(
            "❌ GDRIVE_FOLDER_ID 环境变量为空！"
            "请检查 GitHub Secrets。"
        )

    # ==========================================================
    # 2. Google Drive 认证
    # ==========================================================

    key_info = get_credentials()

    scopes = [
        'https://www.googleapis.com/auth/drive'
    ]

    creds = service_account.Credentials.from_service_account_info(
        key_info,
        scopes=scopes
    )

    service = build(
        'drive',
        'v3',
        credentials=creds
    )

    print("✅ Google Drive API 认证成功")

    # ==========================================================
    # 3. 检查目标文件夹
    # ==========================================================

    folder = test_folder_access(
        service,
        folder_id
    )

    # ==========================================================
    # 4. 打包当前 GitHub 仓库
    # ==========================================================

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    zip_filename = f"backup_{timestamp}.zip"

    exclude_dirs = {
        '.git',
        '.github',
        '__pycache__',
        'venv'
    }

    print(f"📦 正在打包仓库代码为 {zip_filename}...")

    with zipfile.ZipFile(
        zip_filename,
        'w',
        zipfile.ZIP_DEFLATED
    ) as zipf:

        for root, dirs, files in os.walk('.'):

            dirs[:] = [
                d for d in dirs
                if d not in exclude_dirs
            ]

            for file in files:

                # 防止 ZIP 把自己打包进去
                if file == zip_filename:
                    continue

                file_path = os.path.join(
                    root,
                    file
                )

                zipf.write(
                    file_path,
                    os.path.relpath(
                        file_path,
                        '.'
                    )
                )

    print(f"✅ 打包完成: {zip_filename}")

    # ==========================================================
    # 5. 上传到 Google Shared Drive
    # ==========================================================

    print("🚀 正在上传至 Google Drive 目标目录...")

    file_metadata = {
        'name': zip_filename,
        'parents': [folder_id]
    }

    media = MediaFileUpload(
        zip_filename,
        mimetype='application/zip',
        resumable=True
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id,name,parents,driveId',
        supportsAllDrives=True
    ).execute()

    # ==========================================================
    # 6. 输出上传结果
    # ==========================================================

    print("")
    print("🎉🎉🎉 上传成功！")
    print(f"📄 文件名: {file.get('name')}")
    print(f"🆔 File ID: {file.get('id')}")
    print(f"📁 Parent Folder: {file.get('parents')}")
    print(f"🗂️ Shared Drive ID: {file.get('driveId')}")
    print("")

    # ==========================================================
    # 7. 删除 GitHub Runner 上的临时 ZIP
    # ==========================================================

    if os.path.exists(zip_filename):
        os.remove(zip_filename)

        print("🧹 本地临时 ZIP 文件已清理")


if __name__ == '__main__':
    main()
