import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, status
from fastapi.responses import Response
from app.services.metadata.content_presets import ContentPresetService
from app.core.logging import logger

router = APIRouter()


@router.get("", response_model=List[Dict[str, Any]])
async def list_presets():
    """
    List all content niche presets, including Mahadev, Shinchan, and custom categories.
    """
    return ContentPresetService.list_presets()


@router.get("/export")
async def export_presets_json():
    """
    Export all presets and hooks as a downloadable JSON file.
    """
    json_data = ContentPresetService.export_presets_json()
    return Response(
        content=json_data,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=content_presets.json"}
    )


@router.get("/{preset_id}")
async def get_preset(preset_id: str):
    """
    Get a specific preset category by ID with its 31+ hooks and metadata.
    """
    preset = ContentPresetService.get_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Preset '{preset_id}' not found.")
    return preset


@router.post("")
async def save_or_update_preset(preset_data: Dict[str, Any]):
    """
    Create or update a preset category with custom hooks.
    """
    p_id = preset_data.get("id") or preset_data.get("name", "custom").lower().strip().replace(" ", "_")
    return ContentPresetService.save_preset(p_id, preset_data)


@router.post("/import")
async def import_presets(
    incoming_data: Optional[Dict[str, Any]] = None,
    overwrite_all: bool = Query(default=False)
):
    """
    Import presets from JSON body.
    """
    if not incoming_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No JSON data provided.")
    return ContentPresetService.import_presets(incoming_data, overwrite_all=overwrite_all)


@router.post("/upload-json")
async def upload_presets_json_file(
    file: UploadFile = File(...),
    overwrite_all: bool = Query(default=False)
):
    """
    Upload a .json file from computer containing custom presets and hooks.
    """
    try:
        content = await file.read()
        parsed_json = json.loads(content.decode("utf-8"))
        return ContentPresetService.import_presets(parsed_json, overwrite_all=overwrite_all)
    except json.JSONDecodeError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON file format: {err}")
    except Exception as e:
        logger.error(f"Failed to process uploaded JSON presets: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{preset_id}")
async def delete_preset(preset_id: str):
    """
    Delete a custom preset category.
    """
    deleted = ContentPresetService.delete_preset(preset_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Preset '{preset_id}' not found.")
    return {"message": f"Preset '{preset_id}' deleted successfully.", "id": preset_id}
