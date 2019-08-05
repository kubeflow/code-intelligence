#!/bin/bash

pip install -U pytest

pushd tests > /dev/null
    pytest
popd
