# 简介
该仓库是本人在学习立创庐山派时记录下来的内容。

# 关于贡献
如果同仁在使用过程中有疑问或发现 bug 的、可直接提 issues（在历史中没有类似问题）
如果各位有什么新意的点子或功能可参与仓库的建设，进行 Pull requests

# 更新内容

2025/4/7

- `to_onnx.py` 是 pt 转 onnx 模型，支持定制，详情见脚本源码。例 `python .\tools\to_onnx.py`

- `to_kmodel.py` 是 onnx 模型转 k230 的 kmodel 模型以及生成测试文件的脚本。例 `python .\tools\to_kmodel.py --target cpu --model .\yolo11n-obb.onnx --dataset_path .\images\obb-dota\ --input_width 1024 --input_height 1024 --ptq_option 0`

- `onnx_simu.py` 通过 onnx 和 kmodel 输出的模型余弦的比值来判断 kmodel 是否可用。例 `python .\tools\onnx_simu.py --model .\yolo11n-obb.onnx --model_input .\tmp\test_onnx_input.bin --kmodel .\yolo11n-obb.kmodel --kmodel_input .\tmp\test_kmodel_input.bin`

注意：`onnx_simu.py` 只能在 kmodel 的 `--target cpu` 才有效，因为需要在 pc 端测试。部署到 k230 需要保证 `--target k230`

