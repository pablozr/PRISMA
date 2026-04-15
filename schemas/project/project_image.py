from typing import Optional, TypedDict


class ProjectLogoUploadDataResponse(TypedDict):
    projeto_id: int
    image_url: str
    alt_text: Optional[str]


class ProjectLogoUploadResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectLogoUploadDataResponse]
