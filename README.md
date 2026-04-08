# Image-to-3DCAD: VLMを用いた画像からのCADコード生成

技術図面画像からVision Language Model (VLM) を用いてbuild123d CADコードを生成し、正解データと比較評価するパイプラインです。

## 機能

- **ワンショットCAD生成**: VLMによる画像からのbuild123d CADコード生成（1-shot）
- **自動評価**: 生成STEPファイルと正解STEPファイルの幾何学的メトリクス比較（PCD, HDD, IoU, DSC）
- **トポロジメトリクス**: オイラー標数に基づく評価指標
- **バッチ処理**: paired形式データセットの一括処理とレポート生成
- **VLM統合**: Vertex AI経由でGeminiモデルを活用
- **ローカルキャッシュ**: VLMレスポンスをキャッシュしAPI呼び出しを削減

## アーキテクチャ

DDD（ドメイン駆動設計）に基づくクリーンアーキテクチャ：

```
src/
├── domain/                    # ドメイン層（ビジネスロジック）
│   ├── value_objects/         # 値オブジェクト（CadCode, MultiviewImage等）
│   ├── services/              # ドメインサービスインターフェース
│   └── repositories/          # リポジトリインターフェース
│
├── application/               # アプリケーション層
│   ├── workflow/              # LangGraphワークフロー
│   │   ├── nodes/             # ワークフローノード
│   │   ├── graph_builder.py   # グラフ構築
│   │   └── workflow_state.py  # 状態定義
│   ├── use_cases/             # ユースケース
│   ├── services/              # レポート生成
│   └── dto/                   # データ転送オブジェクト
│
├── infrastructure/            # インフラストラクチャ層
│   ├── llm/                   # VLM統合（google-genai + Vertex AI）
│   ├── cad/                   # CADレンダリング（build123d）
│   ├── repositories/          # リポジトリ実装
│   └── services/              # サービス実装
│
└── presentation/              # プレゼンテーション層
    └── cli/                   # CLIエントリポイント
```

## セットアップ

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. 環境設定

`.env`ファイルを作成：

```bash
# Google Cloudプロジェクト
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=global

# Vertex AIモデル
VERTEX_AI_MODEL_NAME=gemini-3.1-flash-lite-preview
```

### 3. Google Cloud認証

```bash
gcloud auth application-default login
```

### 4. テスト実行

```bash
uv run pytest tests/ -v
```

## 使用方法

### パイプライン実行

`paired`形式のデータセットに対して、画像からCAD生成→正解データとの評価→レポート生成を一括実行：

```bash
# 基本的な使用方法
uv run python -m presentation.cli.main pipeline \
    --input data/paired \
    --output-dir data/output/pipeline_results

# 最初の10件のみ処理
uv run python -m presentation.cli.main pipeline \
    --input data/paired \
    --limit 10 \
    --output-dir data/output/pipeline_results

# 既存の出力も再処理する場合
uv run python -m presentation.cli.main pipeline \
    --input data/paired \
    --output-dir data/output/pipeline_results \
    --no-skip-existing
```

**オプション：**
- `--input, -i`: 入力ディレクトリ（paired形式、必須）
- `--output-dir, -o`: 出力ディレクトリ（デフォルト: `data/output/pipeline_{timestamp}`）
- `--limit, -l`: 処理するモデル数の上限
- `--no-skip-existing`: 既存出力があっても再処理する
- `--model`: VLMモデル名（デフォルト: 環境変数VERTEX_AI_MODEL_NAME）

### 入力ディレクトリ形式（paired）

```
input_dir/
├── images/
│   ├── model_a.jpg
│   ├── model_b.png
│   └── ...
└── step/
    ├── model_a.step  (または .stp)
    ├── model_b.step
    └── ...
```

### 出力

```
output_dir/
├── {model_name}/           # 各モデルの出力
│   ├── {model_name}.step   # 生成されたSTEPファイル
│   ├── {model_name}.py     # 生成されたCADコード
│   └── result.json         # 個別結果（メトリクス含む）
├── report.md               # Markdownレポート
└── pipeline_result.json    # JSONレポート
```

### 評価メトリクス

| メトリクス | 説明 | 方向 |
|-----------|------|------|
| PCD | Point Cloud Distance（点群距離） | ↓ 低いほど良い |
| HDD | Hausdorff Distance（ハウスドルフ距離） | ↓ 低いほど良い |
| IoU | Intersection over Union | ↑ 高いほど良い |
| DSC | Dice Similarity Coefficient | ↑ 高いほど良い |
| Topology Error | オイラー標数の差 | ↓ 低いほど良い |

### 比較レポート生成

複数手法の結果を比較するレポートを生成：

```bash
uv run python scripts/generate_comparison_report.py
```

## 処理フロー

```
入力画像 → VLM（CADコード生成） → build123d（STEP出力） → 正解データと評価
```

1. **入力**: paired形式のデータセット（画像 + 正解STEPファイル）
2. **生成**: VLMが画像からbuild123d CADコードを1-shot生成
3. **レンダリング**: build123dでCADコードを実行しSTEPファイルを出力
4. **評価**: 生成STEPと正解STEPの幾何学的メトリクスを計算
5. **レポート**: 全結果をMarkdown/JSONレポートとして出力

## サンプルデータ

`data/sample/` にNIST MBE PMIプロジェクトのテストケースを同梱しています。

```bash
# サンプルデータで動作確認
uv run python -m presentation.cli.main pipeline \
    --input data/sample \
    --output-dir data/output/sample_results
```

## ライセンス

### サンプルデータ（data/sample/）

`data/sample/` に含まれるCADモデルおよびSTEPファイルは、[NIST MBE PMI Validation and Conformance Testing](https://www.nist.gov/ctl/smart-connected-systems-division/smart-connected-manufacturing-systems-group/mbe-pmi-validation) プロジェクトから取得したものです。

これらのファイルは米国連邦政府機関（NIST）が作成したものであり、[Title 17 U.S.C. Section 105](https://www.govinfo.gov/content/pkg/USCODE-2021-title17/html/USCODE-2021-title17-chap1-sec105.htm) に基づき米国内において著作権の対象外（パブリックドメイン）です。
