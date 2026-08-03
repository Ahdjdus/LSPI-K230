

# Introduction

This repository contains notes and records from my study of the Lichuang Lu Shan Series.

# Contributing

If you have any questions or encounter bugs while using this project, feel free to open an issue (provided no similar issue already exists).
If you have any innovative ideas or feature suggestions, you are welcome to contribute to the repository by submitting Pull Requests.

# Changelog

2025/4/7

- `to_onnx.py` converts PyTorch (pt) models to ONNX format and supports customization. See the script source code for details. Example: `python .\tools\to_onnx.py`

- `to_kmodel.py` is a script to convert ONNX models to K230-compatible kmodel format and generate test files. Example: `python .\tools\to_kmodel.py --target cpu --model .\yolo11n-obb.onnx --dataset_path .\images\obb-dota\ --input_width 1024 --input_height 1024 --ptq_option 0`

- `onnx_simu.py` determines the validity of the kmodel by calculating the cosine similarity ratio between the outputs of the ONNX and kmodel models. Example: `python .\tools\onnx_simu.py --model .\yolo11n-obb.onnx --model_input .\tmp\test_onnx_input.bin --kmodel .\yolo11n-obb.kmodel --kmodel_input .\tmp\test_kmodel_input.bin`

Note: `onnx_simu.py` only works when the kmodel is generated with `--target cpu`, as it requires PC-based testing. For K230 deployment, ensure `--target k230` is specified.
