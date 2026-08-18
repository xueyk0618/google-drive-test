import os
import zipfile
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def get_credentials():
    client_id = os.environ.get("GDRIVE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN", "").strip()

    if not client_id:
        raise ValueError("❌ GDRIVE_CLIENT_ID 未配置")

    if not client_secret:
        raise ValueError("❌ GDRIVE_CLIENT_SECRET 未配置")

    if not refresh_token:
        raise ValueError("❌ GDRIVE_REFRESH_TOKEN 未配置")

    print("🔐 正在使用 Google OAuth 认证...")

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[
            "https://www.googleapis.com/auth/drive"
        ]
    )

    print("✅ Google OAuth 凭据创建成功")

    return credentials


def main():

    # =========================================================
    # 1. 获取目标 Google Drive 文件夹
    # =========================================================

    folder_id = os.environ.get("GDRIVE_FOLDER_ID", "").strip()

    if not folder_id:
        raise ValueError(
            "❌ GDRIVE_FOLDER_ID 环境变量为空！"
        )

    # =========================================================
    # 2. Google Drive OAuth 认证
    # =========================================================

    credentials = get_credentials()

    service = build(
        "drive",
        "v3",
        credentials=credentials
    )

    print("✅ Google Drive API 认证成功")

    # =========================================================
    # 3. 检查目标文件夹
    # =========================================================

    print("🔎 正在检查 Google Drive 目标文件夹...")

    folder = service.files().get(
        fileId=folder_id,
        fields="id,name,mimeType,parents"
    ).execute()

    print("✅ Google Drive 文件夹访问成功")
    print(f"📁 Folder Name: {folder.get('name')}")
    print(f"🆔 Folder ID: {folder.get('id')}")

    # =========================================================
    # 4. 打包 GitHub 仓库
    # =========================================================

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    zip_filename = f"backup_{timestamp}.zip"

    exclude_dirs = {
        ".git",
        ".github",
        "__pycache__",
        "venv",
        ".venv"
    }

    print(f"📦 正在打包仓库代码为 {zip_filename}...")

    with zipfile.ZipFile(
        zip_filename,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zipf:

        for root, dirs, files in os.walk("."):

            dirs[:] = [
                d for d in dirs
                if d not in exclude_dirs
            ]

            for file in files:

                if file == zip_filename:
                    continue

                file_path = os.path.join(
                    root,
                    file
                )

                arcname = os.path.relpath(
                    file_path,
                    "."
                )

                zipf.write(
                    file_path,
                    arcname
                )

    print(f"✅ 打包完成: {zip_filename}")

    # =========================================================
    # 5. 上传 Google Drive
    # =========================================================

    print("🚀 正在上传至 Google Drive...")

    file_metadata = {
        "name": zip_filename,
        "parents": [folder_id]
    }

    media = MediaFileUpload(
        zip_filename,
        mimetype="application/zip",
        resumable=True
    )

    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id,name,parents"
    ).execute()

    print()
    print("=" * 60)
    print("🎉 上传成功！")
    print("=" * 60)
    print(f"📄 文件名: {uploaded_file.get('name')}")
    print(f"🆔 File ID: {uploaded_file.get('id')}")
    print(f"📁 Parent Folder: {uploaded_file.get('parents')}")
    print("=" * 60)

    # =========================================================
    # 6. 删除本地临时文件
    # =========================================================

    if os.path.exists(zip_filename):
        os.remove(zip_filename)

        print(
            f"🧹 已删除本地临时文件: {zip_filename}"
        )


if __name__ == "__main__":
    main()
