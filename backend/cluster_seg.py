# -*- coding: utf-8 -*-
"""分群段：學生挑欄位、群數、方法（起點只在第 1 步當示範換） → 2,000 人各在哪一群、每群長什麼樣。

方法：
  gmm     高斯混合模型（full 共變異、reg_covar=1e-3、n_init=3）：每人得到「屬於各群的機率」
  kmeans  K-means（n_init=10）：每人只歸一群
起點（start）＝random_state。同一組設定換起點，GMM 可能分出不同的群（k=3 時 ARI 0.47–1.0，facts/FACTS-20），
  這是教材：非監督沒有標準答案。
群的編號照人數由多到少排（第 1 群最大），免得換起點後編號亂跳。
違約比例（學生資料、考題）只在老師揭曉後由 server 附上；這裡一律算好，server 決定給不給。
「模稜兩可」：GMM 最高的那一群機率 < 0.6。
"""
from functools import lru_cache

import numpy as np
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture

from features import KEYS, BY_KEY
import prep

DATA = None
KS = (2, 3, 4, 5, 6, 7, 8)     # 學生可以自己改群數（2026-11-16 從 2–5 放寬到 2–8）
METHODS = ("gmm", "kmeans")
STARTS = tuple(range(5))
AMBIGUOUS = 0.6
MIN_N = 20      # 「自己試」的分數：少於這個人數的群不算（擋掉切出幾個人的小群；2026-11-17，依據 facts/FACTS-26）
CLASS_CFG = {"cols": tuple(range(10)), "k": 3, "method": "gmm", "start": 0}   # 全班一起取名、投票的那一份


def load(data):
    global DATA
    DATA = data
    fit.cache_clear()


def _model(method: str, k: int, start: int):
    if method == "gmm":
        return GaussianMixture(k, covariance_type="full", reg_covar=1e-3, n_init=3, random_state=start, max_iter=300)
    return KMeans(n_clusters=k, n_init=10, random_state=start)


def _clean_raw(rows: np.ndarray) -> np.ndarray:
    """原始值，但 96/98 當沒填（同前處理）。"""
    raw = DATA.raw[rows].copy()
    for k in prep.LATE_KEYS:
        j = KEYS.index(k)
        raw[np.isin(raw[:, j], prep.CODES), j] = np.nan
    return raw


def describe(rows: np.ndarray) -> dict:
    """一群人的十欄：比例、金額、年齡用中位數；次數用「至少 1 次（筆、人）的人佔幾 %」（中位數多半是 0，看不出差別）。
    沒填的人不算。"""
    raw = _clean_raw(rows)
    out = {}
    for j, k in enumerate(KEYS):
        v = raw[:, j][~np.isnan(raw[:, j])]
        if BY_KEY[k]["kind"] == "count":
            out[k] = {"share": round(float((v >= 1).mean()) * 100, 1) if len(v) else None}
        else:
            out[k] = {"median": float(np.median(v)) if len(v) else None}
    return out


def _profile(rows: np.ndarray) -> dict:
    """一群人的長相：describe() 與標準化平均（看哪一欄特別高或低）。"""
    if len(rows) == 0:      # 相異值比群數少時（例如只挑一個逾期欄、分 8 群）會出現沒有人的群；平均是 NaN，JSON 送不出去
        return {"desc": describe(rows), "zmean": {k: 0.0 for k in KEYS}}
    z = DATA.Z[rows]
    return {"desc": describe(rows), "zmean": {k: round(float(v), 2) for k, v in zip(KEYS, z.mean(axis=0))}}


@lru_cache(maxsize=600)
def fit(cols: tuple, k: int, method: str, start: int) -> dict:
    Zm = DATA.Z[DATA.im][:, list(cols)]
    model = _model(method, k, start).fit(Zm)
    lab = model.predict(Zm)
    order = np.argsort(-np.bincount(lab, minlength=k), kind="stable")   # 舊編號 → 新編號（人多的在前）
    remap = np.empty(k, int)
    remap[order] = np.arange(k)
    lab = remap[lab]
    lab_t = remap[model.predict(DATA.Z[DATA.it][:, list(cols)])]
    ym, yt = DATA.y[DATA.im], DATA.y[DATA.it]
    if method == "gmm":
        prob = model.predict_proba(Zm)[:, order]
    else:
        prob = np.eye(k)[lab]
    clusters = []
    for c in range(k):
        rows = DATA.im[lab == c]
        n, nt = int((lab == c).sum()), int((lab_t == c).sum())
        clusters.append({
            "n": n, "n_test": nt,
            "k_student": int(ym[lab == c].sum()), "k_test": int(yt[lab_t == c].sum()),
            "rate_student": round(float(ym[lab == c].mean()) * 100, 1) if n else None,
            "rate_test": round(float(yt[lab_t == c].mean()) * 100, 1) if nt else None,
            **_profile(rows),
        })
    return {
        "overall": describe(DATA.im),
        "cols": [KEYS[c] for c in cols], "k": k, "method": method, "start": start,
        "labels": lab.tolist(),
        "prob": np.round(prob, 2).tolist(),
        "n_ambiguous": int((prob.max(axis=1) < AMBIGUOUS).sum()),
        "clusters": clusters,
        "score": spread_score([c["n"] for c in clusters], [c["k_student"] for c in clusters]),
    }


def spread_score(n, k_def) -> float:
    """「自己試」的分數（0–100）：各群違約比例差得多開。
    ＝ Σ(人數 ≥ MIN_N 的群) 人數 ×（該群違約比例 − 全體比例）² ÷（總人數 × 全體比例 ×（1 − 全體比例））× 100
    也就是違約（0/1）的變異裡，有幾 % 可以用「分在哪一群」說明（η²）；小群不計入。只用學生資料 2,000 人。"""
    n, k_def = np.asarray(n, float), np.asarray(k_def, float)
    N, m = n.sum(), k_def.sum() / n.sum()
    ok = n >= MIN_N
    r = k_def[ok] / n[ok]
    return round(float((n[ok] * (r - m) ** 2).sum() / (N * m * (1 - m)) * 100), 1)


def strip_answers(res: dict) -> dict:
    """揭曉前：拿掉每群的違約人數與比例。"""
    hidden = ("k_student", "k_test", "rate_student", "rate_test")
    res = {k: v for k, v in res.items() if k != "score"}
    return {**res, "clusters": [{k: v for k, v in c.items() if k not in hidden} for c in res["clusters"]]}
