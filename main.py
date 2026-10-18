import os
import shutil
import tempfile
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from converters.image_converter import convert_image, get_image_targets
from converters.document_converter import convert_document, get_document_targets, SUPPORTED_INPUTS
from stats_manager import record_visit, record_conversion, get_stats

app = FastAPI(title="FileConvert", description="파일 변환기 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static", html=True), name="static")

IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "gif", "bmp", "tiff", "tif", "ico"}
DOC_EXTS   = {"pdf", "txt", "docx", "html", "htm", "csv", "xlsx", "md"}


def detect_category(ext: str) -> str:
    ext = ext.lower().lstrip(".")
    if ext in IMAGE_EXTS:
        return "image"
    if ext in DOC_EXTS:
        return "document"
    return "unknown"


@app.middleware("http")
async def track_visitors_middleware(request: Request, call_next):
    # Only track page views or stats requests, exclude static assets
    path = request.url.path
    if path == "/" or not path.startswith("/static"):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"
        record_visit(client_ip)

    response = await call_next(request)
    return response


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/api/stats")
async def stats_endpoint():
    return get_stats()


@app.get("/api/targets")
async def targets(filename: str, category: str):
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if category == "image":
        return {"targets": get_image_targets(ext)}
    elif category == "document":
        return {"targets": get_document_targets(ext)}
    return {"targets": []}


@app.post("/api/convert")
async def convert_file(
    file: UploadFile = File(...),
    output_format: str = Form(...),
    category: str = Form(...),
):
    ext = os.path.splitext(file.filename or "file.bin")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_in:
        shutil.copyfileobj(file.file, tmp_in)
        tmp_in_path = tmp_in.name

    # Measure uploaded file size for stats
    file_size_bytes = os.path.getsize(tmp_in_path)

    out_suffix = f".{output_format.lower()}"
    tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=out_suffix)
    tmp_out.close()
    tmp_out_path = tmp_out.name

    try:
        if category == "image":
            convert_image(tmp_in_path, tmp_out_path, output_format)
        elif category == "document":
            convert_document(tmp_in_path, tmp_out_path, output_format)
        else:
            raise HTTPException(status_code=400, detail="알 수 없는 카테고리입니다.")

        # Record conversion size upon successful conversion
        record_conversion(file_size_bytes)

        with open(tmp_out_path, "rb") as f:
            content = f.read()

        base = os.path.splitext(file.filename or "converted")[0]
        download_name = f"{base}.{output_format.lower()}"

        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        for p in (tmp_in_path, tmp_out_path):
            try:
                os.unlink(p)
            except Exception:
                pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8088))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
