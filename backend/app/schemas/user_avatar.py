from pydantic import BaseModel


class AvatarUploadResponse(BaseModel):
    etag: str
