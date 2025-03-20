# SPDX-FileCopyrightText: 2024 University of Applied Sciences Osnabrück
# SPDX-FileContributor: Andreas Schliebitz
# SPDX-FileContributor: Henri Graf
# SPDX-FileContributor: Jonas Tüpker
# SPDX-FileContributor: Lukas Hesse
# SPDX-FileContributor: Maik Fruhner
# SPDX-FileContributor: Prof. Dr.-Ing. Heiko Tapken
# SPDX-FileContributor: Tobias Wamhof
#
# SPDX-License-Identifier: MIT

from sqlalchemy.orm import Session
from agri_gaia_backend.db.models import InferenceContainerTemplate
from agri_gaia_backend.schemas.container_template import (
    InferenceContainerTemplateCreate,
)
from typing import List, Optional


def get_container_template(
    db: Session, template_id: int
) -> Optional[InferenceContainerTemplate]:
    return (
        db.query(InferenceContainerTemplate)
        .filter(InferenceContainerTemplate.id == template_id)
        .first()
    )


def get_container_templates(
    db: Session, skip: int = 0, limit: int = 100
) -> List[InferenceContainerTemplate]:
    return db.query(InferenceContainerTemplate).offset(skip).limit(limit).all()


def create_container_template(
    db: Session, template_create: InferenceContainerTemplateCreate
) -> InferenceContainerTemplate:
    db_template = InferenceContainerTemplate(
        name=template_create.name,
        description=template_create.description,
        source=template_create.source,
        dirname=template_create.dirname,
        git_url=template_create.git_url,
        git_ref=template_create.git_ref,
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


def update_container_template(
    db: Session, template: InferenceContainerTemplate
) -> InferenceContainerTemplate:
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def delete_container_template(
    db: Session, template: InferenceContainerTemplate
) -> bool:
    db.delete(template)
    db.commit()
    return True
