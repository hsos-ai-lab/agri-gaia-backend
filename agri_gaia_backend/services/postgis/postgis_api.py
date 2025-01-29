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
from typing import Tuple

# need to import this here, so sqlalchemy can register it, dont remove!
from geoalchemy2 import Geometry
from geoalchemy2 import functions as func

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

from agri_gaia_backend.db.models import Fieldborder

POSTGIS_DB = os.environ.get("POSTGIS_DB")
POSTGIS_USER = os.environ.get("POSTGIS_USER")
POSTGIS_PASSWORD = os.environ.get("POSTGIS_PASSWORD")
CONN_STR = (
    f"postgresql://{POSTGIS_USER}:{POSTGIS_PASSWORD}@postgis_backend/{POSTGIS_DB}"
)


class PostGISAPI:
    def __init__(self) -> None:
        self.engine = create_engine(CONN_STR)

        self.meta = MetaData()
        self.meta.reflect(bind=self.engine)

        self.session = sessionmaker(bind=self.engine)()

    def get_fieldborders(
        self,
        north_west_lat_lng_bounds: Tuple[float, float],
        south_east_lat_lng_bounds: Tuple[float, float],
        limit: int = 1000,
    ):
        nw = north_west_lat_lng_bounds
        se = south_east_lat_lng_bounds
        bbox = f"POLYGON(({nw[1]} {nw[0]},{se[1]} {nw[0]},{se[1]} {se[0]},{nw[1]} {se[0]},{nw[1]} {nw[0]}))"
        print(bbox)
        return (
            self.session.query(Fieldborder)
            .where(Fieldborder.geom != None)
            .where(
                Fieldborder.geom.ST_WITHIN(
                    func.ST_Transform(func.ST_GeomFromText(bbox, 4326), 25832)
                )
            )
            .limit(limit)
            .all()
        )


postgis = PostGISAPI()
