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

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from agri_gaia_backend.services.docker import image_builder


async def _missing_input_data_exception_handler(
    request: Request, ex: image_builder.MissingInputDataException
):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(
            {
                "detail": "Missing properties",
                "exception_type": image_builder.MissingInputDataException.__name__,
                "body": {
                    "model": ex.model_properties,
                    "device": ex.device_properties,
                },
            }
        ),
    )
