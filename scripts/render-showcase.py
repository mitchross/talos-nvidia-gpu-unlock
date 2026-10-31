#!/usr/bin/env python3
"""Render shareable graphics from preserved, sanitized measurements. Never query GPUs."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets/showcase"
OUT.mkdir(parents=True, exist_ok=True)
BENCH = json.loads((ROOT / "evidence/benchmarks.json").read_text())
GEMM = json.loads((ROOT / "evidence/gemm-same-card.json").read_text())
CASE = json.loads((ROOT / "evidence/verified-case.json").read_text())
BG, PANEL, TEXT, MUTED = "#0a101c", "#141f30", "#f0f5ff", "#acbcd2"
LIME, CYAN, ORANGE, GRAY = "#b8f453", "#58d4ee", "#ff9b55", "#8291a8"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
    "figure.facecolor": BG, "axes.facecolor": BG, "axes.edgecolor": "#344155",
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": TEXT, "svg.fonttype": "none", "svg.hashsalt": "talos-gpu-showcase"})


def frame(title, subtitle, height=8):
    fig = plt.figure(figsize=(16, height))
    fig.text(.05, .945, title, fontsize=27, weight="bold", va="top")
    fig.text(.05, .885, subtitle, fontsize=12, color=MUTED, va="top")
    return fig


def finish(fig, name, footer):
    fig.text(.05, .035, footer, fontsize=10, color=MUTED, va="bottom")
    fig.savefig(OUT / (name + ".png"), dpi=130, facecolor=BG)
    fig.savefig(OUT / (name + ".svg"), facecolor=BG, metadata={"Date": None})
    svg = OUT / (name + ".svg")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    plt.close(fig)


def card(ax, x, y, w, h, edge="#344155", fill=PANEL):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.02",
                              facecolor=fill, edgecolor=edge, linewidth=1.5))


def hero():
    fig = plt.figure(figsize=(16, 5.3))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set(xlim=(0, 1), ylim=(0, 1)); ax.axis("off")
    ax.text(.05, .90, "PROXMOX  +  TALOS LINUX", color=CYAN, fontsize=16, weight="bold")
    ax.text(.05, .73, "TWO RTX 3090s. UNLOCKED.", fontsize=33, weight="bold")
    ax.text(.05, .62, "Stock kernel. Early initramfs. Unchanged NVIDIA driver.", color=MUTED, fontsize=16)
    count = sum(g["verified_full_selectors"] for g in CASE["gpus"])
    bf16 = next(r for r in BENCH["same_card_bf16_8192"] if r["watts"] == 250)
    prefill = BENCH["qwen_unlock_comparison"]["prefill_gain_percent"][-1]
    values = [(f"{count} GPUs", "verified in the serving session", CYAN),
              (f"+{bf16['gain_percent']:.1f}%", "same-card BF16 · 8192 · 250 W", LIME),
              (f"+{prefill:.1f}%", "Qwen prefill · C4 · 200 W each", ORANGE)]
    for i, (value, label, color) in enumerate(values):
        x = .05 + i * .31; card(ax, x, .22, .285, .25)
        ax.text(x + .02, .36, value, fontsize=29, weight="bold", color=color)
        ax.text(x + .02, .265, label, fontsize=10.5, color=MUTED)
    ax.text(.05, .10, "GPU Unlock 2.0.0  /  Talos v1.14.5  /  Linux 6.18.58-talos  /  NVIDIA 595.91.07", color=MUTED, fontsize=11)
    finish(fig, "hero", "Measured on existing hardware. Fresh-install and unattended dual-GPU restart validation remain unfinished.")


def gemm(size):
    fig = frame(f"Tensor throughput · {size} × {size}",
                "Each card compared against itself. Stock vs unlocked at the same power cap.", 9)
    axes = fig.subplots(2, 3, gridspec_kw={"left": .075, "right": .97, "top": .79,
                                       "bottom": .16, "hspace": .52, "wspace": .28})
    for row, gpu in enumerate(["GPU A", "GPU B"]):
        for col, dtype in enumerate(["FP16", "BF16", "TF32"]):
            ax = axes[row, col]
            data = sorted([r for r in GEMM["comparisons"] if r["gpu"] == gpu and r["dtype"] == dtype and r["size"] == size], key=lambda r: r["watts_limit"])
            x = np.arange(2); width = .31
            before = [r["before_tflops"] for r in data]; after = [r["after_tflops"] for r in data]
            ax.bar(x-width/2, before, width, color=GRAY, label="Stock")
            ax.bar(x+width/2, after, width, color=LIME, label="Unlocked")
            ax.set_title(gpu + " / " + dtype, loc="left", fontsize=15, weight="bold", pad=10)
            ax.set_xticks(x, [str(r["watts_limit"]) + " W" for r in data])
            ax.set_ylim(0, max(after) * 1.32); ax.set_ylabel("TFLOPS")
            ax.spines[["top", "right"]].set_visible(False); ax.grid(axis="y", alpha=.12); ax.set_axisbelow(True)
            for i, r in enumerate(data):
                ax.text(x[i]-width/2, before[i]+1, f"{before[i]:.2f}", ha="center", fontsize=10, color=MUTED)
                ax.text(x[i]+width/2, after[i]+1, f"{after[i]:.2f}", ha="center", fontsize=10)
                ax.text(x[i], after[i]+max(after)*.16, f"+{r['gain_percent']:.1f}%", ha="center", color=LIME, fontsize=13, weight="bold")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(.5, .065), ncol=2,
               facecolor=BG, edgecolor=BG, labelcolor=TEXT)
    finish(fig, "gemm-" + str(size), "FP32 accumulation · CUDA events · median of 5 windows · driver 595.91.07 · temperatures differed across boots")


def qwen():
    fig = frame("Real Qwen inference · both GPUs unlocked",
                "Baseline: GPU A stock + GPU B unlocked. After: both unlocked. Same model, TP=2, 200 W per GPU.", 7)
    data = BENCH["qwen_unlock_comparison"]
    axes = fig.subplots(1, 3, gridspec_kw={"left": .07, "right": .97, "top": .74, "bottom": .23, "wspace": .25})
    series = [("Prefill", "prefill_gain_percent", ORANGE),
              ("Aggregate output throughput", "output_gain_percent", LIME),
              ("Decode", "decode_change_percent", GRAY)]
    for ax, (title, key, color) in zip(axes, series):
        values = data[key]; x = np.arange(3)
        ax.bar(x, values, .52, color=color)
        ax.axhline(0, color=MUTED, linewidth=1); ax.set_ylim(-5, 27)
        ax.set_xticks(x, ["C1", "C2", "C4"]); ax.set_ylabel("Change vs baseline (%)")
        ax.set_title(title, fontsize=14, loc="left", weight="bold", pad=14)
        ax.spines[["top", "right"]].set_visible(False); ax.grid(axis="y", alpha=.12); ax.set_axisbelow(True)
        for i, value in enumerate(values):
            ax.text(i, value+1.2 if value>=0 else value-2.2, f"{value:+.1f}%", ha="center", fontsize=16, weight="bold", color=color)
    fig.text(.07, .12, "Prefill benefits. Decode showed no demonstrated improvement.", fontsize=15, weight="bold")
    finish(fig, "qwen", "Qwen3.8-27B FP8 · vLLM · concurrency 1 / 2 / 4 · mixed-to-both comparison, not both-stock-to-both-unlocked")


def power():
    fig = frame("Power tradeoff · speed versus GPU energy",
                "Both GPUs unlocked throughout. Eight matched workloads; medians weighted equally across workloads.", 7.5)
    rows = BENCH["power_experiment"]["profiles"]; x = np.arange(len(rows))
    axes = fig.subplots(1, 2, gridspec_kw={"left": .08, "right": .97, "top": .75, "bottom": .25, "wspace": .28})
    for ax, field, scale, ylabel, color in [(axes[0], "output_tps", 1, "Output tokens / second", CYAN),
                                           (axes[1], "output_tokens_per_kwh", .001, "GPU-only output tokens / kWh (thousands)", LIME)]:
        values = [r[field]*scale for r in rows]
        ax.bar(x, values, .53, color=[color, "#6f8da3", "#52667f"] if field.endswith("kwh") else color)
        ax.set_xticks(x, [str(r["watts_per_gpu"]) + " W / GPU" for r in rows]); ax.set_ylim(0, max(values)*1.22)
        ax.set_ylabel(ylabel); ax.spines[["top", "right"]].set_visible(False); ax.grid(axis="y", alpha=.12); ax.set_axisbelow(True)
        for i, value in enumerate(values):ax.text(i, value+max(values)*.035, f"{value:.2f}" if scale==1 else f"{value:.1f}k", ha="center", fontsize=17, weight="bold")
    fig.text(.08, .145, "Actual combined load power:  387.4 W  /  431.8 W  /  472.8 W", fontsize=13, color=MUTED)
    fig.text(.08, .09, "200 W: energy default     ·     225 W: interactive alternative     ·     250 W: limited extra throughput", fontsize=13, weight="bold")
    finish(fig, "power", "Measured GPU-sensor energy only, not wall power · shortened sweep · mixed 5 / 3 repetitions · warmups and request gaps excluded")


def boot():
    fig = frame("The order that made Talos work",
                "GPU Unlock must complete before NVIDIA binds the selected GPU. The stock kernel is preserved.", 6.5)
    ax = fig.add_axes([.04, .13, .92, .65]); ax.set(xlim=(0, 1), ylim=(0, 1)); ax.axis("off")
    nodes = [("01", "Proxmox", "VFIO passthrough", ORANGE), ("02", "Talos kernel", "6.18.58-talos", CYAN),
             ("03", "Early init", "module + firmware", CYAN), ("04", "GPU Unlock", "fresh-success barrier", LIME),
             ("05", "machined", "then NVIDIA", CYAN), ("06", "vLLM", "both GPUs serving", LIME)]
    for i, (number, title, sub, color) in enumerate(nodes):
        x = .02 + i*.165; card(ax, x, .51, .125, .33, edge=color)
        ax.text(x+.012, .77, number, color=color, fontsize=12, weight="bold")
        ax.text(x+.012, .665, title, fontsize=13, weight="bold")
        ax.text(x+.012, .57, sub, fontsize=9, color=MUTED)
        if i<5:ax.add_patch(FancyArrowPatch((x+.136,.675),(x+.155,.675),arrowstyle="-|>",mutation_scale=10,color=MUTED,shrinkA=0,shrinkB=0))
    ax.annotate("", xy=(.578,.25), xytext=(.578,.49), arrowprops={"arrowstyle":"-|>", "color":ORANGE,"lw":1.6})
    card(ax, .42, .04, .51, .20, edge=ORANGE)
    ax.text(.44,.165,"Failure: stop early boot; retain serial evidence",fontsize=12,weight="bold",color=ORANGE)
    ax.text(.44,.085,"Manual recovery through the preserved stock boot image",fontsize=11,color=MUTED)
    ax.text(.01,.29,"EARLY firmware path",fontsize=12,weight="bold",color=CYAN)
    ax.text(.01,.20,"/usr/lib/firmware",fontsize=12,color=MUTED,family="monospace")
    ax.text(.01,.105,"Visible before NVIDIA starts",fontsize=11,color=MUTED)
    finish(fig, "boot-flow", "Tested in separate per-card boot transactions. Automatic dual-card cold / warm restart handling remains unvalidated.")


hero(); gemm(8192); gemm(4096); qwen(); power(); boot()
report = {"renderer": "scripts/render-showcase.py", "source_files": {}, "outputs": {},
          "new_gpu_measurements": False, "fresh_install_claimed": False,
          "note": "Hero metrics, charts, and boot flow use preserved evidence; GPU identities are sanitized."}
for path in [ROOT/"evidence/benchmarks.json", ROOT/"evidence/gemm-same-card.json", ROOT/"evidence/verified-case.json"]:
    report["source_files"][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
for path in sorted(OUT.glob("*")):
    if path.suffix in [".png", ".svg"]:report["outputs"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
(OUT/"validation.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps({"graphics": len(report["outputs"]), "output_directory": str(OUT.relative_to(ROOT))}))
