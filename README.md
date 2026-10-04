# モデルベース開発 スターターキット

Pythonと生成AIを活用したモデルベース開発 (MBD: Model-Based Development)を始めるためのスターターキットです。

現時点ではまず、Python で設計した制御アルゴリズムを C++ へ移植し、両者の出力一致性を自動検証するためのフレームワークを用意しています。

## 概要

本フレームワークは次の開発フローを支援します。

1. **制御アルゴリズムの設計**: Python で制御ロジックを実装し、動作を素早く検証する
2. **C++ への移植**: 組み込みや高性能環境向けに同等ロジックを C++ で実装する
3. **SIL 検証**: Python 実装と C++ 実装を同一テストから呼び出し、出力の一致性を確認する

この SIL (Software-In-the-Loop) 検証により、C++ 移植の正確性をコード変更のたびに継続的に保証できます。

`SIL_Operator` は、Python ソースファイルを解析して対応する pybind11 C++ 拡張モジュールを自動生成・ビルドします。テストコードから Python 実装と C++ 実装の両方を呼び出し、出力の等価性を検証することで、C++ 移植の正確性を確認できます。

```
Python 実装 (.py)
    ↓  SIL_Operator.build_SIL_code()
C++ ラッパー (_SIL.cpp) + CMakeLists.txt を自動生成
    ↓  CMake / pybind11 でビルド
Python から import 可能な .so モジュール
    ↓  テストで双方の出力を比較
等価性の検証
```

## リポジトリ構成

```
.
├── source/
│   ├── my_func.py          # Python 実装（参照実装）
│   ├── my_func.hpp         # C++ 実装
│   └── my_func_SIL.cpp     # pybind11 ラッパー（手動または自動生成）
├── tests/
│   ├── SIL_operator.py     # SIL ビルドフレームワーク本体
│   ├── SIL_operator_exclude_paths.json  # ビルドから除外するパスの設定
│   └── my_func/
│       └── test.py         # 等価性テスト
└── docker/
    ├── Dockerfile
    ├── docker-compose.yml
    └── install_environment_for_docker.sh
```

## 主要コンポーネント

### `SIL_Operator` (tests/SIL_operator.py)

SIL コードのビルドを管理するメインクラスです。

```python
from SIL_operator import SIL_Operator

generator = SIL_Operator("my_func.py", current_dir)
generator.build_SIL_code(build_type="Debug")
```

| 引数 | 説明 |
|------|------|
| `target_python_file_name` | 対象の Python ファイル名（`.py` 付き） |
| `SIL_folder` | ビルド成果物の出力先ディレクトリ |

`build_SIL_code()` は以下を自動実行します：

1. Python ファイルを AST 解析してクラス・メソッドを抽出
2. `_SIL.cpp` が未存在の場合、pybind11 ラッパーを自動生成
3. `CMakeLists.txt` を生成（インクルードパス・ソースファイルを自動検出）
4. CMake でビルドし、`.so` モジュールをテストディレクトリに配置

### `CmakeGenerator`

プロジェクトのソースツリーを走査して `CMakeLists.txt` を生成します。`SIL_operator_exclude_paths.json` に記載されたパスパターン（デフォルトは `build/` 配下）を除外します。

### `PybindCppGenerator`

Python ファイルを解析し、クラスのメソッドに対応する pybind11 C++ スケルトンコードを生成します。ダンダーメソッド（`__init__` 等）はスキップされます。

### `PythonAnalyzer`

Python ソースファイルを AST で解析し、クラス定義とメソッド一覧を抽出します。

## テストの実行

```bash
cd /workspace
source /opt/venv_python/bin/activate
python tests/my_func/test_add.py
python tests/my_func/test_Calculator.py
```

各テストは Python 実装と C++ SIL 実装の出力をステップごとに比較し、不一致があれば `AssertionError` を送出します。

### 検証対象

| テストファイル | 検証内容 |
|---|---|
| `test_add.py` | `add(a, b)` — 加算関数の等価性 |
| `test_Calculator.py` | `Calculator.integrate()` / `reset()` — 積分器クラスの状態遷移とリセットの等価性 |

### `Calculator` SIL バインディング

`source/my_func_SIL.cpp` では `my_func::Calculator` を pybind11 クラスとして公開しています。Python 側と C++ 側のインスタンスを同一ステップ列で並走させ、`integrate()` の戻り値を逐次照合します。`reset()` 呼び出しも両インスタンスに同時適用し、状態リセット後の挙動も検証します。

## Docker 環境

```bash
cd docker
docker compose up -d
docker compose exec mbd_core_env_container bash
```

### 補足（VS Code 設定）

#### 1) `.vscode/c_cpp_properties.json` で Python 3.14 を使う場合

`.vscode/c_cpp_properties.json` の `includePath` にある Python 3.14 用の2行はコメントアウトされています。  
Python 3.14 側で IntelliSense を合わせる場合は、以下の 3.14 用2行をコメント解除してください（必要に応じて 3.12 用2行はコメントアウト）。

```jsonc
// "/usr/include/python3.14",
// "/opt/venv_python/lib/python3.14/site-packages/pybind11/include"
```

#### 2) WSL Ubuntu を使わず、`wslc` でコンテナを起動したい場合

VS Code の `settings.json`（ユーザー設定）で Docker コマンド設定を `wslc` に設定します。

```jsonc
// "dev.containers.dockerPath": "docker",
"dev.containers.dockerPath": "wslc",
```

設定変更後、コマンドパレットから **Reopen in Container** をクリックしてコンテナを再オープンしてください。

コンテナには以下が含まれます：

- Ubuntu 24.04 / 26.04
- Python 3.12 / 3.14（Ubuntu バージョンに依存）
- CMake、GCC、GDB、clang-format
- pybind11
- NumPy、SciPy、matplotlib、pytest、pandas、SymPy 等の科学技術計算ライブラリ

## 必要環境（ローカル）

- Ubuntu 24.04 以降
- Python 3.12 以降
- CMake 3.14 以降
- pybind11
- GCC（C++11 対応）

## exclude_paths の設定

`tests/SIL_operator_exclude_paths.json` でビルド対象から除外するパスパターンを指定できます。

```json
{
  "exclude_paths": [
    "build",
    "build/*",
    "*/build",
    "*/build/*"
  ]
}
```

ワイルドカード（`*`, `?`, `[]`）および前方一致によるディレクトリ除外をサポートしています。
