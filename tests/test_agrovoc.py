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

import json
from fastapi.testclient import TestClient

from starlette.status import (
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)


class TestKeywordsByLanguageAgrovoc:
    # TODO rückgabe sortiert?
    def test_get_keywords_en_agrovoc(self, testclient: TestClient):
        response = testclient.get("/agrovoc/keywords?language=en")

        assert response.status_code == HTTP_200_OK, "Error getting Keywords"
        # assert len(response.json()) == 51540, "Wrong amount of Keywords"

    def test_get_keywords_de_agrovoc(self, testclient: TestClient):
        response = testclient.get("/agrovoc/keywords?language=de")

        assert response.status_code == HTTP_200_OK, "Error getting Keywords"
        # assert len(response.json()) == 46036, "Wrong amount of Keywords"

    def test_get_keywords_check_if_sorted_agrovoc(self, testclient: TestClient):
        # Nicht unbedingt optimal, json.dump macht komische sachen mit der JSON länge
        response = testclient.get("/agrovoc/keywords?language=en")

        keywords = json.dumps(
            response.json(), separators=(",", ":"), ensure_ascii=False
        )

        manually_sorted_keywords = json.dumps(
            response.json(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

        assert response.status_code == HTTP_200_OK, "Error getting Keywords"
        assert keywords == manually_sorted_keywords, "Original keywords were not sorted"


class TestKeywordsCheckAgrovoc:
    def test_check_keywords_agrovoc(self, testclient: TestClient):
        response = testclient.get("/agrovoc/keywords/racoons/check")

        concept = response.json()["concept"]

        assert response.status_code == HTTP_200_OK, "Error checking Keywords"
        assert (
            concept == "http://aims.fao.org/aos/agrovoc/c_331202"
        ), "Wrong concept was returned"

    def test_check_wrong_keywords_agrovoc(self, testclient: TestClient):
        response = testclient.get("/agrovoc/keywords/wrongOne/check")

        concept = response.json()["concept"]

        assert response.status_code == HTTP_200_OK, "Error checking Keywords"
        assert concept == None, "Wrong concept was returned"


class TestGetLanguagesForKeywordAgrovoc:
    def test_get_languages_for_keyword(self, testclient: TestClient):
        response = testclient.get("/agrovoc/keywords/racoons/languages")

        assert response.status_code == HTTP_200_OK, "Error getting Languages"
        assert len(response.json()) >= 0, "Wrong amount of Languages"

    def test_get_languages_for_wrong_keyword(self, testclient: TestClient):

        response = testclient.get("/agrovoc/keywords/wrongOne/check")

        concept = response.json()["concept"]

        assert response.status_code == HTTP_200_OK, "Error checking Keywords"
        assert concept == None, "The Keyword should not exist"

        response = testclient.get("/agrovoc/keywords/wrongOne/languages")

        assert (
            response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        ), "Query should throw an error"


class TestGetBroaderAndNarrower:
    def test_get_broader_agrovoc(self, testclient: TestClient):
        response = testclient.get("/agrovoc/keywords/racoons/check")

        concept = response.json()["concept"]

        assert response.status_code == HTTP_200_OK, "Error checking Keywords"
        assert (
            concept == "http://aims.fao.org/aos/agrovoc/c_331202"
        ), "Wrong concept was returned"

        response = testclient.get("/agrovoc/keywords/racoons/languages/en/broader")

        assert response.status_code == HTTP_200_OK, "Error getting broader information"

        broader = response.json()
        assert broader == ["Coatis", "Procyonidae"], "Wrong information was returned"

    def test_get_broader_wrong_keyword_agrovoc(self, testclient: TestClient):
        response = testclient.get("/agrovoc/keywords/wrongOne/languages/en/broader")

        assert response.status_code == HTTP_200_OK, "Error getting broader information"

        broader = response.json()
        assert broader == []

    def test_get_broader_wrong_language_agrovoc(self, testclient: TestClient):
        response = testclient.get("/agrovoc/keywords/racoons/languages/xx/broader")

        assert response.status_code == HTTP_200_OK, "Error getting broader information"

        broader = response.json()
        assert broader == []

    def test_get_narrower_agrovoc(self, testclient: TestClient):
        response = testclient.get("/agrovoc/keywords/procyonidae/check")

        concept = response.json()["concept"]

        assert response.status_code == HTTP_200_OK, "Error checking Keywords"
        assert (
            concept == "http://aims.fao.org/aos/agrovoc/c_15609"
        ), "Wrong concept was returned"

        response = testclient.get("/agrovoc/keywords/Procyonidae/languages/en/narrower")

        assert response.status_code == HTTP_200_OK, "Error getting narrower information"
        print(response.json())
        narrower = response.json()
        assert narrower == [
            "Potos flavus",
            "Procyon",
            "kinkajous",
            "raccoons",
            "racoons",
        ], "Wrong information was returned"

    def test_get_narrower_wrong_keyword_agrovoc(self, testclient: TestClient):
        response = testclient.get("/agrovoc/keywords/wrongOne/languages/en/narrower")

        assert response.status_code == HTTP_200_OK, "Error getting narrower information"

        narrower = response.json()
        assert narrower == []

    def test_get_narrower_wrong_language_agrovoc(self, testclient: TestClient):
        response = testclient.get("/agrovoc/keywords/wrongOne/languages/xx/narrower")

        assert response.status_code == HTTP_200_OK, "Error getting narrower information"

        narrower = response.json()
        assert narrower == []

    def test_get_additional_agrovoc(self, testclient: TestClient):
        response = testclient.get("/agrovoc/keywords/procyonidae/check")

        concept = response.json()["concept"]

        assert response.status_code == HTTP_200_OK, "Error checking Keywords"
        assert (
            concept == "http://aims.fao.org/aos/agrovoc/c_15609"
        ), "Wrong concept was returned"

        response = testclient.get(
            "/agrovoc/keywords/procyonidae/languages/en/additional"
        )

        assert response.status_code == HTTP_200_OK, "Error getting narrower information"

        narrower = response.json()["narrower"]
        broader = response.json()["broader"]

        assert narrower == [
            "Potos flavus",
            "Procyon",
            "kinkajous",
            "raccoons",
            "racoons",
        ], "Wrong information was returned"

        assert broader[0] == "Carnivora", "Wrong information was returned"

    def test_get_additional_wrong_keyword_agrovoc(self, testclient: TestClient):
        response = testclient.get("/agrovoc/keywords/wrongOne/languages/en/additional")

        assert (
            response.status_code == HTTP_200_OK
        ), "Error getting additional information"

        assert response.json() == []

    def test_get_additional_wrong_language_agrovoc(self, testclient: TestClient):

        response = testclient.get("/agrovoc/keywords/racoons/languages/xx/additional")

        assert (
            response.status_code == HTTP_200_OK
        ), "Error getting additional information"

        narrower = response.json()["narrower"]
        broader = response.json()["broader"]

        assert broader == []
        assert narrower == []
