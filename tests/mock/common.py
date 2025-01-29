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

import re
from collections import OrderedDict


class MockRequestsMethod:
    def __init__(self):
        self.responses = OrderedDict()

    def add_response(self, regex: str, response):
        self.responses[regex] = response

    def __call__(self, *args, **kwargs):
        url = args[0] if len(args) > 0 else kwargs["url"]
        for regex, response in self.responses.items():
            if re.match(regex, url):
                if isinstance(response, MockResponse):
                    return response
                else:
                    return response(*args, **kwargs)
        raise NotImplementedError(f"Mock method not implemented for this url: '{url}'")


class MockResponse:
    pass


class SuccessfulMockResponse(MockResponse):
    def __init__(self, status_code: int = 200):
        self.ok = True
        self.status_code = status_code

    def raise_for_status(self):
        pass
