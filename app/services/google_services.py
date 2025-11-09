from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from typing import List, Dict, Optional
from app.utils import get_logger
import io

logger = get_logger(__name__)


class GoogleServices:

    @staticmethod
    def list_sheets(access_token: str, page_token: Optional[str] = None, page_size: int = 50) -> Dict:
        """
        List Google Sheets in the user's drive using OAuth access token with pagination support

        Args:
            access_token: OAuth access token
            page_token: Optional page token for pagination (from previous response)
            page_size: Number of files to return per page (default: 50, max: 1000)

        Returns:
            Dict with 'files' (list) and 'next_page_token' (str or None)
        """
        creds = Credentials(token=access_token)

        try:
            service = build("drive", "v3", credentials=creds)

            # Limit page_size to Google Drive API max (1000)
            page_size = min(page_size, 1000)

            response = service.files().list(
                q="(mimeType='application/vnd.google-apps.spreadsheet' or mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')",
                spaces="drive",
                fields="nextPageToken, files(id, name)",
                pageToken=page_token,
                pageSize=page_size
            ).execute()

            files = response.get("files", [])
            next_page_token = response.get("nextPageToken", None)

            return {
                "files": files,
                "next_page_token": next_page_token
            }

        except HttpError as e:
            logger.error(f"Google API Error: {e}")
            raise e

    @staticmethod
    def search_spreadsheet(access_token: str, keyword: str) -> List[Dict]:
        """
        Search Google Sheets by name (case-insensitive, contains search)
        """
        creds = Credentials(token=access_token)

        try:
            service = build("drive", "v3", credentials=creds)

            # Chuẩn rồi nhé, nhưng nếu muốn logic rõ ràng hơn về điều kiện AND/OR, nên thêm dấu ngoặc:
            query = (
                f"(mimeType='application/vnd.google-apps.spreadsheet' or "
                f"mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') "
                f"and name contains '{keyword}'"
            )

            response = service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)"
            ).execute()

            files = response.get("files", [])

            return files

        except HttpError as e:
            logger.error(f"Google API Error: {e}")
            raise e

    @staticmethod
    def list_pdfs(access_token: str, page_token: Optional[str] = None, page_size: int = 50) -> Dict:
        """
        List PDF files in the user's drive using OAuth access token with pagination support

        Args:
            access_token: OAuth access token
            page_token: Optional page token for pagination (from previous response)
            page_size: Number of files to return per page (default: 50, max: 1000)

        Returns:
            Dict with 'files' (list) and 'next_page_token' (str or None)
        """
        creds = Credentials(token=access_token)

        try:
            service = build("drive", "v3", credentials=creds)

            # Limit page_size to Google Drive API max (1000)
            page_size = min(page_size, 1000)

            response = service.files().list(
                q="mimeType='application/pdf'",
                spaces="drive",
                fields="nextPageToken, files(id, name)",
                pageToken=page_token,
                pageSize=page_size
            ).execute()

            files = response.get("files", [])
            next_page_token = response.get("nextPageToken", None)

            return {
                "files": files,
                "next_page_token": next_page_token
            }

        except HttpError as e:
            logger.error(f"Google API Error: {e}")
            raise e

    @staticmethod
    def search_pdf(access_token: str, keyword: str) -> List[Dict]:
        """
        Search PDF files by name (case-insensitive, contains search)
        """
        creds = Credentials(token=access_token)

        try:
            service = build("drive", "v3", credentials=creds)

            query = f"mimeType='application/pdf' and name contains '{keyword}'"

            response = service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)"
            ).execute()

            files = response.get("files", [])

            return files

        except HttpError as e:
            logger.error(f"Google API Error: {e}")
            raise e

    @staticmethod
    def get_file_info(access_token: str, file_id: str) -> Dict:
        """
        Get file information from Google Drive

        Args:
            access_token: OAuth access token
            file_id: Google Drive file ID

        Returns:
            Dict with file information (id, name, mimeType, size)
        """
        creds = Credentials(token=access_token)

        try:
            service = build("drive", "v3", credentials=creds)

            file_metadata = service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size"
            ).execute()

            return file_metadata

        except HttpError as e:
            logger.error(f"Google API Error getting file info: {e}")
            raise e

    @staticmethod
    def download_file(access_token: str, file_id: str, mime_type: str) -> bytes:
        """
        Download file from Google Drive

        Args:
            access_token: OAuth access token
            file_id: Google Drive file ID
            mime_type: File MIME type

        Returns:
            File content as bytes
        """
        creds = Credentials(token=access_token)

        try:
            service = build("drive", "v3", credentials=creds)

            # For PDF files, download directly
            request = service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            file_content.seek(0)
            return file_content.read()

        except HttpError as e:
            logger.error(f"Google API Error downloading file: {e}")
            raise e

    @staticmethod
    def export_sheet(access_token: str, file_id: str, format: str = 'xlsx') -> bytes:
        """
        Export Google Sheet to specified format

        Args:
            access_token: OAuth access token
            file_id: Google Drive file ID
            format: Export format (xlsx, csv, pdf, etc.)

        Returns:
            Exported file content as bytes
        """
        creds = Credentials(token=access_token)

        try:
            service = build("drive", "v3", credentials=creds)

            # Map format to MIME type
            mime_type_map = {
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'csv': 'text/csv',
                'pdf': 'application/pdf',
                'ods': 'application/vnd.oasis.opendocument.spreadsheet'
            }

            export_mime_type = mime_type_map.get(format.lower(), mime_type_map['xlsx'])

            # Export the file
            request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            file_content.seek(0)
            return file_content.read()

        except HttpError as e:
            logger.error(f"Google API Error exporting sheet: {e}")
            raise e
