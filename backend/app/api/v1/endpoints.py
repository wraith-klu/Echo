import os
import shutil
import time
import soundfile as sf
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logger import logger
from app.core.database import get_db
from app.services.ingestion import UPLOAD_DIR, validate_and_convert_audio
from app.services.language_detection import LanguageDetectionService, SUPPORTED_LANGUAGES
from app.services.translation import NLLB_LANG_MAP

router = APIRouter()

@router.get("/status")
def get_status():
    """
    Returns the status of the pipeline components (ASR, Translation, TTS).
    """
    logger.info("Status endpoint queried.")
    from app.main import ml_models
    asr_status = "ready" if "asr" in ml_models else "pending_load"
    translation_status = "ready" if "translation" in ml_models else "pending_load"
    tts_status = "ready" if "tts" in ml_models else "pending_load"
    return {
        "services": {
            "ingestion": "ready",
            "asr": asr_status,
            "translation": translation_status,
            "tts": tts_status
        }
    }


@router.post("/audio/upload")
async def upload_audio_file(
    file: UploadFile = File(...),
    device_id: str = Form("upload_client")
):
    """
    HTTP POST endpoint to upload a complete WAV or other audio file for testing.
    Validates sample rate, channels, bit depth, and converts it if needed.
    """
    logger.info(f"Received audio file upload request: filename='{file.filename}', device_id='{device_id}'")

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Naming convention: device_id + timestamp + original extension
    timestamp = int(time.time() * 1000)
    _, ext = os.path.splitext(file.filename)
    if not ext:
        ext = ".wav"  # Default to WAV extension if none provided
    
    temp_filename = f"{device_id}_{timestamp}_temp{ext}"
    temp_file_path = os.path.join(UPLOAD_DIR, temp_filename)

    # Save uploaded file contents to a temporary file on disk first
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Saved raw uploaded file to temporary path: {temp_file_path}")
    except Exception as e:
        logger.error(f"Failed to write uploaded file to disk: {e}")
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Could not save upload: {str(e)}")

    # Run the validation and conversion utility
    try:
        validated_file_path = validate_and_convert_audio(temp_file_path)
    except Exception as e:
        logger.error(f"Audio validation/conversion failed: {e}")
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=400,
            detail=f"Audio validation failed. Ensure the file is a valid audio format. Details: {str(e)}"
        )

    # Read verified metadata to send back to the user
    try:
        info = sf.info(validated_file_path)
        data, _ = sf.read(validated_file_path)
        duration = len(data) / info.samplerate

        return {
            "status": "success",
            "filename": os.path.basename(validated_file_path),
            "original_filename": file.filename,
            "device_id": device_id,
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "duration_sec": round(duration, 3),
            "subtype": info.subtype,
            "path": validated_file_path
        }
    except Exception as e:
        logger.error(f"Failed to read validated audio metadata: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Validated audio was created, but metadata parsing failed: {str(e)}"
        )


@router.post("/audio/transcribe")
async def transcribe_audio_endpoint(
    file: UploadFile = File(None),
    filename: str = Form(None),
    source_language: str = Form(None),
    target_language: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Transcribes an audio file, detects/validates its language, and optionally translates.
    Accepts:
    1. An uploaded file (multipart/form-data)
    2. A filename of a previously saved file in the upload directory
    3. Optional source_language override parameter
    4. Optional target_language for translation (defaults to None = no translation)
    """
    logger.info("ASR transcription + LID + Translation endpoint called.")
    from app.main import ml_models
    asr_service = ml_models.get("asr")
    if not asr_service:
        raise HTTPException(
            status_code=503,
            detail="ASR model service is not initialized or loaded."
        )

    # Validate source_language if overridden by client
    if source_language:
        source_language_clean = source_language.strip().lower()
        if not LanguageDetectionService.is_language_supported(source_language_clean):
            raise HTTPException(
                status_code=400,
                detail=f"Specified source language '{source_language}' is not supported. Supported languages: {sorted(list(SUPPORTED_LANGUAGES))}"
            )
    else:
        source_language_clean = None

    file_path = None

    if file:
        # Direct upload flow
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        timestamp = int(time.time() * 1000)
        _, ext = os.path.splitext(file.filename)
        if not ext:
            ext = ".wav"
        temp_name = f"direct_transcribe_{timestamp}{ext}"
        file_path = os.path.join(UPLOAD_DIR, temp_name)
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            # Validate/convert to standard format
            file_path = validate_and_convert_audio(file_path)
        except Exception as e:
            logger.error(f"Processing uploaded file failed: {e}")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=400, detail=f"Failed to process uploaded file: {str(e)}")

    elif filename:
        # Previously saved file flow
        filename_clean = os.path.basename(filename)
        file_path = os.path.join(UPLOAD_DIR, filename_clean)
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Audio file '{filename_clean}' not found in upload directory."
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either an uploaded 'file' or a 'filename' of a saved file."
        )

    try:
        from app.services.pipeline import PipelineOrchestrator
        from fastapi.responses import FileResponse
        
        result = await PipelineOrchestrator.run(
            file_path=file_path,
            ml_models=ml_models,
            device_id="REST_Client",
            source_language_override=source_language_clean,
            target_language=target_language,
            db=db,
        )
        
        if result.status == "error":
            raise HTTPException(status_code=500, detail=result.error)
            
        return {
            "status": result.status,
            "filename": result.filename,
            "duration": result.duration,
            "message": result.message,
            "transcription": result.transcription,
            "translation": result.translation,
            "tts": result.tts,
            "latencies": result.latencies
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ASR/LID/Translation endpoint failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")



@router.get("/audio/tts/{filename}")
async def get_tts_audio_endpoint(filename: str):
    """
    Serves a generated TTS audio WAV file from the upload directory.
    """
    from fastapi.responses import FileResponse
    filename_clean = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_DIR, filename_clean)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"TTS audio file '{filename_clean}' not found."
        )
    return FileResponse(file_path, media_type="audio/wav", filename=filename_clean)


# ---------------------------------------------------------------------------
# History endpoint
# ---------------------------------------------------------------------------

@router.get("/history")
async def get_translation_history(
    device_id: Optional[str] = Query(None, description="Filter by device firmware ID"),
    session_id: Optional[str] = Query(None, description="Filter by session UUID"),
    limit: int = Query(50, ge=1, le=200, description="Max rows to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns paginated translation history.

    Optional filters:
    - **device_id**: firmware identifier of the device (e.g. 'ESP32_001')
    - **session_id**: UUID of a specific session
    """
    from app.services.db_service import get_history
    return await get_history(db, device_id=device_id, session_id=session_id, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# Devices endpoint
# ---------------------------------------------------------------------------

@router.get("/devices")
async def list_devices(
    active_only: bool = Query(False, description="Return only currently active devices"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists all devices that have ever connected to the backend.
    """
    from app.services.db_service import get_devices
    devices = await get_devices(db, active_only=active_only, limit=limit, offset=offset)
    return {
        "total": len(devices),
        "items": [
            {
                "id": d.id,
                "device_id": d.device_id,
                "name": d.name,
                "description": d.description,
                "registered_at": d.registered_at.isoformat() if d.registered_at else None,
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
                "is_active": d.is_active,
                "meta": d.meta,
            }
            for d in devices
        ],
    }
