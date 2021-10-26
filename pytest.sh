#!/usr/bin/env bash

rm -rf mmiab-test.db
pytest -s --cov-config .coveragerc --cov monolith monolith/classes/tests
