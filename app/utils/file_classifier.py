class FileClassifier:
    """Utility class for classifying and checking file types"""

    @staticmethod
    def is_csv_or_excel(file_type: str, file_ext: str) -> bool:
        """Kiểm tra xem file có phải là CSV hoặc Excel không"""
        csv_types = ["text/csv", "application/csv"]
        excel_types = [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ]
        excel_extensions = [".xls", ".xlsx"]
        csv_extensions = [".csv"]

        return (
            file_type in csv_types or
            file_type in excel_types or
            file_ext.lower() in excel_extensions or
            file_ext.lower() in csv_extensions
        )

    @staticmethod
    def is_pdf(file_type: str, file_ext: str) -> bool:
        """Kiểm tra xem file có phải là PDF không"""
        return file_type == "application/pdf" or file_ext.lower() == ".pdf"

    @staticmethod
    def is_image(file_type: str, file_ext: str) -> bool:
        """Kiểm tra xem file có phải là hình ảnh không"""
        image_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"]
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]

        return (
            file_type in image_types or
            file_ext.lower() in image_extensions
        )

    @staticmethod
    def is_text(file_type: str, file_ext: str) -> bool:
        """Kiểm tra xem file có phải là text không"""
        text_types = ["text/plain", "text/html", "text/xml", "application/json"]
        text_extensions = [".txt", ".html", ".xml", ".json", ".md"]

        return (
            file_type in text_types or
            file_ext.lower() in text_extensions
        )

    @staticmethod
    def is_video(file_type: str, file_ext: str) -> bool:
        """Kiểm tra xem file có phải là video không"""
        video_types = ["video/mp4", "video/avi", "video/mov", "video/wmv", "video/mkv"]
        video_extensions = [".mp4", ".avi", ".mov", ".wmv", ".mkv", ".webm"]

        return (
            file_type in video_types or
            file_ext.lower() in video_extensions
        )

    @staticmethod
    def is_audio(file_type: str, file_ext: str) -> bool:
        """Kiểm tra xem file có phải là audio không"""
        audio_types = ["audio/mp3", "audio/wav", "audio/flac", "audio/aac", "audio/ogg"]
        audio_extensions = [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"]

        return (
            file_type in audio_types or
            file_ext.lower() in audio_extensions
        )

    @staticmethod
    def get_file_category(file_type: str, file_ext: str) -> str:
        """Xác định category của file"""
        if FileClassifier.is_csv_or_excel(file_type, file_ext):
            return "spreadsheet"
        elif FileClassifier.is_pdf(file_type, file_ext):
            return "document"
        elif FileClassifier.is_image(file_type, file_ext):
            return "image"
        elif FileClassifier.is_text(file_type, file_ext):
            return "text"
        elif FileClassifier.is_video(file_type, file_ext):
            return "video"
        elif FileClassifier.is_audio(file_type, file_ext):
            return "audio"
        else:
            return "other"
