# -*- coding: utf-8 -*-
"""PCA 段。教學順序（四步；「為什麼要壓」改在投影片講，系統畫面 2026-11-16 拿掉）：
  1. 2 欄示範（demo2）：額度使用率 × 年齡 → 壓到一條線上 → 每人 1 個分數；離線的距離＝還原不回來的部分。
  2. 10 欄 → 3 個分數（fit）：「留下幾成資訊」＝用前 k 個分數還原原本的欄位，還原得回來的比例（recon、cum）；
     點一個人看原本 vs 還原（person）。
  3. 每個分數在量什麼（loadings）→ 取名。
  4. 公布誰違約：各主成分高分端的違約比例（by_pc_default，揭曉才給）。

不看違約答案（非監督）。正負號：每個主成分「權重絕對值最大的那一欄」為正，方便命名。
「還原得回來的比例」＝1 − 還原誤差平方和 ÷ 原本的平方和（標準化後），整體就是累積解釋變異比例。
"""
from functools import lru_cache

import numpy as np

from features import KEYS
import prep

DATA = None     # prep.Data，server 啟動時 load() 設定
DEMO_KEYS = ("util", "age")     # 第 1 步的兩欄：都是連續值，圖上不會疊成格子


def load(data):
    global DATA
    DATA = data
    fit.cache_clear()
    _svd_all.cache_clear()


def _svd(Zm: np.ndarray):
    mu = Zm.mean(axis=0)
    _, s, Vt = np.linalg.svd(Zm - mu, full_matrices=False)
    Vt = Vt.copy()
    for i in range(Vt.shape[0]):
        if Vt[i, np.argmax(np.abs(Vt[i]))] < 0:
            Vt[i] = -Vt[i]
    var = s ** 2
    return mu, Vt, var / var.sum()


def _recon(Zc: np.ndarray, Vt: np.ndarray) -> list:
    """用前 k 個分數還原：每一欄還原得回來幾 %（k＝1…欄數）。Zc 已置中。"""
    tot = (Zc ** 2).sum(axis=0)
    out = []
    for k in range(1, Vt.shape[0] + 1):
        R = Zc @ Vt[:k].T @ Vt[:k]
        r2 = 1 - ((Zc - R) ** 2).sum(axis=0) / np.where(tot == 0, 1, tot)
        out.append([round(float(v) * 100) for v in r2])
    return out


@lru_cache(maxsize=1100)
def fit(cols: tuple, keep_codes: bool = False) -> dict:
    """cols：欄號 tuple（照 KEYS 順序）。回傳 2,000 人的前 3 個主成分座標（不足 3 欄補 0）。"""
    Z = DATA.Z_keep if keep_codes else DATA.Z
    Zm = Z[DATA.im][:, list(cols)]
    mu, Vt, ev = _svd(Zm)
    pcs = (Zm - mu) @ Vt.T
    xyz = np.zeros((len(Zm), 3))
    m = min(3, pcs.shape[1])
    xyz[:, :m] = pcs[:, :m]
    keys = [KEYS[c] for c in cols]
    return {
        "cols": keys,
        "keep_codes": keep_codes,
        "xyz": np.round(xyz, 3).tolist(),
        "ev": [round(float(v), 4) for v in ev],
        "cum": [round(float(v), 4) for v in np.cumsum(ev)],
        "recon": _recon(Zm - mu, Vt),          # recon[k-1][j]：用前 k 個分數，第 j 欄還原幾 %
        "loadings": [{k: round(float(Vt[i, j]), 3) for j, k in enumerate(keys)} for i in range(min(3, len(keys)))],
    }


def demo2() -> dict:
    """第 1 步：兩欄壓成 1 個分數。點（標準化後）、線的方向、每人的分數與還原值（原始單位）。"""
    cols = prep.cols_index(DEMO_KEYS)
    Zm = DATA.Z[DATA.im][:, cols]
    mu, Vt, ev = _svd(Zm)
    v = Vt[0]
    score = (Zm - mu) @ v
    back = prep.unscale(mu + np.outer(score, v), DATA.mu, DATA.sd, cols)
    return {
        "cols": list(DEMO_KEYS),
        "pts": np.round(Zm, 3).tolist(),
        "dir": [round(float(x), 4) for x in v],
        "r": round(float(np.corrcoef(Zm.T)[0, 1]), 2),
        "keep": round(float(ev[0]), 4),
        "score": np.round(score, 2).tolist(),
        "restored": np.round(back, 4).tolist(),
    }


@lru_cache(maxsize=1)
def _svd_all():
    Zm = DATA.Z[DATA.im]
    mu, Vt, _ = _svd(Zm)
    return mu, Vt


def person(i: int, k: int) -> dict:
    """第 2 步：十欄全用，第 i 個人（0–1999）的前 k 個分數，以及用這 k 個分數還原的十欄（原始單位）。"""
    mu, Vt = _svd_all()
    z = DATA.Z[DATA.im[i]]
    s = (z - mu) @ Vt[:k].T
    back = prep.unscale((mu + s @ Vt[:k])[None, :], DATA.mu, DATA.sd)[0]
    return {"i": i, "k": k, "scores": [round(float(x), 2) for x in s], "restored": [round(float(x), 4) for x in back]}


def by_pc_default(n_pc: int = 3) -> list:
    """第 4 步（揭曉）：十欄全用，各主成分分數高低兩半、最高 10% 的違約比例（學生資料 2,000 人）。"""
    xyz = np.array(fit(tuple(range(len(KEYS))))["xyz"])
    y = DATA.y[DATA.im]
    out = []
    for j in range(n_pc):
        x = xyz[:, j]
        med, q90 = np.quantile(x, [0.5, 0.9])
        out.append({"pc": f"PC{j + 1}",
                    "low": round(float(y[x < med].mean()) * 100, 1),
                    "high": round(float(y[x >= med].mean()) * 100, 1),
                    "top10": round(float(y[x >= q90].mean()) * 100, 1)})
    return out
