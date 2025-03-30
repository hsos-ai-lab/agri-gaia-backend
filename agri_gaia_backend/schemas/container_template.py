# SPDX-FileCopyrightText: 2024 Osnabrück University of Applied Sciences
# SPDX-FileContributor: Andreas Schliebitz
# SPDX-FileContributor: Henri Graf
# SPDX-FileContributor: Jonas Tüpker
# SPDX-FileContributor: Lukas Hesse
# SPDX-FileContributor: Maik Fruhner
# SPDX-FileContributor: Prof. Dr.-Ing. Heiko Tapken
# SPDX-FileContributor: Tobias Wamhof
#
# SPDX-License-Identifier: MIT

# schemas/container_template.py
from pydantic import BaseModel
from typing import Optional


class InferenceContainerTemplateBase(BaseModel):
    name: str
    source: str
    dirname: str
    description: Optional[str] = None
    git_url: Optional[str] = None
    git_ref: Optional[str] = None


class InferenceContainerTemplateCreate(InferenceContainerTemplateBase):
    pass


class InferenceContainerTemplate(InferenceContainerTemplateBase):
    id: int

    class Config:
        from_attributes = True


class InferenceContainerTemplateUpdateParams(BaseModel):
    git_ref: str
    git_username: Optional[str]
    git_access_token: Optional[str]
