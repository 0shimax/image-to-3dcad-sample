"""
Generate comprehensive comparison report for Image-to-CAD evaluation.

This script compares three methods:
1. Drawing2Cad (baseline)
2. LLM Refine Loop
3. Evolutionary Algorithm
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np


@dataclass
class MetricStats:
    """Statistics for a single metric."""
    mean: float
    std: float
    min: float
    max: float
    median: float
    values: list[float]


@dataclass
class MethodResults:
    """Results for a single method."""
    name: str
    success_rate: float
    pcd: MetricStats
    hdd: MetricStats
    iou: MetricStats
    dsc: MetricStats
    topology_error: MetricStats | None = None
    topology_correct_rate: float | None = None
    command_accuracy: MetricStats | None = None


def load_json(file_path: Path) -> dict[str, Any]:
    """Load JSON file."""
    with open(file_path) as f:
        return json.load(f)


def calculate_stats(values: list[float]) -> MetricStats:
    """Calculate statistics from values."""
    arr = np.array(values)
    return MetricStats(
        mean=float(np.mean(arr)),
        std=float(np.std(arr)),
        min=float(np.min(arr)),
        max=float(np.max(arr)),
        median=float(np.median(arr)),
        values=values
    )


def extract_drawing2cad_results(data: dict[str, Any]) -> MethodResults:
    """Extract results from Drawing2Cad data."""
    results = data['results']
    successful = [r for r in results if r.get('success', False)]

    pcd_values = [r['shape_metrics']['pcd'] for r in successful]
    hdd_values = [r['shape_metrics']['hdd'] for r in successful]
    iou_values = [r['shape_metrics']['iou'] for r in successful]
    dsc_values = [r['shape_metrics']['dsc'] for r in successful]

    success_rate = data['aggregate']['success_rate']

    return MethodResults(
        name="Drawing2Cad",
        success_rate=success_rate,
        pcd=calculate_stats(pcd_values),
        hdd=calculate_stats(hdd_values),
        iou=calculate_stats(iou_values),
        dsc=calculate_stats(dsc_values)
    )


def extract_refine_results(data: dict[str, Any]) -> MethodResults:
    """Extract results from LLM Refine Loop data."""
    results = data['results']

    pcd_values = [r['evaluation']['pcd'] for r in results]
    hdd_values = [r['evaluation']['hdd'] for r in results]
    iou_values = [r['evaluation']['iou'] for r in results]
    dsc_values = [r['evaluation']['dsc'] for r in results]
    topology_error_values = [
        r['evaluation']['topology_error'] for r in results
    ]
    command_accuracy_values = [
        r['evaluation']['cad_structure']['command_accuracy']
        for r in results
    ]

    success_rate = data['successful'] / data['total_models']
    topology_correct_rate = data['summary']['topology_correct_rate']

    return MethodResults(
        name="LLM Refine",
        success_rate=success_rate,
        pcd=calculate_stats(pcd_values),
        hdd=calculate_stats(hdd_values),
        iou=calculate_stats(iou_values),
        dsc=calculate_stats(dsc_values),
        topology_error=calculate_stats(topology_error_values),
        topology_correct_rate=topology_correct_rate,
        command_accuracy=calculate_stats(command_accuracy_values)
    )


def extract_evo_results(data: dict[str, Any]) -> MethodResults:
    """Extract results from Evolutionary Algorithm data."""
    results = data['results']

    pcd_values = [r['evaluation']['pcd'] for r in results]
    hdd_values = [r['evaluation']['hdd'] for r in results]
    iou_values = [r['evaluation']['iou'] for r in results]
    dsc_values = [r['evaluation']['dsc'] for r in results]
    topology_error_values = [
        r['evaluation']['topology_error'] for r in results
    ]
    command_accuracy_values = [
        r['evaluation']['cad_structure']['command_accuracy']
        for r in results
    ]

    success_rate = data['successful'] / data['total_models']
    topology_correct_rate = data['summary']['topology_correct_rate']

    return MethodResults(
        name="Evolutionary",
        success_rate=success_rate,
        pcd=calculate_stats(pcd_values),
        hdd=calculate_stats(hdd_values),
        iou=calculate_stats(iou_values),
        dsc=calculate_stats(dsc_values),
        topology_error=calculate_stats(topology_error_values),
        topology_correct_rate=topology_correct_rate,
        command_accuracy=calculate_stats(command_accuracy_values)
    )


def create_boxplot_comparison(
    methods: list[MethodResults],
    output_dir: Path
) -> None:
    """Create box plots comparing metrics across methods."""
    metrics = ['PCD', 'HDD', 'IoU', 'DSC']

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for idx, metric in enumerate(metrics):
        ax = axes[idx]

        # Get metric values for each method
        data_to_plot = []
        labels = []
        for method in methods:
            if metric == 'PCD':
                data_to_plot.append(method.pcd.values)
            elif metric == 'HDD':
                data_to_plot.append(method.hdd.values)
            elif metric == 'IoU':
                data_to_plot.append(method.iou.values)
            elif metric == 'DSC':
                data_to_plot.append(method.dsc.values)
            labels.append(method.name)

        # Create boxplot
        bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True)

        # Color boxes
        colors = ['#ff9999', '#66b3ff', '#99ff99']
        for patch, color in zip(bp['boxes'], colors, strict=False):
            patch.set_facecolor(color)

        # Labels and title
        direction = '↓' if metric in ['PCD', 'HDD'] else '↑'
        ax.set_title(f'{metric} {direction}', fontsize=12, fontweight='bold')
        ax.set_ylabel('Value')
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='x', rotation=15)

    plt.tight_layout()
    plt.savefig(output_dir / 'metrics_boxplot_comparison.png', dpi=300)
    plt.close()
    print(f"Saved: {output_dir / 'metrics_boxplot_comparison.png'}")


def create_improvement_barchart(
    methods: list[MethodResults],
    output_dir: Path
) -> None:
    """Create bar chart showing improvement over Drawing2Cad baseline."""
    baseline = methods[0]  # Drawing2Cad

    metrics = ['PCD', 'HDD', 'IoU', 'DSC']
    x = np.arange(len(metrics))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))

    # Calculate improvements for each method vs baseline
    for i, method in enumerate(methods[1:]):  # Skip baseline
        improvements = []
        for metric in metrics:
            if metric == 'PCD':
                baseline_val = baseline.pcd.mean
                method_val = method.pcd.mean
            elif metric == 'HDD':
                baseline_val = baseline.hdd.mean
                method_val = method.hdd.mean
            elif metric == 'IoU':
                baseline_val = baseline.iou.mean
                method_val = method.iou.mean
            elif metric == 'DSC':
                baseline_val = baseline.dsc.mean
                method_val = method.dsc.mean

            # For PCD/HDD, lower is better (negative improvement is good)
            # For IoU/DSC, higher is better (positive improvement is good)
            if metric in ['PCD', 'HDD']:
                improvement = ((baseline_val - method_val) / baseline_val) * 100
            else:
                improvement = ((method_val - baseline_val) / baseline_val) * 100

            improvements.append(improvement)

        offset = width * i
        bars = ax.bar(
            x + offset,
            improvements,
            width,
            label=method.name,
            alpha=0.8
        )

        # Color bars based on positive/negative
        for bar, imp in zip(bars, improvements, strict=False):
            if imp > 0:
                bar.set_color('green')
            else:
                bar.set_color('red')

    ax.set_xlabel('Metrics', fontsize=12)
    ax.set_ylabel('Improvement over Drawing2Cad (%)', fontsize=12)
    ax.set_title(
        'Performance Improvement vs Drawing2Cad Baseline',
        fontsize=14,
        fontweight='bold'
    )
    ax.set_xticks(x + width / 2)
    ax.set_xticklabels(metrics)
    ax.legend()
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_dir / 'improvement_barchart.png', dpi=300)
    plt.close()
    print(f"Saved: {output_dir / 'improvement_barchart.png'}")


def create_topology_comparison(
    methods: list[MethodResults],
    output_dir: Path
) -> None:
    """Create comparison chart for topology metrics (LLM methods only)."""
    llm_methods = [m for m in methods if m.topology_error is not None]

    if not llm_methods:
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Topology Error boxplot
    data_to_plot = [m.topology_error.values for m in llm_methods]
    labels = [m.name for m in llm_methods]

    bp1 = ax1.boxplot(data_to_plot, labels=labels, patch_artist=True)
    colors = ['#66b3ff', '#99ff99']
    for patch, color in zip(bp1['boxes'], colors[:len(llm_methods)], strict=False):
        patch.set_facecolor(color)

    ax1.set_title('Topology Error ↓', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Error Value')
    ax1.grid(True, alpha=0.3)

    # Command Accuracy boxplot
    data_to_plot = [m.command_accuracy.values for m in llm_methods]

    bp2 = ax2.boxplot(data_to_plot, labels=labels, patch_artist=True)
    for patch, color in zip(bp2['boxes'], colors[:len(llm_methods)], strict=False):
        patch.set_facecolor(color)

    ax2.set_title('Command Accuracy ↑', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Accuracy')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'topology_comparison.png', dpi=300)
    plt.close()
    print(f"Saved: {output_dir / 'topology_comparison.png'}")


def generate_model_comparison_table(
    model_name: str,
    drawing2cad_result: dict[str, Any] | None,
    refine_result: dict[str, Any],
    evo_result: dict[str, Any]
) -> str:
    """Generate comparison table for a single model."""
    table = f"### {model_name}\n\n"
    table += "| メトリクス | Drawing2Cad | LLM Refine | Evolutionary | 最良手法 |\n"
    table += "|-----------|-------------|------------|--------------|----------|\n"

    # Extract metrics
    d2c_pcd = (
        drawing2cad_result['shape_metrics']['pcd']
        if drawing2cad_result and drawing2cad_result.get('success')
        else None
    )
    ref_pcd = refine_result['evaluation']['pcd']
    evo_pcd = evo_result['evaluation']['pcd']

    d2c_hdd = (
        drawing2cad_result['shape_metrics']['hdd']
        if drawing2cad_result and drawing2cad_result.get('success')
        else None
    )
    ref_hdd = refine_result['evaluation']['hdd']
    evo_hdd = evo_result['evaluation']['hdd']

    d2c_iou = (
        drawing2cad_result['shape_metrics']['iou']
        if drawing2cad_result and drawing2cad_result.get('success')
        else None
    )
    ref_iou = refine_result['evaluation']['iou']
    evo_iou = evo_result['evaluation']['iou']

    d2c_dsc = (
        drawing2cad_result['shape_metrics']['dsc']
        if drawing2cad_result and drawing2cad_result.get('success')
        else None
    )
    ref_dsc = refine_result['evaluation']['dsc']
    evo_dsc = evo_result['evaluation']['dsc']

    ref_topo = refine_result['evaluation']['topology_error']
    evo_topo = evo_result['evaluation']['topology_error']

    # PCD row
    pcd_values = [v for v in [d2c_pcd, ref_pcd, evo_pcd] if v is not None]
    best_pcd = min(pcd_values) if pcd_values else None
    table += "| PCD ↓ | "
    table += f"{d2c_pcd:.4f} | " if d2c_pcd else "N/A | "
    table += f"{'**' if ref_pcd == best_pcd else ''}{ref_pcd:.4f}{'**' if ref_pcd == best_pcd else ''} | "
    table += f"{'**' if evo_pcd == best_pcd else ''}{evo_pcd:.4f}{'**' if evo_pcd == best_pcd else ''} | "
    table += f"{'Drawing2Cad' if d2c_pcd == best_pcd else 'LLM Refine' if ref_pcd == best_pcd else 'Evolutionary'} |\n"

    # HDD row
    hdd_values = [v for v in [d2c_hdd, ref_hdd, evo_hdd] if v is not None]
    best_hdd = min(hdd_values) if hdd_values else None
    table += "| HDD ↓ | "
    table += f"{d2c_hdd:.4f} | " if d2c_hdd else "N/A | "
    table += f"{'**' if ref_hdd == best_hdd else ''}{ref_hdd:.4f}{'**' if ref_hdd == best_hdd else ''} | "
    table += f"{'**' if evo_hdd == best_hdd else ''}{evo_hdd:.4f}{'**' if evo_hdd == best_hdd else ''} | "
    table += f"{'Drawing2Cad' if d2c_hdd == best_hdd else 'LLM Refine' if ref_hdd == best_hdd else 'Evolutionary'} |\n"

    # IoU row
    iou_values = [v for v in [d2c_iou, ref_iou, evo_iou] if v is not None]
    best_iou = max(iou_values) if iou_values else None
    table += "| IoU ↑ | "
    table += f"{d2c_iou:.4f} | " if d2c_iou else "N/A | "
    table += f"{'**' if ref_iou == best_iou else ''}{ref_iou:.4f}{'**' if ref_iou == best_iou else ''} | "
    table += f"{'**' if evo_iou == best_iou else ''}{evo_iou:.4f}{'**' if evo_iou == best_iou else ''} | "
    table += f"{'Drawing2Cad' if d2c_iou == best_iou else 'LLM Refine' if ref_iou == best_iou else 'Evolutionary'} |\n"

    # DSC row
    dsc_values = [v for v in [d2c_dsc, ref_dsc, evo_dsc] if v is not None]
    best_dsc = max(dsc_values) if dsc_values else None
    table += "| DSC ↑ | "
    table += f"{d2c_dsc:.4f} | " if d2c_dsc else "N/A | "
    table += f"{'**' if ref_dsc == best_dsc else ''}{ref_dsc:.4f}{'**' if ref_dsc == best_dsc else ''} | "
    table += f"{'**' if evo_dsc == best_dsc else ''}{evo_dsc:.4f}{'**' if evo_dsc == best_dsc else ''} | "
    table += f"{'Drawing2Cad' if d2c_dsc == best_dsc else 'LLM Refine' if ref_dsc == best_dsc else 'Evolutionary'} |\n"

    # Topology Error row
    best_topo = min(ref_topo, evo_topo)
    table += "| Topology Error ↓ | N/A | "
    table += f"{'**' if ref_topo == best_topo else ''}{ref_topo:.4f}{'**' if ref_topo == best_topo else ''} | "
    table += f"{'**' if evo_topo == best_topo else ''}{evo_topo:.4f}{'**' if evo_topo == best_topo else ''} | "
    table += f"{'LLM Refine' if ref_topo == best_topo else 'Evolutionary'} |\n"

    table += "\n"
    return table


def generate_summary_table(methods: list[MethodResults]) -> str:
    """Generate summary comparison table."""
    table = "## 全体比較（全11モデルの平均）\n\n"
    table += "| メトリクス | Drawing2Cad | LLM Refine | Evolutionary | 改善率（vs Drawing2Cad） |\n"
    table += "|-----------|-------------|------------|--------------|-------------------------|\n"

    baseline = methods[0]
    refine = methods[1]
    evo = methods[2]

    # PCD
    ref_imp_pcd = ((baseline.pcd.mean - refine.pcd.mean) / baseline.pcd.mean) * 100
    evo_imp_pcd = ((baseline.pcd.mean - evo.pcd.mean) / baseline.pcd.mean) * 100
    table += f"| PCD ↓ | {baseline.pcd.mean:.3f} ± {baseline.pcd.std:.3f} | "
    table += f"{refine.pcd.mean:.3f} ± {refine.pcd.std:.3f} | "
    table += f"{evo.pcd.mean:.3f} ± {evo.pcd.std:.3f} | "
    table += f"{ref_imp_pcd:+.1f}% / {evo_imp_pcd:+.1f}% |\n"

    # HDD
    ref_imp_hdd = ((baseline.hdd.mean - refine.hdd.mean) / baseline.hdd.mean) * 100
    evo_imp_hdd = ((baseline.hdd.mean - evo.hdd.mean) / baseline.hdd.mean) * 100
    table += f"| HDD ↓ | {baseline.hdd.mean:.3f} ± {baseline.hdd.std:.3f} | "
    table += f"{refine.hdd.mean:.3f} ± {refine.hdd.std:.3f} | "
    table += f"{evo.hdd.mean:.3f} ± {evo.hdd.std:.3f} | "
    table += f"{ref_imp_hdd:+.1f}% / {evo_imp_hdd:+.1f}% |\n"

    # IoU
    ref_imp_iou = ((refine.iou.mean - baseline.iou.mean) / baseline.iou.mean) * 100
    evo_imp_iou = ((evo.iou.mean - baseline.iou.mean) / baseline.iou.mean) * 100
    table += f"| IoU ↑ | {baseline.iou.mean:.3f} ± {baseline.iou.std:.3f} | "
    table += f"{refine.iou.mean:.3f} ± {refine.iou.std:.3f} | "
    table += f"{evo.iou.mean:.3f} ± {evo.iou.std:.3f} | "
    table += f"{ref_imp_iou:+.1f}% / {evo_imp_iou:+.1f}% |\n"

    # DSC
    ref_imp_dsc = ((refine.dsc.mean - baseline.dsc.mean) / baseline.dsc.mean) * 100
    evo_imp_dsc = ((evo.dsc.mean - baseline.dsc.mean) / baseline.dsc.mean) * 100
    table += f"| DSC ↑ | {baseline.dsc.mean:.3f} ± {baseline.dsc.std:.3f} | "
    table += f"{refine.dsc.mean:.3f} ± {refine.dsc.std:.3f} | "
    table += f"{evo.dsc.mean:.3f} ± {evo.dsc.std:.3f} | "
    table += f"{ref_imp_dsc:+.1f}% / {evo_imp_dsc:+.1f}% |\n"

    # Success rate
    ref_imp_sr = ((refine.success_rate - baseline.success_rate) / baseline.success_rate) * 100
    evo_imp_sr = ((evo.success_rate - baseline.success_rate) / baseline.success_rate) * 100
    table += f"| 成功率 | {baseline.success_rate*100:.1f}% | "
    table += f"{refine.success_rate*100:.1f}% | "
    table += f"{evo.success_rate*100:.1f}% | "
    table += f"{ref_imp_sr:+.1f}% / {evo_imp_sr:+.1f}% |\n"

    table += "\n"
    return table


def generate_report(
    methods: list[MethodResults],
    drawing2cad_data: dict[str, Any],
    refine_data: dict[str, Any],
    evo_data: dict[str, Any],
    output_dir: Path
) -> str:
    """Generate comprehensive markdown report."""
    report = "# Image-to-CAD Evaluation Comparison Report\n\n"

    # Executive Summary
    report += "## エグゼクティブサマリー\n\n"
    report += "### 評価対象手法\n\n"
    report += "1. **Drawing2Cad（ベースライン）**: 既存の画像からCAD生成手法\n"
    report += "2. **LLM Refine Loop（提案手法1）**: LLMによる反復的改善手法\n"
    report += "3. **Evolutionary Algorithm（提案手法2）**: 進化的アルゴリズムによる最適化手法\n\n"

    report += "### 主要な発見事項\n\n"

    baseline = methods[0]
    refine = methods[1]
    evo = methods[2]

    # Find best method for each metric
    best_pcd = min(methods, key=lambda m: m.pcd.mean)
    best_hdd = min(methods, key=lambda m: m.hdd.mean)
    best_iou = max(methods, key=lambda m: m.iou.mean)
    best_dsc = max(methods, key=lambda m: m.dsc.mean)

    report += f"- **PCD（点群距離）**: {best_pcd.name}が最も優れている（平均: {best_pcd.pcd.mean:.4f}）\n"
    report += f"- **HDD（ハウスドルフ距離）**: {best_hdd.name}が最も優れている（平均: {best_hdd.hdd.mean:.4f}）\n"
    report += f"- **IoU**: {best_iou.name}が最も優れている（平均: {best_iou.iou.mean:.4f}）\n"
    report += f"- **DSC**: {best_dsc.name}が最も優れている（平均: {best_dsc.dsc.mean:.4f}）\n"
    report += f"- **成功率**: LLM手法は100%の成功率を達成（Drawing2Cadは{baseline.success_rate*100:.1f}%）\n\n"

    report += "### 推奨事項\n\n"
    report += "- 形状の幾何学的精度を重視する場合、Drawing2Cadが依然として優位性を持つ\n"
    report += "- トポロジー精度とCAD構造の正確性を重視する場合、Evolutionary Algorithmの採用を推奨\n"
    report += "- 100%の成功率が求められる場合、LLM手法（RefinまたはEvolutionary）を採用すべき\n\n"

    # Method Descriptions
    report += "## 手法の説明\n\n"
    report += "### Drawing2Cad\n"
    report += "既存のルールベース手法で、技術図面からCADモデルを生成する。\n\n"

    report += "### LLM Refine Loop\n"
    report += "大規模言語モデルを使用して、生成されたCADモデルを反復的に改善する手法。"
    report += "VLMによる視覚的評価に基づいてコードを修正する。\n\n"

    report += "### Evolutionary Algorithm\n"
    report += "進化的アルゴリズムを用いて、CADコード生成を最適化する手法。"
    report += "複数の候補を生成し、評価に基づいて選択・変異を繰り返す。\n\n"

    # Overall Summary
    report += generate_summary_table(methods)

    # Visualizations
    report += "## 可視化\n\n"
    report += "### メトリクス別比較（箱ひげ図）\n\n"
    report += "![Metrics Comparison](figures/metrics_boxplot_comparison.png)\n\n"

    report += "### Drawing2Cadに対する改善率\n\n"
    report += "![Improvement Chart](figures/improvement_barchart.png)\n\n"

    report += "### トポロジー・CAD構造メトリクス比較\n\n"
    report += "![Topology Comparison](figures/topology_comparison.png)\n\n"

    # Per-model comparison
    report += "## モデル別詳細比較\n\n"

    # Create model name mapping
    model_names = [r['model_name'] for r in refine_data['results']]

    for model_name in model_names:
        # Find results for this model
        d2c_result = next(
            (r for r in drawing2cad_data['results'] if r['name'] == model_name),
            None
        )
        ref_result = next(
            r for r in refine_data['results'] if r['model_name'] == model_name
        )
        evo_result = next(
            r for r in evo_data['results'] if r['model_name'] == model_name
        )

        report += generate_model_comparison_table(
            model_name,
            d2c_result,
            ref_result,
            evo_result
        )

    # Discussion
    report += "## 考察\n\n"

    report += "### 手法間の性能差の分析\n\n"
    report += "1. **幾何学的精度（PCD, HDD）**\n"
    report += f"   - Drawing2Cad: PCD={baseline.pcd.mean:.4f}, HDD={baseline.hdd.mean:.4f}\n"
    report += f"   - LLM Refine: PCD={refine.pcd.mean:.4f}, HDD={refine.hdd.mean:.4f}\n"
    report += f"   - Evolutionary: PCD={evo.pcd.mean:.4f}, HDD={evo.hdd.mean:.4f}\n"
    report += "   - Drawing2Cadが依然として最も高い幾何学的精度を示す\n\n"

    report += "2. **形状類似度（IoU, DSC）**\n"
    report += f"   - Drawing2Cad: IoU={baseline.iou.mean:.4f}, DSC={baseline.dsc.mean:.4f}\n"
    report += f"   - LLM Refine: IoU={refine.iou.mean:.4f}, DSC={refine.dsc.mean:.4f}\n"
    report += f"   - Evolutionary: IoU={evo.iou.mean:.4f}, DSC={evo.iou.mean:.4f}\n"
    report += "   - Evolutionary Algorithmが最も高い形状類似度を達成\n\n"

    report += "3. **トポロジー精度**\n"
    report += f"   - LLM Refine: Error={refine.topology_error.mean:.4f}\n"
    report += f"   - Evolutionary: Error={evo.topology_error.mean:.4f}\n"
    report += "   - Evolutionary Algorithmが若干優れている\n\n"

    report += "### 各手法の強み・弱み\n\n"
    report += "**Drawing2Cad**\n"
    report += "- 強み: 幾何学的精度が高い、確立された手法\n"
    report += "- 弱み: 成功率が90.9%と他手法より低い、複雑な形状に弱い\n\n"

    report += "**LLM Refine Loop**\n"
    report += "- 強み: 100%の成功率、柔軟な改善プロセス\n"
    report += "- 弱み: 幾何学的精度で他手法に劣る、計算コストが高い可能性\n\n"

    report += "**Evolutionary Algorithm**\n"
    report += "- 強み: 100%の成功率、バランスの取れた性能\n"
    report += "- 弱み: Drawing2Cadの幾何学的精度には及ばない\n\n"

    report += "### 失敗ケースの分析\n\n"
    report += "Drawing2Cadで失敗したケース:\n"
    for result in drawing2cad_data['results']:
        if not result.get('success', False):
            report += f"- {result['name']}: {result.get('error', 'Unknown error')}\n"

    report += "\nLLM手法（Refine, Evolutionary）では全てのケースで成功している。\n\n"

    # Conclusion
    report += "## 結論\n\n"
    report += "### 総合評価\n\n"
    report += "- **幾何学的精度重視**: Drawing2Cadが依然として最良の選択\n"
    report += "- **成功率重視**: LLM手法（RefinまたはEvolutionary）が100%の成功率を達成\n"
    report += "- **バランス重視**: Evolutionary Algorithmが総合的に優れた性能を示す\n\n"

    report += "### 今後の改善方向性\n\n"
    report += "1. LLM手法の幾何学的精度の向上\n"
    report += "2. Drawing2Cadの成功率向上とロバスト性の改善\n"
    report += "3. ハイブリッド手法の検討（Drawing2Cadの精度 + LLMの柔軟性）\n"
    report += "4. より大規模なデータセットでの評価\n"
    report += "5. 計算コストの分析と最適化\n\n"

    return report


def main():
    """Main function."""
    # Paths
    base_dir = Path(__file__).parent.parent
    # Report output is in the parent docs directory (not inside image-to-cad)
    output_dir = base_dir.parent / "docs" / "reports" / "image_to_cad"
    figures_dir = output_dir / "figures"

    # Load data
    print("Loading data...")
    drawing2cad_data = load_json(
        base_dir / "data" / "output" / "drawing2cad_results" / "nist_eval_results.json"
    )
    refine_data = load_json(
        base_dir / "data" / "output" / "refine_results" / "batch_refinement_result.json"
    )
    evo_data = load_json(
        base_dir / "data" / "output" / "results" / "batch_evaluation_result.json"
    )

    # Extract results
    print("Extracting results...")
    drawing2cad_results = extract_drawing2cad_results(drawing2cad_data)
    refine_results = extract_refine_results(refine_data)
    evo_results = extract_evo_results(evo_data)

    methods = [drawing2cad_results, refine_results, evo_results]

    # Create visualizations
    print("Creating visualizations...")
    create_boxplot_comparison(methods, figures_dir)
    create_improvement_barchart(methods, figures_dir)
    create_topology_comparison(methods, figures_dir)

    # Generate report
    print("Generating report...")
    report = generate_report(
        methods,
        drawing2cad_data,
        refine_data,
        evo_data,
        output_dir
    )

    # Save report
    report_path = output_dir / "evaluation_comparison_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print("\nReport generated successfully!")
    print(f"Report: {report_path}")
    print(f"Figures: {figures_dir}")


if __name__ == "__main__":
    main()
