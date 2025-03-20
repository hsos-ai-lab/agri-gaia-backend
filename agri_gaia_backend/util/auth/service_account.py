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

import os

BACKEND_OPENID_CLIENT_ID = os.environ.get("BACKEND_OPENID_CLIENT_ID")
BACKEND_SERVICE_ACCOUNT_PASSWORD = os.environ.get("BACKEND_OPENID_CLIENT_SECRET")
BACKEND_SERVICE_ACCOUNT_USERNAME = f"service-account-{BACKEND_OPENID_CLIENT_ID}"

REALM_SERVICE_ACCOUNT_USERNAME = os.environ.get("REALM_SERVICE_ACCOUNT_USERNAME")
REALM_SERVICE_ACCOUNT_PASSWORD = os.environ.get("REALM_SERVICE_ACCOUNT_PASSWORD")
