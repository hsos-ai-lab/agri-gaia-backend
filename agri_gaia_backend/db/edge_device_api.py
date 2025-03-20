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

from typing import List
from sqlalchemy.orm import Session

from agri_gaia_backend.db.models import EdgeDevice
from agri_gaia_backend.schemas import edge_device as schemas


def get_edge_device(db: Session, edge_device_id: int) -> EdgeDevice:
    return db.query(EdgeDevice).filter(EdgeDevice.id == edge_device_id).first()


def get_edge_devices(db: Session, skip: int = 0, limit: int = 100) -> List[EdgeDevice]:
    return db.query(EdgeDevice).offset(skip).limit(limit).all()


def create_edge_device(
    db: Session,
    name: str,
    edge_key: str,
    portainer_id: int,
) -> EdgeDevice:
    db_edge_device = EdgeDevice(name=name, edge_key=edge_key, portainer_id=portainer_id)
    db.add(db_edge_device)
    db.commit()
    db.refresh(db_edge_device)
    return db_edge_device


def update_edge_device(db: Session, edge_device: EdgeDevice) -> EdgeDevice:
    db.add(edge_device)
    db.commit()
    db.refresh(edge_device)
    return edge_device


def delete_edge_device(db: Session, edge_device: EdgeDevice) -> bool:
    db.delete(edge_device)
    db.commit()
    return True
