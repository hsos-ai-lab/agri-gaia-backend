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

import logging
from typing import Set

from agri_gaia_backend.schemas.agrovoc_keyword import (
    AgrovocKeyword,
    AgrovocKeywordWithLanguage,
)
from agri_gaia_backend.services.graph.sparql_operations import util as sparql_util
from fastapi import APIRouter

ROOT_PATH = "/agrovoc"

logger = logging.getLogger("api-logger")
router = APIRouter(prefix=ROOT_PATH)

predef_datatypes = {
    "http://www.w3.org/2001/XMLSchema#integer": "integer",
    "http://www.w3.org/2001/XMLSchema#string": "string",
    "http://www.w3.org/2001/XMLSchema#anyType": "string",
    "http://www.w3.org/2001/XMLSchema#boolean": "boolean",
    "http://w3id.org/agri-gaia-x/asset#ApiPath": "string",
    "http://www.w3.org/2001/XMLSchema#anyUri": "string",
}


@router.get("/keywords/{keyword}/languages")
def get_languages_for_keyword(keyword: str):
    languages, language = sparql_util.get_possible_languages_for_keyword(keyword)
    sorted_languages = sorted(languages)
    sorted_languages.remove(language)
    sorted_languages.insert(0, language)

    return sorted_languages


@router.get("/keywords")
def get_agrovoc_keywords_for_language(language: str):
    return sorted(sparql_util.get_possible_keywords(language))


@router.get("/keywords/{keyword}/check")
def check_keyword(keyword: str):
    concept, uri = sparql_util.check_keyword(keyword)
    return {"name": keyword, "concept": concept}


@router.get("/keywords/{keyword}/languages/{language}/broader")
def get_broader_concepts_for_keyword(keyword: str, language: str):
    concept, uri = sparql_util.check_keyword(keyword)
    if concept is None:
        return []

    return sorted(sparql_util.get_additional_information(concept, language, "broader"))


@router.get("/keywords/{keyword}/languages/{language}/narrower")
def get_narrower_concepts_for_keyword(keyword: str, language: str):
    concept, uri = sparql_util.check_keyword(keyword)
    if concept is None:
        return []

    return sorted(sparql_util.get_additional_information(concept, language, "narrower"))


@router.get("/keywords/{keyword}/languages/{language}/additional")
def get_additional_information_on_concept(keyword: str, language: str):
    concept, uri = sparql_util.check_keyword(keyword)
    if concept is None:
        return []

    broader = sorted(
        sparql_util.get_additional_information(concept, language, "broader")
    )
    narrower = sorted(
        sparql_util.get_additional_information(concept, language, "narrower")
    )

    return {"broader": broader, "narrower": narrower}


# TODO: Move outside of this router
@router.get("/classes")
def get_all_classes():
    result = sparql_util.query_possible_data_ressource_labels()
    return result


# TODO: Move outside of this router
@router.get("/classes/{class_name}")
def get_attributes_for_class(class_name: str):
    result = sparql_util.query_attributes_for_class(class_name)
    attributes = result["results"]["bindings"]
    return _create_json_schema(class_name, attributes=attributes)


# TODO: Move outside of this router
def _create_json_schema(classname: str, attributes):
    schema = dict()

    schema["description"] = f"A JSON Schema for the {classname}."
    schema["type"] = "object"
    schema["properties"] = dict()

    for attribute in attributes:
        if attribute["range"]["value"] in predef_datatypes:
            print(attribute)
            # TODO: keep label AND prop
            propId = (
                attribute["prop"]["value"]
                .replace("<", "")
                .replace(">", "")
                .split("#")[1]
            )
            schema["properties"][propId] = {
                "type": predef_datatypes[attribute["range"]["value"]]
            }
    return schema
