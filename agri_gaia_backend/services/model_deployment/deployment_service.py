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

from sqlalchemy.orm import Session

from ...db.models import ModelDeploymentStatus, EdgeDevice, Model

import logging

logger = logging.getLogger("api-logger")


def deploy_model_to_edge(
    model: Model, edge_device: EdgeDevice
) -> ModelDeploymentStatus:
    raise NotImplementedError("Edge Deployment is not implemented yet")
    return ModelDeploymentStatus.running


def undeploy_model_from_edge(
    model: Model, edge_deviec: EdgeDevice
) -> ModelDeploymentStatus:
    raise NotImplementedError("Edge Deployment is not implemented yet")
    return ModelDeploymentStatus.exited
