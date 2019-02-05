# coding=utf-8
from tests import factories

import pytest


@pytest.fixture
def author():
    return factories.AuthorFactory()


@pytest.fixture
def book():
    return factories.BookFactory()
