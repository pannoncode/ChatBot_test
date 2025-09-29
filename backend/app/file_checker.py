from werkzeug.datastructures import FileStorage

ALLOWED_EXTENSIONS = {"pdf", "txt", "docx", "md"}
ALLOWED_MIMETYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/markdown",
    "text/x-markdown",
}


def file_checker(file: FileStorage):
    file_name = file.filename
    ext = file_name.lower().split(".")[-1]
    
    return (
        {
            "valid": ext in ALLOWED_EXTENSIONS and
            file.mimetype in ALLOWED_MIMETYPES,
            "extension": ext
        }

    )
