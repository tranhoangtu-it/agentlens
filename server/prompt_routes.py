"""FastAPI router for prompt template and version management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_deps import get_current_user
from auth_models import User
from prompt_models import PromptTemplateIn, PromptTemplateOut, PromptVersionIn, PromptVersionOut
from prompt_storage import (
    add_version,
    create_prompt,
    diff_versions,
    get_prompt,
    get_version,
    list_prompts,
    list_versions,
)

router = APIRouter(prefix="/api", tags=["prompts"])


# ── Prompt Templates ─────────────────────────────────────────────────────────


@router.get("/prompts")
def list_prompt_templates(user: User = Depends(get_current_user)):
    """List all prompt templates for the authenticated user."""
    templates = list_prompts(user_id=user.id)
    return {"prompts": templates}


@router.post("/prompts", status_code=201)
def create_prompt_template(body: PromptTemplateIn, user: User = Depends(get_current_user)):
    """Create a new named prompt template."""
    if not body.name.strip():
        raise HTTPException(422, "Prompt name must not be empty")
    template = create_prompt(user_id=user.id, name=body.name.strip())
    return template


@router.get("/prompts/{prompt_id}", response_model=PromptTemplateOut)
def get_prompt_template(prompt_id: str, user: User = Depends(get_current_user)):
    """Get a prompt template with all its versions."""
    template = get_prompt(prompt_id=prompt_id, user_id=user.id)
    if not template:
        raise HTTPException(404, "Prompt template not found")
    versions = list_versions(prompt_id=prompt_id, user_id=user.id)
    result = PromptTemplateOut(
        id=template.id,
        user_id=template.user_id,
        name=template.name,
        latest_version=template.latest_version,
        created_at=template.created_at,
        updated_at=template.updated_at,
        versions=[
            PromptVersionOut(
                id=v.id,
                prompt_id=v.prompt_id,
                version=v.version,
                content=v.content,
                variables_json=v.variables_json,
                metadata_json=v.metadata_json,
                created_at=v.created_at,
            )
            for v in versions
        ],
    )
    return result


# ── Prompt Versions ──────────────────────────────────────────────────────────


@router.post("/prompts/{prompt_id}/versions", status_code=201)
def add_prompt_version(
    prompt_id: str,
    body: PromptVersionIn,
    user: User = Depends(get_current_user),
):
    """Add a new version to an existing prompt template."""
    if not body.content.strip():
        raise HTTPException(422, "Version content must not be empty")
    version = add_version(
        prompt_id=prompt_id,
        content=body.content,
        variables=body.variables,
        metadata=body.metadata,
        user_id=user.id,
    )
    if not version:
        raise HTTPException(404, "Prompt template not found")
    return version


@router.get("/prompts/{prompt_id}/versions/{version_number}")
def get_prompt_version(
    prompt_id: str,
    version_number: int,
    user: User = Depends(get_current_user),
):
    """Get a specific version of a prompt template."""
    version = get_version(prompt_id=prompt_id, version=version_number, user_id=user.id)
    if not version:
        raise HTTPException(404, "Prompt version not found")
    return version


@router.get("/prompts/{prompt_id}/diff")
def diff_prompt_versions(
    prompt_id: str,
    v1: int = Query(..., description="First version number"),
    v2: int = Query(..., description="Second version number"),
    user: User = Depends(get_current_user),
):
    """Return unified diff between two versions of a prompt."""
    if v1 == v2:
        raise HTTPException(422, "v1 and v2 must be different version numbers")
    result = diff_versions(prompt_id=prompt_id, v1=v1, v2=v2, user_id=user.id)
    if not result:
        raise HTTPException(404, "One or both versions not found")
    return result
