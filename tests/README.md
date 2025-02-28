<!--
SPDX-FileCopyrightText: 2024 University of Applied Sciences Osnabrück
SPDX-FileContributor: Andreas Schliebitz
SPDX-FileContributor: Henri Graf
SPDX-FileContributor: Jonas Tüpker
SPDX-FileContributor: Lukas Hesse
SPDX-FileContributor: Maik Fruhner
SPDX-FileContributor: Prof. Dr.-Ing. Heiko Tapken
SPDX-FileContributor: Tobias Wamhof

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Testing Guide

This readme contains an overview of the overall structure of the testing suite. In this testing suite `pytest` is used as the core testing framework. This readme also contains information on how `pytest` is used in this testing suide and provides some supplementary information where the official docs are not intuitive.

## Basic resources

Pytest docs: https://docs.pytest.org/en/7.1.x/

Official FastAPI Documentation for Testing: https://fastapi.tiangolo.com/tutorial/testing/

Nice guide for the basics if testing FastAPI with pytest: https://www.jeffastor.com/blog/testing-fastapi-endpoints-with-docker-and-pytest

## Concept of testing fixtures

Pytest does not use the basic XUnit pattern with the setup/teardown methods but uses a fixture concept instead. Fixtures provide a modular way to setup a testing environment.

Wikipedia: https://en.wikipedia.org/wiki/Test_fixture

Pytest Docs: https://docs.pytest.org/en/7.1.x/explanation/fixtures.html#about-fixtures

Setup and Teardown with a fixture concept: https://stackoverflow.com/questions/26405380/how-do-i-correctly-setup-and-teardown-for-my-pytest-class-with-tests

## Basic structures of fixtures in this testsuite

- A session-scoped fixture is used to create and delete a testuser for the whole session.
- For each test a new backend app is created. That means that the tested backend app is actually not the one that is currently running in the backend container as the init process.
- For each test a new database session is created
- For each test a new testclient is created. There are 3 Testclients:
  - An unauthenticated testclient
  - A testclient that is authenticated with the credentials from the testuser
  - A testclient that automatically deletes the resources that are created with the post methods using the resources delete endpoint

## Warnings

In this testing suite [warnings](https://docs.pytest.org/en/stable/how-to/capture-warnings.html) are used to report errors that occur during test cleanup. In this case a UserWarning beginning with "CleanupError" in the message string is issued.
To disable this warning for specific tests e.g. because the deletion of a resource shall be tested (in this case the cleanup will throw an error because it can't find the resource) it can be disable on test level using the decorator `@pytest.mark.filterwarnings("ignore:CleanupError")`. See dataset delete test for an example.
