from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from .client import R2Client


router = APIRouter(prefix="/cloudflare", tags=["cloudflare"])


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a .jsonocel file to Cloudflare R2.

    Args:
        file: The uploaded file (multipart/form-data)

    Returns:
        dict: Contains the UUID4 token for the uploaded file

    Raises:
        HTTPException: If upload fails
    """
    try:
        file_content = await file.read()

        r2_client = R2Client()

        file_uuid = await r2_client.upload_file(
            file_content=file_content, filename=file.filename
        )

        return JSONResponse(status_code=200, content={"uuid": file_uuid})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
