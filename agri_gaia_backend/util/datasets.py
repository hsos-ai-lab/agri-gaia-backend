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

import xmltodict
from typing import List, Optional
from fastapi import HTTPException
from fastapi.datastructures import UploadFile


def validate_name(name: str):
    if (
        name.lower() == "shapes"
        or name.lower() == "ontologies"
        or name.lower() == "agrovoc"
    ):
        raise HTTPException(
            status_code=400,
            detail="Cannot be named 'shapes', 'ontologies' or 'agrovoc'",
        )


def validate_dataresource_configuration_files(
    type: Optional[str], files: Optional[List[UploadFile]]
):
    """
    Validates if all configuration files for a specific dataset type are present.

    Args:
        type: The Dataset Type, which should be created.
        files: The list of uploaded files.

    Returns:
        a dictionary containing all relevant configuration files for the desired Dataset type.
    """
    if type == "AgriSyntheticImageDataResource" and files != None:
        foundConfig = None
        foundAssetCatalog = None
        for file in files:
            if file.filename == "asset_catalog.yaml":
                foundAssetCatalog = file
            if file.filename == "job_config.syclops.yaml":
                foundConfig = file
        if foundConfig is None or foundAssetCatalog is None:
            raise HTTPException(
                status_code=400,
                detail="No Config Files found.",
            )
        else:
            return {"config": foundConfig, "asset_catalog": foundAssetCatalog}
    return


def is_cvat_annotation_xml(annotation_file: UploadFile) -> bool:
    try:
        annotation_file_bytes = annotation_file.file.read()
        annotation_xml = xmltodict.parse(annotation_file_bytes)
        return (
            "annotations" in annotation_xml
            and "task" in annotation_xml["annotations"]["meta"]
        )
    except:
        return False
    finally:
        annotation_file.file.seek(0)
