#!/bin/env bash

python3 -m piper.train.export_onnx \
  --checkpoint ./lightning_logs/version_5/checkpoints/epoch=10246-val_mel=0.0983.ckpt \
  --output-file ./morpheus/morpheus-medium.onnx