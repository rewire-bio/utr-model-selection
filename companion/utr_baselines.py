"""Compare cheap baselines, a small CNN and a frozen UTR-LM representation for
mean ribosome load (MRL) on the Sample et al. (2019) designed 5' UTR library.

The protocol is fixed in PROTOCOL.md (utr-mrl-designed-choice-v1). Commands:

    fetch     download pinned inputs and check SHA-256
    prepare   join data and metadata, build input tracks, splits and groups
    embed     frozen UTR-LM embeddings (CPU only)
    fit       fit one method on one split, save validation/test predictions
    evaluate  metrics, cluster-bootstrap intervals, examples, resource table
    run-all   every step in order, one subprocess per fitted method

Source datasets and model weights are downloaded at runtime and never bundled.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import platform
import resource
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

PROTOCOL_ID = "utr-mrl-designed-choice-v1"
LEADER = "GGGACATCGTAGAGAGTCGTACTTA"
INSERT = slice(25, 75)
SEQ_LEN = 855
UTRLM_COMMIT = "b77b589bf182eb9de6a1a5024fa09d44294d94fc"
UTRLM_RAW = f"https://raw.githubusercontent.com/a96123155/UTR-LM/{UTRLM_COMMIT}/"
UTRLM_CKPT = "ESM2_1.4_five_species_TrainLossMin_6layers_16heads_128embedsize_4096batchToks.pkl"

PINS = {
    "mrl-sample-designed.parquet": {
        "url": "https://huggingface.co/datasets/morrislab/mrl-sample/resolve/"
               "ef67f7cf8a999bb1c412ad6551aa7d9f901cbb95/mrl-sample-designed.parquet",
        "sha256": "8b8c57581d472e89a21f8b468b3b0599f6c235c01423264561e6c302d78927d4",
    },
    "GSM3130443_designed_library.csv.gz": {
        "url": "https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM3130nnn/GSM3130443/suppl/"
               "GSM3130443_designed_library.csv.gz",
        "sha256": "b72ac298cb0f4d21f911d330c0def06f8d94f15d9f8cc22f3a50ae87a7ef7ee5",
    },
    f"utrlm/{UTRLM_CKPT}": {
        "url": UTRLM_RAW + "Model/Pretrained/" + UTRLM_CKPT,
        "sha256": "2fc9b7b09a1167aa7fd4694df6a4a105d1939ae7099168bed3b061beb55917c0",
    },
}
UTRLM_CODE = {  # UTR-LM's modified ESM package (GPL-3.0), fetched at runtime, not redistributed
    "esm/__init__.py": "472f6fa6276a8b1c99d341a839cfd623d046f60feb789341c81730c674f4e068",
    "esm/axial_attention.py": "2b1433abe19a4821346f4715271dacfbea1435e95c6f2e335812e5af41087180",
    "esm/constants.py": "c1cf30243cd77ee38a45f81917259caf488c5938969a4ae6f3318544f187b3fd",
    "esm/data.py": "d28148d08ebad0652173166b0752ffc63289a2c979a878edb709ae0196d0f1a3",
    "esm/model/esm1.py": "725c4002f1ad731286057d9d2c05f53a8f216026d690ee477457985988337d6e",
    "esm/model/esm2.py": "bdb16d8949cafa708aa0b3b91ffdb2f199624d66ed426c7212f6afd83e8abae9",
    "esm/model/msa_transformer.py": "a7c03d20e3f94a049b5f53b5db95f5b9b1ef3762b151e61b2bee19f431a07328",
    "esm/modules.py": "52c0764374e53c2c0c0b03f53e2f0949a42613d55e5a912dd1072a91189a460f",
    "esm/multihead_attention.py": "a14601490c60f6b701b3659a02acc19a67723564d425a381b1d1096a30f6e131",
    "esm/pretrained.py": "79b6e3437985dec0a5cb79b78d63124074ba56a23262a70cc3344d8e6f618949",
    "esm/rotary_embedding.py": "8e39963efefcc64b9a8bd88c5ea210b5924b55dc64c215262067a16e0e0463c6",
    "esm/version.py": "f9d6749e95189819e770a161e5688617e3e573f28c1cc06b3c82e9cbb85b2440",
}
for _rel, _sha in UTRLM_CODE.items():
    PINS[f"utrlm/{_rel}"] = {"url": UTRLM_RAW + "Scripts/" + _rel, "sha256": _sha}

HISTORICAL_SPLIT_SHA256 = "00e287b18ba4e90cb682af6e3fcdfc97e07f2b4b25d13265cd0eca37996536a2"
GROUPED_SEED = 20260930
LINK_K = 20
GIANT_FRACTION = 0.01
ALPHAS = [1e-3, 1e-2, 0.1, 1.0, 10.0, 100.0, 1e3, 1e4]
REPLAY_ALPHAS = [0.001, 0.01, 0.1, 1.0, 10.0]
RIDGE_METHODS = ["comp_utr", "kmer_utr", "onehot_pos", "annot", "cheap_combined"]
FROZEN_METHODS = ["utrlm_mean_ridge", "utrlm_pos_ridge", "utrlm_cnn"]
CNN_METHODS = ["cnn", "utrlm_cnn"]
ALL_METHODS = ["train_mean", "comp_full_replay", *RIDGE_METHODS, "cnn", *FROZEN_METHODS]
SPLITS = ["historical", "grouped"]
SEEDS = [0, 1, 2]
BOOTSTRAPS = 2000
BOOT_SEED = 7
MSE_THRESHOLD = 0.10
PRECISION_THRESHOLD = 0.05
SMOKE_STRIDE = 20


# ----------------------------------------------------------------------------- utilities

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def peak_rss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / 1e6 if sys.platform == "darwin" else rss / 1e3  # bytes on macOS, KiB on Linux


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=_json_default) + "\n")


def _json_default(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    raise TypeError(type(x))


def hardware() -> dict:
    cpu = platform.processor()
    if sys.platform == "darwin":
        try:
            cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True,
                                 text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            pass
    import torch
    return {"platform": platform.platform(), "machine": platform.machine(), "cpu": cpu,
            "cpu_count": os.cpu_count(), "python": platform.python_version(),
            "torch": torch.__version__, "mps_available": bool(torch.backends.mps.is_available())}


# ----------------------------------------------------------------------------- fetch

def fetch(inputs: Path) -> dict:
    inputs.mkdir(parents=True, exist_ok=True)
    receipt = {}
    for rel, pin in PINS.items():
        out = inputs / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if not out.exists() or sha256_file(out) != pin["sha256"]:
            tmp = out.with_suffix(out.suffix + ".part")
            req = urllib.request.Request(pin["url"], headers={"User-Agent": "utr-baselines/0.1"})
            with urllib.request.urlopen(req, timeout=300) as resp, open(tmp, "wb") as fh:
                while chunk := resp.read(1 << 20):
                    fh.write(chunk)
            tmp.replace(out)
        digest = sha256_file(out)
        if digest != pin["sha256"]:
            raise SystemExit(f"SHA-256 mismatch for {rel}: {digest} != {pin['sha256']}")
        receipt[rel] = {"url": pin["url"], "sha256": digest, "bytes": out.stat().st_size}
    write_json(inputs / "fetch-receipt.json", receipt)
    total = sum(r["bytes"] for r in receipt.values())
    print(f"fetched {len(receipt)} files, {total / 1e6:.1f} MB, all SHA-256 verified")
    return receipt


def verify_inputs(inputs: Path) -> None:
    for rel, pin in PINS.items():
        path = inputs / rel
        if not path.exists() or sha256_file(path) != pin["sha256"]:
            raise SystemExit(f"missing or modified input {rel}; run `fetch` first")


# ----------------------------------------------------------------------------- prepare

def historical_split(n: int) -> tuple[dict, str]:
    """mRNABench/rewirebench seed-2541 split over source row order."""
    from sklearn.model_selection import train_test_split
    idx = np.arange(n)
    train, held = train_test_split(idx, test_size=0.3, random_state=2541)
    val, test = train_test_split(held, test_size=0.5, random_state=2541)
    membership = {"train": [int(i) for i in train], "validation": [int(i) for i in val],
                  "test": [int(i) for i in test]}
    digest = hashlib.sha256(json.dumps(membership, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return membership, digest


def link_components(inserts: np.ndarray, mothers: np.ndarray, k: int = LINK_K) -> np.ndarray:
    """Union-find over shared `mother` or any identical k-nt substring. Returns component ids."""
    n = len(inserts)
    parent = np.arange(n)

    def find(i):
        root = i
        while parent[root] != root:
            root = parent[root]
        while parent[i] != root:
            parent[i], i = root, parent[i]
        return root

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    first: dict = {}
    for i, m in enumerate(mothers):
        if m in first:
            union(first[m], i)
        else:
            first[m] = i
    first = {}
    for i, s in enumerate(inserts):
        for p in range(len(s) - k + 1):
            kmer = s[p:p + k]
            if kmer in first:
                union(first[kmer], i)
            else:
                first[kmer] = i
    roots = np.array([find(i) for i in range(n)])
    _, comp = np.unique(roots, return_inverse=True)  # ids ordered by lowest member index
    return comp


def grouped_split(comp: np.ndarray, seed: int = GROUPED_SEED) -> np.ndarray:
    n = len(comp)
    sizes = np.bincount(comp)
    split = np.full(n, "", dtype=object)
    giant = np.flatnonzero(sizes > GIANT_FRACTION * n)
    order = np.random.default_rng(seed).permutation(np.setdiff1d(np.arange(len(sizes)), giant))
    target = 0.15 * n
    filled = {"test": 0, "validation": 0}
    assign = {}
    for c in order:
        if filled["test"] < target:
            assign[c] = "test"; filled["test"] += sizes[c]
        elif filled["validation"] < target:
            assign[c] = "validation"; filled["validation"] += sizes[c]
        else:
            assign[c] = "train"
    for c in giant:
        assign[c] = "train"
    return np.array([assign[c] for c in comp], dtype=object)


def icc1(values: np.ndarray, groups: np.ndarray) -> dict:
    """One-way ANOVA intraclass correlation over groups with at least two members."""
    df = pd.DataFrame({"y": values, "g": groups})
    df = df[df.groupby("g").y.transform("size") >= 2]
    k = df.groupby("g").size()
    a, n = len(k), len(df)
    grand = df.y.mean()
    means = df.groupby("g").y.mean()
    ssb = float((k * (means - grand) ** 2).sum())
    ssw = float(((df.y - df.g.map(means)) ** 2).sum())
    msb, msw = ssb / (a - 1), ssw / (n - a)
    k0 = (n - (k ** 2).sum() / n) / (a - 1)
    return {"icc1": (msb - msw) / (msb + (k0 - 1) * msw), "groups": int(a), "records": int(n)}


def prepare(inputs: Path, work: Path, smoke: bool) -> dict:
    verify_inputs(inputs)
    t0 = time.perf_counter()
    src = pd.read_parquet(inputs / "mrl-sample-designed.parquet", columns=["sequence", "target_mrl_designed"])
    n = len(src)
    seqs = src["sequence"].to_numpy()
    lengths = src["sequence"].str.len()
    checks = {"rows": n, "missing_targets": int(src["target_mrl_designed"].isna().sum()),
              "all_length_855": bool((lengths == SEQ_LEN).all())}
    checks["leader_constant"] = bool((src["sequence"].str[:25] == LEADER).all())
    tails = src["sequence"].str[75:]
    checks["tail_constant"] = bool(tails.nunique() == 1)
    checks["tail_length"] = int(tails.iloc[0].__len__())
    inserts = src["sequence"].str[INSERT].to_numpy()
    checks["alphabet_acgt"] = bool(pd.Series(inserts).str.fullmatch("[ACGT]{50}").all())
    if not (checks["all_length_855"] and checks["leader_constant"] and checks["tail_constant"]
            and checks["alphabet_acgt"] and checks["missing_targets"] == 0):
        raise SystemExit(f"input track assumptions failed: {checks}")

    geo = pd.read_csv(inputs / "GSM3130443_designed_library.csv.gz", low_memory=False,
                      usecols=["utr", "library", "mother", "total", "rl"])
    geo["insert"] = geo["utr"].str[:50]
    meta = pd.DataFrame({"insert": inserts}).merge(geo, on="insert", how="left", validate="one_to_one")
    checks["geo_rows"] = len(geo)
    checks["geo_joined"] = int(meta["library"].notna().sum())
    checks["geo_rl_max_abs_diff"] = float(np.abs(meta["rl"].to_numpy() - src["target_mrl_designed"].to_numpy()).max())
    if checks["geo_joined"] != n or checks["geo_rl_max_abs_diff"] != 0.0:
        raise SystemExit(f"GEO join failed: {checks}")

    membership, digest = historical_split(n)
    checks["historical_split_sha256"] = digest
    if digest != HISTORICAL_SPLIT_SHA256:
        raise SystemExit("historical split does not match the published split hash")
    hist = np.empty(n, dtype=object)
    for name, idx in membership.items():
        hist[idx] = name

    comp = link_components(inserts, meta["mother"].to_numpy())
    grouped = grouped_split(comp)
    sizes = np.bincount(comp)
    records = pd.DataFrame({
        "source_index": np.arange(n), "insert": inserts, "mrl": src["target_mrl_designed"].to_numpy(),
        "library": meta["library"].to_numpy(), "mother": meta["mother"].to_numpy(),
        "total_reads": meta["total"].to_numpy(), "component": comp,
        "split_historical": hist, "split_grouped": grouped})
    train_hist = records.split_historical == "train"
    test_hist = records.split_historical == "test"
    comps_with_train = set(records.loc[train_hist, "component"])
    dependence = {
        "components": int(len(sizes)), "largest_component": int(sizes.max()),
        "components_over_1pct": int((sizes > GIANT_FRACTION * n).sum()),
        "mother_families": int(meta["mother"].nunique()),
        "icc_training_labels_historical": icc1(records.loc[train_hist, "mrl"].to_numpy(),
                                               records.loc[train_hist, "component"].to_numpy()),
        "historical_test_with_component_in_train": float(
            records.loc[test_hist, "component"].isin(comps_with_train).mean()),
        "grouped_test_with_component_in_train": float(
            records.loc[records.split_grouped == "test", "component"].isin(
                set(records.loc[records.split_grouped == "train", "component"])).mean()),
    }
    counts = {s: records[f"split_{s}"].value_counts().to_dict() for s in SPLITS}
    if smoke:
        records = records[records.source_index % SMOKE_STRIDE == 0].reset_index(drop=True)
    work.mkdir(parents=True, exist_ok=True)
    records.to_parquet(work / "records.parquet", index=False)
    info = {"protocol": PROTOCOL_ID, "smoke": smoke, "records_written": len(records), "checks": checks,
            "constant_tail": tails.iloc[0],
            "split_counts_full": counts, "dependence": dependence,
            "library_counts": meta["library"].value_counts().to_dict(),
            "seconds": time.perf_counter() - t0, "peak_rss_mb": peak_rss_mb()}
    write_json(work / "prepare.json", info)
    print(f"prepared {len(records)} records; split counts {counts}")
    return info


# ----------------------------------------------------------------------------- features

BASES = "ACGT"
STOPS = ("TAA", "TAG", "TGA")


def onehot(inserts) -> np.ndarray:
    lut = np.full(256, -1, dtype=np.int64)
    for i, b in enumerate(BASES):
        lut[ord(b)] = i
    codes = lut[np.frombuffer("".join(inserts).encode(), dtype=np.uint8).reshape(len(inserts), 50)]
    return np.eye(4, dtype=np.float32)[codes]  # (n, 50, 4)


def comp_features(inserts) -> np.ndarray:
    oh = onehot(inserts).mean(1)
    return np.column_stack([oh, oh[:, 1] + oh[:, 2]])  # A, C, G, T fractions, GC fraction


def kmer_features(inserts) -> np.ndarray:
    kmers = ["".join(p) for k in (1, 2, 3) for p in itertools.product(BASES, repeat=k)]
    index = {km: j for j, km in enumerate(kmers)}
    out = np.zeros((len(inserts), len(kmers)), dtype=np.float32)
    for i, s in enumerate(inserts):
        for k in (1, 2, 3):
            for p in range(50 - k + 1):
                out[i, index[s[p:p + k]]] += 1
    return out


def annot_features(inserts) -> np.ndarray:
    """uAUG/uORF/stop/Kozak features. The main AUG starts right after the 50-nt insert."""
    rows = []
    for s in inserts:
        starts = [p for p in range(48) if s[p:p + 3] == "ATG"]
        oof = [p for p in starts if (50 - p) % 3 != 0]
        inframe = [p for p in starts if (50 - p) % 3 == 0]
        uorf = 0
        for p in starts:
            if any(s[q:q + 3] in STOPS for q in range(p + 3, 48, 3)):
                uorf = 1
                break
        m3 = s[-3]
        rows.append([len(starts), float(bool(oof)), float(bool(inframe)), float(uorf),
                     sum(s[p:p + 3] in STOPS for p in range(48)), float(m3 in "AG"),
                     *[float(s[-3 + j] == b) for j in range(3) for b in BASES]])
    return np.asarray(rows, dtype=np.float32)


def full_comp_features(inserts) -> np.ndarray:
    """rewirebench SequenceComposition on the full 855-nt processed sequence."""
    tail = FULL_TAIL_CACHE["tail"]
    out = np.empty((len(inserts), 6))
    for i, s in enumerate(inserts):
        seq = LEADER + s + tail
        counts = [seq.count(b) for b in BASES]
        out[i] = [np.log1p(len(seq)), *[c / len(seq) for c in counts], (len(seq) - sum(counts)) / len(seq)]
    return out


FULL_TAIL_CACHE: dict = {}


def cheap_matrix(method: str, inserts) -> np.ndarray:
    if method == "comp_utr":
        return comp_features(inserts)
    if method == "kmer_utr":
        return kmer_features(inserts)
    if method == "onehot_pos":
        return onehot(inserts).reshape(len(inserts), -1)
    if method == "annot":
        return annot_features(inserts)
    if method == "cheap_combined":
        return np.hstack([kmer_features(inserts), onehot(inserts).reshape(len(inserts), -1),
                          annot_features(inserts)])
    raise ValueError(method)


# ----------------------------------------------------------------------------- ridge

def ridge_select(get_block, tr_idx, va_idx, y_tr, y_va, alphas=ALPHAS, chunk=4096):
    """Standardised ridge with alpha chosen on validation MSE. `get_block(idx)` returns features.

    Builds Z'Z in float64 in chunks so a 6,400-column float16 cache never needs expanding at once.
    """
    first = np.asarray(get_block(tr_idx[:1]), dtype=np.float64)
    d = first.shape[1]
    s1, s2 = np.zeros(d), np.zeros(d)
    for i in range(0, len(tr_idx), chunk):
        x = np.asarray(get_block(tr_idx[i:i + chunk]), dtype=np.float64)
        s1 += x.sum(0); s2 += (x * x).sum(0)
    mu = s1 / len(tr_idx)
    sd = np.sqrt(np.maximum(s2 / len(tr_idx) - mu ** 2, 0))
    sd[sd < 1e-12] = 1.0
    ym = float(np.mean(y_tr))
    gram, xty = np.zeros((d, d)), np.zeros(d)
    for i in range(0, len(tr_idx), chunk):
        z = (np.asarray(get_block(tr_idx[i:i + chunk]), dtype=np.float64) - mu) / sd
        gram += z.T @ z
        xty += z.T @ (y_tr[i:i + chunk] - ym)
    evals, evecs = np.linalg.eigh(gram)
    evals = np.maximum(evals, 0)
    qb = evecs.T @ xty
    weights = {a: evecs @ (qb / (evals + a)) for a in alphas}

    def predict(idx, w):
        out = []
        for i in range(0, len(idx), chunk):
            z = (np.asarray(get_block(idx[i:i + chunk]), dtype=np.float64) - mu) / sd
            out.append(z @ w + ym)
        return np.concatenate(out)

    val_mse = {a: float(np.mean((predict(va_idx, w) - y_va) ** 2)) for a, w in weights.items()}
    best = min(alphas, key=lambda a: (val_mse[a], a))
    return best, val_mse, lambda idx: predict(idx, weights[best])


# ----------------------------------------------------------------------------- CNN

def build_cnn(in_channels: int):
    import torch.nn as nn

    class CNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = nn.Sequential(
                nn.Conv1d(in_channels, 120, 8, padding="same"), nn.ReLU(),
                nn.Conv1d(120, 120, 8, padding="same"), nn.ReLU(),
                nn.Conv1d(120, 120, 8, padding="same"), nn.ReLU())
            self.head = nn.Sequential(nn.Flatten(), nn.Linear(120 * 50, 40), nn.ReLU(), nn.Dropout(0.2),
                                      nn.Linear(40, 1))

        def forward(self, x):  # x: (batch, channels, 50)
            return self.head(self.conv(x)).squeeze(-1)

    return CNN()


def choose_device(model, sample, allow_mps: bool) -> tuple[str, float | None]:
    import torch
    if not (allow_mps and torch.backends.mps.is_available()):
        return "cpu", None
    model.eval()
    with torch.no_grad():
        ref = model(sample).numpy()
        got = model.to("mps")(sample.to("mps")).cpu().numpy()
    model.to("cpu")
    diff = float(np.abs(ref - got).max())
    return ("mps" if diff < 1e-3 else "cpu"), diff


def train_cnn(get_x, tr_idx, va_idx, y_tr, y_va, in_channels, seed, max_epochs, allow_mps, batch=128,
              patience=3):
    import torch
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.set_num_threads(min(8, os.cpu_count() or 1))
    model = build_cnn(in_channels)
    mu, sd = float(y_tr.mean()), float(y_tr.std())
    device, mps_diff = choose_device(model, torch.from_numpy(get_x(tr_idx[:256])), allow_mps)
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    gen = torch.Generator().manual_seed(seed)
    yt = torch.from_numpy(((y_tr - mu) / sd).astype(np.float32))
    best, best_state, best_epoch, bad, history = np.inf, None, 0, 0, []

    def predict_on(idx, dev):
        model.eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(idx), 2048):
                out.append(model(torch.from_numpy(get_x(idx[i:i + 2048])).to(dev)).cpu().numpy())
        return np.concatenate(out) * sd + mu

    for epoch in range(1, max_epochs + 1):
        model.train()
        perm = torch.randperm(len(tr_idx), generator=gen).numpy()
        t0 = time.perf_counter()
        for i in range(0, len(perm), batch):
            b = np.sort(perm[i:i + batch])
            xb = torch.from_numpy(get_x(tr_idx[b])).to(device)
            loss = torch.mean((model(xb) - yt[b].to(device)) ** 2)
            opt.zero_grad()
            loss.backward()
            opt.step()
        val = float(np.mean((predict_on(va_idx, device) - y_va) ** 2))
        history.append({"epoch": epoch, "val_mse": val, "seconds": time.perf_counter() - t0})
        if val < best - 1e-6:
            best, best_epoch, bad = val, epoch, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    model.load_state_dict(best_state)
    model.to("cpu")
    info = {"device": device, "mps_initial_max_abs_diff": mps_diff, "best_epoch": best_epoch,
            "epochs_run": len(history), "history": history, "val_mse_training_device": best}
    return (lambda idx: predict_on(idx, "cpu")), info


# ----------------------------------------------------------------------------- UTR-LM

def load_utrlm(inputs: Path):
    import torch
    sys.path.insert(0, str(inputs / "utrlm"))
    import esm  # UTR-LM's modified ESM package, fetched at runtime
    from esm.model.esm2 import ESM2
    alphabet = esm.data.Alphabet(standard_toks="AGCT", mask_prob=0.0)
    model = ESM2(num_layers=6, embed_dim=128, attention_heads=16, alphabet=alphabet)
    state = torch.load(inputs / "utrlm" / UTRLM_CKPT, map_location="cpu", weights_only=True)
    model.load_state_dict({k.replace("module.", ""): v for k, v in state.items()}, strict=True)
    model.eval()
    return model, alphabet


def utrlm_tokens(alphabet, inserts):
    import torch
    lut = {b: alphabet.tok_to_idx[b] for b in BASES}
    return torch.tensor([[alphabet.cls_idx] + [lut[c] for c in s] + [alphabet.eos_idx] for s in inserts])


def embed(inputs: Path, work: Path) -> dict:
    import torch
    verify_inputs(inputs)
    torch.set_num_threads(min(8, os.cpu_count() or 1))
    records = pd.read_parquet(work / "records.parquet")
    t0 = time.perf_counter()
    model, alphabet = load_utrlm(inputs)
    load_s = time.perf_counter() - t0
    # Known-answer gate: masked-nucleotide accuracy on 1,000 historical-training inserts (CPU).
    train = records.loc[records.split_historical == "train", "insert"].to_numpy()[:1000]
    tok = utrlm_tokens(alphabet, train)
    gen = torch.Generator().manual_seed(1)
    mask = torch.rand(tok.shape, generator=gen) < 0.15
    mask[:, 0] = False
    mask[:, -1] = False
    masked = tok.clone()
    masked[mask] = alphabet.mask_idx
    with torch.no_grad():
        pred = model(masked)["logits"].argmax(-1)
    mlm_acc = float((pred[mask] == tok[mask]).float().mean())
    counts = pd.Series(list("".join(train))).value_counts(normalize=True)
    majority = float(counts.max())
    if not mlm_acc > majority + 0.02:
        raise SystemExit(f"UTR-LM known-answer check failed: MLM accuracy {mlm_acc:.3f} vs majority {majority:.3f}")
    cache = work / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    n = len(records)
    per_pos = np.lib.format.open_memmap(cache / "utrlm_pos.f16.npy", mode="w+", dtype=np.float16, shape=(n, 50, 128))
    mean = np.empty((n, 128), dtype=np.float32)
    inserts = records["insert"].to_numpy()
    t1 = time.perf_counter()
    with torch.no_grad():
        for i in range(0, n, 512):
            reps = model(utrlm_tokens(alphabet, inserts[i:i + 512]), repr_layers=[6],
                         return_representation=True)["representations"][6][:, 1:51]
            per_pos[i:i + 512] = reps.numpy().astype(np.float16)
            mean[i:i + 512] = reps.mean(1).numpy()
    per_pos.flush()
    np.save(cache / "utrlm_mean.npy", mean)
    info = {"checkpoint": UTRLM_CKPT, "commit": UTRLM_COMMIT, "device": "cpu",
            "parameters": int(sum(p.numel() for p in model.parameters())),
            "mlm_masked_accuracy": mlm_acc, "majority_base_rate": majority,
            "load_seconds": load_s, "embed_seconds": time.perf_counter() - t1, "records": n,
            "cache_bytes": {p.name: p.stat().st_size for p in cache.glob("utrlm_*")},
            "peak_rss_mb": peak_rss_mb()}
    write_json(work / "embed.json", info)
    print(f"embedded {n} inserts in {info['embed_seconds']:.1f} s; MLM accuracy {mlm_acc:.3f} "
          f"(majority {majority:.3f})")
    return info


# ----------------------------------------------------------------------------- fit

def fit(work: Path, split: str, method: str, max_epochs: int, seeds: list[int], allow_mps: bool) -> dict:
    records = pd.read_parquet(work / "records.parquet")
    col = f"split_{split}"
    tr = np.flatnonzero(records[col].to_numpy() == "train")
    va = np.flatnonzero(records[col].to_numpy() == "validation")
    te = np.flatnonzero(records[col].to_numpy() == "test")
    y = records.mrl.to_numpy(dtype=np.float64)
    inserts = records["insert"].to_numpy()
    out_dir = work / "runs" / split / method
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    info = {"protocol": PROTOCOL_ID, "split": split, "method": method, "n_train": len(tr),
            "n_validation": len(va), "n_test": len(te)}
    preds = {}
    if method == "train_mean":
        m = float(y[tr].mean())
        info["val_mse"] = float(np.mean((m - y[va]) ** 2))
        preds["prediction"] = np.full(len(records), m)
    elif method == "comp_full_replay":
        from sklearn.linear_model import RidgeCV
        FULL_TAIL_CACHE["tail"] = _constant_tail(work)
        x = full_comp_features(inserts)
        model = RidgeCV(alphas=REPLAY_ALPHAS).fit(x[tr], y[tr])
        info["alpha"] = float(model.alpha_)
        preds["prediction"] = model.predict(x)
        info["val_mse"] = float(np.mean((preds["prediction"][va] - y[va]) ** 2))
    elif method in RIDGE_METHODS or method in ("utrlm_mean_ridge", "utrlm_pos_ridge"):
        if method in RIDGE_METHODS:
            tf = time.perf_counter()
            x = cheap_matrix(method, inserts)
            info["feature_seconds"] = time.perf_counter() - tf
            info["n_features"] = int(x.shape[1])
            get = lambda idx: x[idx]
        elif method == "utrlm_mean_ridge":
            x = np.load(work / "cache" / "utrlm_mean.npy")
            info["n_features"] = int(x.shape[1])
            get = lambda idx: x[idx]
        else:
            pos = np.load(work / "cache" / "utrlm_pos.f16.npy", mmap_mode="r")
            info["n_features"] = 50 * 128
            get = lambda idx: np.asarray(pos[idx]).reshape(len(idx), -1)
        alpha, val_mse, predict = ridge_select(get, tr, va, y[tr], y[va])
        info.update(alpha=alpha, val_mse_by_alpha={str(k): v for k, v in val_mse.items()}, val_mse=val_mse[alpha])
        preds["prediction"] = predict(np.arange(len(records)))
    elif method in CNN_METHODS:
        if method == "cnn":
            x = onehot(inserts).transpose(0, 2, 1).copy()  # (n, 4, 50)
            get = lambda idx: x[idx]
            channels = 4
        else:
            pos = np.load(work / "cache" / "utrlm_pos.f16.npy", mmap_mode="r")
            get = lambda idx: np.ascontiguousarray(np.asarray(pos[idx], dtype=np.float32).transpose(0, 2, 1))
            channels = 128
        info["seeds"] = {}
        for seed in seeds:
            ts = time.perf_counter()
            predict, sinfo = train_cnn(get, tr, va, y[tr], y[va], channels, seed, max_epochs, allow_mps)
            p = predict(np.arange(len(records)))
            sinfo["val_mse"] = float(np.mean((p[va] - y[va]) ** 2))
            sinfo["seconds"] = time.perf_counter() - ts
            info["seeds"][str(seed)] = sinfo
            preds[f"prediction_seed{seed}"] = p
        preds["prediction"] = preds[f"prediction_seed{seeds[0]}"]
        info["val_mse"] = info["seeds"][str(seeds[0])]["val_mse"]
    else:
        raise ValueError(method)
    info["seconds"] = time.perf_counter() - t0
    info["peak_rss_mb"] = peak_rss_mb()
    keep = np.concatenate([va, te])
    frame = pd.DataFrame({"source_index": records.source_index.to_numpy()[keep],
                          "split": records[col].to_numpy()[keep], **{k: v[keep] for k, v in preds.items()}})
    frame.sort_values("source_index").to_parquet(out_dir / "predictions.parquet", index=False)
    write_json(out_dir / "fit.json", info)
    print(f"{split}/{method}: val MSE {info['val_mse']:.4f} in {info['seconds']:.1f} s")
    return info


def _constant_tail(work: Path) -> str:
    info = json.loads((work / "prepare.json").read_text())
    tail = info.get("constant_tail")
    if tail:
        return tail
    raise SystemExit("prepare.json lacks the constant tail; rerun prepare")


# ----------------------------------------------------------------------------- evaluate

def regression_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    from scipy.stats import pearsonr, spearmanr
    err = p - y
    out = {"n": int(len(y)), "mse": float(np.mean(err ** 2)), "mae": float(np.mean(np.abs(err))),
           "r2": float(1 - np.sum(err ** 2) / np.sum((y - y.mean()) ** 2))}
    if np.ptp(p) == 0:
        out["pearson"] = out["spearman"] = None
        out["correlation_note"] = "undefined: constant predictions"
    else:
        out["pearson"] = float(pearsonr(y, p)[0])
        out["spearman"] = float(spearmanr(y, p)[0])
    return out


def top_k_order(p: np.ndarray, source_index: np.ndarray) -> np.ndarray:
    return np.lexsort((source_index, -p))  # highest prediction first, ties to lower source index


def precision_at_k(p, high, source_index, k) -> float:
    order = top_k_order(p, source_index)
    return float(high[order[:k]].mean())


def cluster_bootstrap(comp_codes: np.ndarray, n_comp: int, B: int = BOOTSTRAPS, seed: int = BOOT_SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, n_comp, size=(B, n_comp))
    return np.stack([np.bincount(d, minlength=n_comp) for d in draws]).astype(np.float64)  # (B, n_comp)


def boot_mse(err2, comp_codes, n_comp, W):
    sse = np.bincount(comp_codes, weights=err2, minlength=n_comp)
    cnt = np.bincount(comp_codes, minlength=n_comp).astype(float)
    return (W @ sse) / (W @ cnt)


def boot_precision(p, high, source_index, comp_codes, W, frac=0.01):
    order = top_k_order(p, source_index)
    w_rec = W[:, comp_codes[order]]  # (B, n) record weights in ranked order
    total = w_rec.sum(1)
    k = np.maximum(np.floor(frac * total), 1)
    cum = np.cumsum(w_rec, 1)
    take = np.clip(np.minimum(cum, k[:, None]) - np.concatenate([np.zeros((len(W), 1)), np.minimum(cum, k[:, None])[:, :-1]], 1), 0, None)
    return (take * high[order][None, :]).sum(1) / k


def ci(a) -> list:
    return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]


def evaluate(work: Path) -> dict:
    records = pd.read_parquet(work / "records.parquet")
    results = {"protocol": PROTOCOL_ID, "thresholds": {"mse": MSE_THRESHOLD, "precision_at_1pct": PRECISION_THRESHOLD},
               "bootstraps": BOOTSTRAPS, "bootstrap_seed": BOOT_SEED, "splits": {}}
    for split in SPLITS:
        col = f"split_{split}"
        runs = work / "runs" / split
        if not runs.exists():
            continue
        test = records[records[col] == "test"].reset_index(drop=True)
        train_y = records.loc[records[col] == "train", "mrl"].to_numpy()
        y = test.mrl.to_numpy()
        high_cut = float(np.percentile(train_y, 90))
        high = (y >= high_cut).astype(float)
        k = max(int(np.floor(0.01 * len(test))), 1)
        codes, uniq = pd.factorize(test.component)
        n_comp = len(uniq)
        W = cluster_bootstrap(codes, n_comp)
        fits, preds = {}, {}
        for m in ALL_METHODS:
            f = runs / m / "fit.json"
            if not f.exists():
                continue
            fits[m] = json.loads(f.read_text())
            pr = pd.read_parquet(runs / m / "predictions.parquet")
            pr = test[["source_index"]].merge(pr, on="source_index", how="left", validate="one_to_one")
            preds[m] = pr
        split_out = {"n_test": len(test), "test_components": n_comp, "high_mrl_cutoff": high_cut,
                     "capacity_k": k, "test_base_rate": float(high.mean()), "methods": {}}
        cheap = [m for m in RIDGE_METHODS if m in fits]
        reference = min(cheap, key=lambda m: fits[m]["val_mse"]) if cheap else None
        split_out["reference"] = reference
        boot = {}
        for m, pr in preds.items():
            p = pr["prediction"].to_numpy()
            covered = np.isfinite(p)
            met = regression_metrics(y[covered], p[covered])
            met["coverage"] = f"{int(covered.sum())}/{len(test)}"
            met["precision_at_k"] = precision_at_k(p, high, test.source_index.to_numpy(), k)
            met["enrichment"] = met["precision_at_k"] / float(high.mean())
            bm = boot_mse((p - y) ** 2, codes, n_comp, W)
            bp = boot_precision(p, high, test.source_index.to_numpy(), codes, W)
            boot[m] = (bm, bp)
            met["mse_ci95"] = ci(bm)
            met["precision_at_k_ci95"] = ci(bp)
            met["val_mse"] = fits[m]["val_mse"]
            met["fit_seconds"] = fits[m]["seconds"]
            met["peak_rss_mb"] = fits[m]["peak_rss_mb"]
            seed_cols = [c for c in pr.columns if c.startswith("prediction_seed")]
            if seed_cols:
                met["per_seed"] = {c.replace("prediction_", ""): {
                    **{kk: vv for kk, vv in regression_metrics(y, pr[c].to_numpy()).items() if kk in ("mse", "r2", "spearman")},
                    "precision_at_k": precision_at_k(pr[c].to_numpy(), high, test.source_index.to_numpy(), k)}
                    for c in seed_cols}
                mses = [v["mse"] for v in met["per_seed"].values()]
                met["seed_mse_range"] = [min(mses), max(mses)]
            split_out["methods"][m] = met
        comparisons = []
        pairs = [(m, reference) for m in preds if reference and m not in (reference, "train_mean", "comp_full_replay")]
        pairs += [(m, "cnn") for m in FROZEN_METHODS if m in preds and "cnn" in preds]
        for m, ref in pairs:
            d_mse = boot[ref][0] - boot[m][0]
            d_prec = boot[m][1] - boot[ref][1]
            point_mse = split_out["methods"][ref]["mse"] - split_out["methods"][m]["mse"]
            point_prec = split_out["methods"][m]["precision_at_k"] - split_out["methods"][ref]["precision_at_k"]
            lo, hi = ci(d_mse)
            plo, phi = ci(d_prec)
            comparisons.append({
                "method": m, "reference": ref, "mse_reduction": point_mse, "mse_reduction_ci95": [lo, hi],
                "mse_verdict": _verdict(point_mse, lo, hi, MSE_THRESHOLD),
                "precision_gain": point_prec, "precision_gain_ci95": [plo, phi],
                "precision_verdict": _verdict(point_prec, plo, phi, PRECISION_THRESHOLD)})
        split_out["comparisons"] = comparisons
        split_out["per_library_mse"] = {
            m: test.assign(e=(preds[m]["prediction"].to_numpy() - y) ** 2).groupby("library").e.mean().to_dict()
            for m in [reference, "cnn", "utrlm_cnn", "utrlm_pos_ridge"] if m in preds}
        split_out["library_test_counts"] = test.library.value_counts().to_dict()
        if "cnn" in preds:
            q = pd.qcut(test.total_reads, 4, labels=["Q1 (fewest reads)", "Q2", "Q3", "Q4 (most reads)"])
            split_out["cnn_mse_by_read_depth_quartile"] = test.assign(
                e=(preds["cnn"]["prediction"].to_numpy() - y) ** 2, q=q).groupby("q", observed=True).e.mean().to_dict()
            if reference:
                split_out["reference_mse_by_read_depth_quartile"] = test.assign(
                    e=(preds[reference]["prediction"].to_numpy() - y) ** 2, q=q).groupby("q", observed=True).e.mean().to_dict()
        if split == "grouped" and "cnn" in preds:
            split_out["examples"] = examples(test, preds)
        results["splits"][split] = split_out
    prep = json.loads((work / "prepare.json").read_text())
    results["dependence"] = prep["dependence"]
    embed_info = work / "embed.json"
    if embed_info.exists():
        results["embed"] = json.loads(embed_info.read_text())
    write_json(work / "metrics.json", results)
    _print_summary(results)
    return results


def _verdict(point, lo, hi, threshold) -> str:
    if lo > 0 and point >= threshold:
        return "adds practical value"
    if lo > 0:
        return "difference below practical threshold"
    if hi < 0:
        return "worse than reference"
    return "no supported difference"


def examples(test: pd.DataFrame, preds: dict) -> list:
    y = test.mrl.to_numpy()
    idx = test.source_index.to_numpy()
    cols = [m for m in ["cnn", "cheap_combined", "utrlm_cnn", "utrlm_pos_ridge"] if m in preds]

    def row(i, rule):
        r = test.iloc[i]
        return {"rule": rule, "source_index": int(r.source_index), "library": r.library, "insert": r["insert"],
                "measured_mrl": float(r.mrl), "total_reads": int(r.total_reads),
                "predicted": {m: float(preds[m]["prediction"].iloc[i]) for m in cols}}

    picks = []
    for q in (10, 50, 90):
        target = np.percentile(y, q)
        i = int(np.lexsort((idx, np.abs(y - target)))[0])
        picks.append(row(i, f"measured MRL closest to test {q}th percentile"))
    err = np.abs(preds["cnn"]["prediction"].to_numpy() - y)
    i = int(np.lexsort((idx, -err))[0])
    picks.append(row(i, "largest absolute cnn (seed 0) error"))
    mothers = dict(zip(test["insert"], range(len(test))))
    snv = test[(test.library == "snv") & (test.mother != test["insert"])
               & test.mother.isin(list(mothers))].sort_values("source_index")
    if len(snv):
        i = int(test.index.get_loc(snv.index[0]))
        picks.append(row(i, "lowest-index snv variant whose reference (mother) is also in test"))
        picks.append(row(mothers[snv.iloc[0].mother], "reference (mother) of that snv variant"))
    return picks


def _print_summary(results):
    for split, s in results["splits"].items():
        print(f"\n[{split}] n_test={s['n_test']} components={s['test_components']} k={s['capacity_k']} "
              f"reference={s['reference']}")
        for m, v in s["methods"].items():
            print(f"  {m:18s} MSE {v['mse']:.3f} [{v['mse_ci95'][0]:.3f}, {v['mse_ci95'][1]:.3f}]  "
                  f"R2 {v['r2']:.3f}  P@k {v['precision_at_k']:.3f}")
        for c in s["comparisons"]:
            print(f"  {c['method']} vs {c['reference']}: dMSE {c['mse_reduction']:+.3f} "
                  f"[{c['mse_reduction_ci95'][0]:+.3f}, {c['mse_reduction_ci95'][1]:+.3f}] {c['mse_verdict']}; "
                  f"dP@k {c['precision_gain']:+.3f} {c['precision_verdict']}")


# ----------------------------------------------------------------------------- run-all

def run_all(inputs: Path, work: Path, smoke: bool, allow_mps: bool) -> None:
    me = [sys.executable, str(Path(__file__).resolve())]
    log = {"hardware": hardware(), "smoke": smoke, "steps": []}

    def step(args):
        t0 = time.perf_counter()
        subprocess.run(me + args, check=True)
        log["steps"].append({"args": args, "wall_seconds": time.perf_counter() - t0})

    step(["fetch", "--inputs", str(inputs)])
    step(["prepare", "--inputs", str(inputs), "--work", str(work)] + (["--smoke"] if smoke else []))
    step(["embed", "--inputs", str(inputs), "--work", str(work)])
    epochs = ["--max-epochs", "2", "--seeds", "0"] if smoke else []
    mps = [] if allow_mps else ["--cpu-only"]
    for split in SPLITS:
        for method in ALL_METHODS:
            step(["fit", "--work", str(work), "--split", split, "--method", method] + epochs + mps)
    step(["evaluate", "--work", str(work)])
    write_json(work / "run-log.json", log)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("fetch"); a.add_argument("--inputs", type=Path, required=True)
    a = sub.add_parser("prepare"); a.add_argument("--inputs", type=Path, required=True)
    a.add_argument("--work", type=Path, required=True); a.add_argument("--smoke", action="store_true")
    a = sub.add_parser("embed"); a.add_argument("--inputs", type=Path, required=True)
    a.add_argument("--work", type=Path, required=True)
    a = sub.add_parser("fit"); a.add_argument("--work", type=Path, required=True)
    a.add_argument("--split", choices=SPLITS, required=True); a.add_argument("--method", choices=ALL_METHODS, required=True)
    a.add_argument("--max-epochs", type=int, default=20); a.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    a.add_argument("--cpu-only", action="store_true")
    a = sub.add_parser("evaluate"); a.add_argument("--work", type=Path, required=True)
    a = sub.add_parser("run-all"); a.add_argument("--inputs", type=Path, required=True)
    a.add_argument("--work", type=Path, required=True); a.add_argument("--smoke", action="store_true")
    a.add_argument("--cpu-only", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "fetch":
        fetch(args.inputs)
    elif args.cmd == "prepare":
        prepare(args.inputs, args.work, args.smoke)
    elif args.cmd == "embed":
        embed(args.inputs, args.work)
    elif args.cmd == "fit":
        fit(args.work, args.split, args.method, args.max_epochs, args.seeds, not args.cpu_only)
    elif args.cmd == "evaluate":
        evaluate(args.work)
    elif args.cmd == "run-all":
        run_all(args.inputs, args.work, args.smoke, not args.cpu_only)


if __name__ == "__main__":
    main()
