from app.crud.base import BaseCRUD
from app.models.file import File
from app.schemas.file import FileCreate, FileUpdate



class FileCRUD((BaseCRUD[File, FileCreate, FileUpdate])):
    def __init__(self):
        super().__init__(File)


