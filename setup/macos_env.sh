#!/bin/bash
ENV="ifx_gui"
PKG_LIST=(pyyaml pyserial boto3 tk bottleneck opencv numpy fastavro matplotlib)
echo creating macos ${ENV} environment
conda env remove --name ${ENV}
conda create --name ${ENV} ${PKG_LIST[@]} python=3.7
