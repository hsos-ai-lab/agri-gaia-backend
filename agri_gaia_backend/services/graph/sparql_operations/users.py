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

import os

from rdflib.namespace import RDF, DCTERMS
from rdflib import Namespace
from rdflib import Graph
from rdflib import Literal, URIRef

from . import util

import logging

FUSEKI_ENDPOINT = os.environ.get("FUSEKI_ENDPOINT")
SPARQL_UPDATE_ENDPOINT = f"{FUSEKI_ENDPOINT}ds/update"
SPARQL_QUERY_ENDPOINT = f"{FUSEKI_ENDPOINT}ds/sparql"

logger = logging.getLogger("api-logger")


def query_for_username(username):
    query = f"""SELECT ?iri WHERE {{
            ?iri a <http://w3id.org/gaia-x/participant#Participant> .
            ?iri <https://w3id.org/idsa/core/name> {username} .
        }}"""

    return util.send_query(SPARQL_QUERY_ENDPOINT, query)


def delete_user(username):
    query = f"""
        DELETE{{  ?id ?p ?o }}
            WHERE{{   
                {{
                    FILTER (?id = {username})
                    ?id ?p ?o
                }}                
            }}"""

    return util.send_update(SPARQL_UPDATE_ENDPOINT, query)


def get_default_graph(username):
    graph = Graph()
    gaiax_participant = Namespace("http://w3id.org/gaia-x/participant#")

    graph.bind("gaiax_participant", gaiax_participant)
    graph.bind("dct", DCTERMS)
    graph.add((URIRef(username), gaiax_participant.name, Literal(username)))
    graph.add((URIRef(username), RDF.type, gaiax_participant.Participant))
    return graph
