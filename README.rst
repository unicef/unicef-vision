UNICEF-Vision
=========


Installation
------------

.. code-block:: bash

    pip install unicef-vision


Setup
-----

Add ``unicef_vision`` to ``INSTALLED_APPS`` in settings

.. code-block:: bash

    INSTALLED_APPS = [
        ...
        'unicef_vision',
    ]


Usage
-----

TODO

Contributing
------------

Environment Setup
~~~~~~~~~~~~~~~~~

To install the necessary libraries

.. code-block:: bash

    $ make install


Coding Standards
~~~~~~~~~~~~~~~~

See `PEP 8 Style Guide for Python Code <https://www.python.org/dev/peps/pep-0008/>`_ for complete details on the coding standards.

To run checks on the code to ensure code is in compliance

.. code-block:: bash

    $ make lint


Testing
~~~~~~~

Testing is important and tests are located in `tests/` directory and can be run with;

.. code-block:: bash

    $ make test

Coverage report is viewable in `build/coverage` directory, and can be generated with;



Links
~~~~~

+--------------------+----------------+--------------+--------------------+
| Stable             | |master-build| | |master-cov| |                    |
+--------------------+----------------+--------------+--------------------+
| Development        | |dev-build|    | |dev-cov|    |                    |
+--------------------+----------------+--------------+--------------------+
| Source Code        |https://github.com/unicef/unicef-vision             |
+--------------------+----------------+-----------------------------------+
| Issue tracker      |https://github.com/unicef/unicef-vision/issues      |
+--------------------+----------------+-----------------------------------+


.. |master-build| image:: https://secure.travis-ci.org/unicef/unicef-vision.svg?branch=master
                    :target: http://travis-ci.org/unicef/unicef-vision/

.. |master-cov| image:: https://codecov.io/gh/unicef/unicef-vision/branch/master/graph/badge.svg
                    :target: https://codecov.io/gh/unicef/unicef-vision

.. |dev-build| image:: https://secure.travis-ci.org/unicef/unicef-vision.svg?branch=develop
                  :target: http://travis-ci.org/unicef/unicef-vision/

.. |dev-cov| image:: https://codecov.io/gh/unicef/unicef-vision/branch/develop/graph/badge.svg
                    :target: https://codecov.io/gh/unicef/unicef-vision



Compatibility Matrix
--------------------

Stable
~~~~~~

.. image:: https://travis-matrix-badges.herokuapp.com/repos/unicef/unicef-vision/branches/master


Develop
~~~~~~~

.. image:: https://travis-matrix-badges.herokuapp.com/repos/unicef/unicef-vision/branches/develop
