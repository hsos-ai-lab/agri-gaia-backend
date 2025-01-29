# SPDX-FileCopyrightText: 2024 University of Applied Sciences Osnabrück
# SPDX-FileContributor: Andreas Schliebitz
# SPDX-FileContributor: Henri Graf
# SPDX-FileContributor: Jonas Tüpker
# SPDX-FileContributor: Lukas Hesse
# SPDX-FileContributor: Maik Fruhner
# SPDX-FileContributor: Prof. Dr.-Ing. Heiko Tapken
# SPDX-FileContributor: Tobias Wamhof
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import io
import logging
from pathlib import Path
import tempfile
from typing import List, Optional
import uuid
import zipfile
from fastapi import status
import git


# main.py or a new router file
from fastapi import APIRouter, File, Response, UploadFile, Form, HTTPException, Depends
import git.exc
from sqlalchemy.orm import Session
from agri_gaia_backend.routers.common import check_exists, get_db
from agri_gaia_backend.schemas.container_template import (
    InferenceContainerTemplateCreate,
    InferenceContainerTemplate,
    InferenceContainerTemplateUpdateParams,
)
from agri_gaia_backend.db import container_template_api as db_api
from agri_gaia_backend.services.container_template.definitions import (
    INFERENCE_CONTAINER_TEMPLATES_DIR,
)
from agri_gaia_backend.services.container_template.validation import (
    ContainerTemplateValidationException,
    InferenceContainerTemplateValidator,
)
from agri_gaia_backend.util import common

ROOT_PATH = "/inference-container-templates"

logger = logging.getLogger("api-logger")
router = APIRouter(prefix=ROOT_PATH)


@router.get("", response_model=List[InferenceContainerTemplate])
def list_templates(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db_api.get_container_templates(db, skip, limit)


@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    container_template = check_exists(db_api.get_container_template(db, template_id))
    common.rm(INFERENCE_CONTAINER_TEMPLATES_DIR / container_template.dirname)
    db_api.delete_container_template(db, container_template)
    return Response(status_code=204)


@router.post("/create/upload", response_model=InferenceContainerTemplate)
def create_template_from_zipfile(
    name: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    with tempfile.TemporaryDirectory() as template_directory:
        zip_bytes = file.file.read()
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(template_directory)
            files = os.listdir(template_directory)
            if len(files) == 1:
                temp = os.path.join(template_directory, files[0])
                if os.path.isdir(temp):
                    template_directory = temp
        try:
            InferenceContainerTemplateValidator().validate(template_directory)
        except ContainerTemplateValidationException as e:
            raise HTTPException(400, str(e))

        dirname = _install_template(template_directory)

        template_create = InferenceContainerTemplateCreate(
            name=name,
            description=description,
            source="upload",
            dirname=dirname,
        )
        return db_api.create_container_template(db, template_create)


@router.post("/create/git", response_model=InferenceContainerTemplate)
def create_template_from_git(
    name: str = Form(...),
    description: str = Form(None),
    git_url: str = Form(...),
    git_ref: str = Form(...),
    git_username: str = Form(None),
    git_access_token: str = Form(None),
    db: Session = Depends(get_db),
):
    with tempfile.TemporaryDirectory() as template_directory:
        _clone_git_repo(
            git_url, git_ref, template_directory, git_username, git_access_token
        )
        try:
            InferenceContainerTemplateValidator().validate(template_directory)
            dirname = _install_template(template_directory)
        except ContainerTemplateValidationException as e:
            raise HTTPException(400, str(e))

        template_create = InferenceContainerTemplateCreate(
            name=name,
            description=description,
            source="git",
            dirname=dirname,
            git_url=git_url,
            git_ref=git_ref,
        )
        return db_api.create_container_template(db, template_create)


@router.patch("/{template_id}/update-from-git")
def update_git_template(
    template_id: int,
    params: InferenceContainerTemplateUpdateParams,
    db: Session = Depends(get_db),
):
    inference_container_template = check_exists(
        db_api.get_container_template(db, template_id)
    )
    if inference_container_template.source != "git":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The container template can't be updated because the template wasn't created using a git type source",
        )
    with tempfile.TemporaryDirectory() as temp_directory:
        _clone_git_repo(
            inference_container_template.git_url,
            params.git_ref,
            temp_directory,
            params.git_username,
            params.git_access_token,
        )
        try:
            InferenceContainerTemplateValidator().validate(temp_directory)
            template_dir_path = (
                INFERENCE_CONTAINER_TEMPLATES_DIR / inference_container_template.dirname
            )
            common.rm(template_dir_path)
            common.mv(temp_directory, template_dir_path)
        except ContainerTemplateValidationException as e:
            raise HTTPException(
                400, f"The update was cancelled due to the following reason: {str(e)}"
            )
        inference_container_template.git_ref = params.git_ref
        return db_api.update_container_template(db, inference_container_template)


def _install_template(template_directory: Path) -> None:
    installation_dirname = str(uuid.uuid4()).replace("-", "")
    installation_path = INFERENCE_CONTAINER_TEMPLATES_DIR / installation_dirname

    common.mv(template_directory, installation_path)

    return installation_dirname


def _clone_git_repo(
    git_url: str,
    git_ref: str,
    destination_dir: str,
    git_username: Optional[str],
    git_access_token: Optional[str],
) -> None:
    if git_access_token is not None:
        if git_username is None:
            git_username = "token_user"
        auth_url = git_url.replace(
            "https://", f"https://{git_username}:{git_access_token}@"
        )
    else:
        auth_url = git_url
    logger.info(auth_url)
    try:
        repo = git.Repo.clone_from(auth_url, destination_dir)
    except git.exc.GitCommandError as e:
        logger.exception(e)
        raise HTTPException(400, f"Error cloning git repository '{git_url}'")

    try:
        repo.git.checkout(git_ref)
    except git.exc.GitCommandError as e:
        logger.exception(e)
        raise HTTPException(400, f"Error checking out reference '{git_ref}'")
