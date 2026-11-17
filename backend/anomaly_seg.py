# -*- coding: utf-8 -*-
"""異常偵測段（比賽：抓異常）。四條路線（見下方「四條路線」）：挑欄位 →（要不要 PCA）→（要不要分群）→ 哪些人是異常。
下面的規則是路線 1（只挑欄位，用多變量常態找出最不常見的 10%）；其他路線在檔案後半。

規則（facts/FACTS-19、FACTS-20）：
  - 模型：學生 2,000 人（只用挑的欄位）估平均與共變異；分數＝馬氏距離平方，越大越不常見（機率密度越低）。
    建模完全不看違約答案。
  - 標記：分數最高的 10%。學生資料標 200 人、考題標 14,800 人；卡在線上的同分者抽籤補滿（算分用期望值）。
  - 分數：鑑別度（2026-11-17 起，跟分群段同一把尺）＝把人分成「異常／正常」兩群，兩群違約比例差多開
    （cluster_seg.spread_score，少於 20 人的那一群不算）。F1 仍然算好放在結果裡，但畫面不顯示、不拿來排名。
    依據 facts/FACTS-29：27,706 組設定，兩種分數的等級相關 0.89–1.00，每條路線第一名相同。
    學生手機看「自己 2,000 人」的分數；考題分數只給老師，揭曉才看。
    1,023 種挑法中，兩者的等級相關 0.967（FACTS-20），所以學生手上的分數就是可靠的驗證分數。
  - 揭露：10% 是看過答案才定的；5% 時只挑一欄就是第一名（FACTS-19）。
"""
import itertools
from functools import lru_cache

import numpy as np

from features import KEYS
import cluster_seg
import pca_seg

DATA = None
Q = 0.10            # 標出最不常見的 10%
TOP_SHOW = 5        # 手機上列出最異常的幾個人
CLASS_COLS = tuple(range(10))   # 揭曉「異常≠違約」用：十欄全用


def load(data):
    global DATA
    DATA = data
    score.cache_clear()
    _pipe.cache_clear()


def mvn_score(Zfit: np.ndarray, Za: np.ndarray) -> np.ndarray:
    mu = Zfit.mean(axis=0)
    cov = np.atleast_2d(np.cov(Zfit, rowvar=False)) + 1e-6 * np.eye(Zfit.shape[1])
    P = np.linalg.pinv(cov)
    D = Za - mu
    return np.round(np.einsum("ij,jk,ik->i", D, P, D), 8)   # 取到小數 8 位：浮點誤差不該拆開同分


def _eta(n: float, tp: float, P: int, N: int) -> dict:
    """鑑別度與兩群的違約比例。n＝標成異常的人數，tp＝其中違約的人數。"""
    rest = N - n
    return {"eta": cluster_seg.spread_score([n, rest], [tp, P - tp]) if 0 < n < N else 0.0,
            "rate_flag": round(tp / n * 100, 1) if n else None, "rate_rest": round((P - tp) / rest * 100, 1) if rest else None,
            "n_rest": int(rest)}


def flag_stats(s: np.ndarray, y: np.ndarray, q: float = Q) -> dict:
    """正好標 round(q*N) 人；同分抽籤，真違約人數取期望值。"""
    N, P = len(s), int(y.sum())
    n = int(round(q * N))
    v = np.partition(s, N - n)[N - n]
    above, tie = s > v, s == v
    need = n - int(above.sum())
    tp = float((above & (y == 1)).sum() + need * y[tie].mean())
    p, r = tp / n, tp / P
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"n_flag": n, "tp": round(tp, 1), "positives": P, "precision": round(p * 100, 1), "recall": round(r * 100, 1),
            "f1": round(f1 * 100, 2), "lift": round(p / (P / N), 2), "tie_group": int(tie.sum()), "tie_drawn": need,
            "cut": float(v), **_eta(n, tp, P, N)}


def flagged_rows(s: np.ndarray, q: float = Q) -> np.ndarray:
    """畫圖用：標出的人（同分時照列號取，固定不變）。"""
    n = int(round(q * len(s)))
    return np.argsort(-s, kind="stable")[:n]


@lru_cache(maxsize=1100)
def score(cols: tuple) -> dict:
    Zm = DATA.Z[DATA.im][:, list(cols)]
    s = mvn_score(Zm, DATA.Z[:, list(cols)])
    sm, st = s[DATA.im], s[DATA.it]
    mine = flag_stats(sm, DATA.y[DATA.im])
    test = flag_stats(st, DATA.y[DATA.it])
    top = np.argsort(-sm, kind="stable")[:TOP_SHOW]
    return {
        "cols": [KEYS[c] for c in cols],
        "student": mine,
        "test": test,
        "flagged": sorted(flagged_rows(sm).tolist()),      # 2,000 人裡的位置（0–1999）
        "top": [{"i": int(i), "score": round(float(sm[i]), 1)} for i in top],
    }


# ===== 四條路線（2026-11-17）=====
# 學生可以選擇要不要加 PCA、要不要加分群，再提交「哪些人是異常」：
#   路線 1  原始欄位                    → 馬氏距離最大的 10%（上面的 score()，原本的比賽）
#   路線 2  原始欄位 → PCA 留前 pca_k 個分數 → 馬氏距離最大的 10%
#   路線 3  原始欄位 → 分群              → 人數最少的那一群就是異常（電腦挑，學生不指定）
#   路線 4  原始欄位 → PCA → 分群        → 同上
# PCA、分群都只用學生 2,000 人來算（不看違約）；考題的人用同一組權重、同一個分群模型套上去。
# 分群固定起點 0（免得靠換起點刷分）；群的編號照人數由多到少。
# 2026-11-17 改：原本讓學生自己指定哪幾群是異常，實測變成「挑逾期最多的那群」＝猜違約（FACTS-28），
#   所以改成電腦挑「有人的群裡人數最少的那一群」。四條路線的「異常」都是同一個意思：少見的人。


def _feats(cols: tuple, pca_k: int) -> np.ndarray:
    Z = DATA.Z[:, list(cols)]
    if not pca_k:
        return Z
    mu, Vt, _ = pca_seg._svd(Z[DATA.im])
    return (Z - mu) @ Vt[:pca_k].T


def _plain_stats(flag: np.ndarray, y: np.ndarray) -> dict:
    """指定名單（不是固定 10%）的統計：人數、違約人數、鑑別度（F1 也算，但畫面不用）。"""
    n, P, tp = int(flag.sum()), int(y.sum()), int((flag & (y == 1)).sum())
    p, r = (tp / n if n else 0.0), tp / P
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"n_flag": n, "tp": tp, "positives": P, "precision": round(p * 100, 1), "recall": round(r * 100, 1),
            "f1": round(f1 * 100, 2), "lift": round(p / (P / len(y)), 2) if n else 0.0, "tie_group": 0, "tie_drawn": 0, **_eta(n, tp, P, len(y))}


@lru_cache(maxsize=600)
def _pipe(cols: tuple, pca_k: int, k: int, method: str) -> dict:
    """路線 2–4 共用：算特徵；不分群就算馬氏距離，分群就算每個人在哪一群（學生與考題）。"""
    X = _feats(cols, pca_k)
    Xm = X[DATA.im]
    if not k:
        return {"s": mvn_score(Xm, X)}
    model = cluster_seg._model(method, k, 0).fit(Xm)
    lab = model.predict(Xm)
    order = np.argsort(-np.bincount(lab, minlength=k), kind="stable")
    remap = np.empty(k, int)
    remap[order] = np.arange(k)
    return {"lab": remap[lab], "lab_t": remap[model.predict(X[DATA.it])]}


def run(cols: tuple, pca_k: int = 0, k: int = 0, method: str = "kmeans") -> dict:
    """一次提交的完整結果（含考題分數；給學生前用 public() 拿掉）。pick＝分群時被當成異常的那一群（電腦挑的）。"""
    if not pca_k and not k:
        return {**score(cols), "pca_k": 0, "k": 0, "method": "", "pick": []}
    r = _pipe(cols, pca_k, k, method)
    ym, yt = DATA.y[DATA.im], DATA.y[DATA.it]
    out = {"cols": [KEYS[c] for c in cols], "pca_k": pca_k, "k": k, "method": method if k else "", "pick": []}
    if not k:
        sm, st = r["s"][DATA.im], r["s"][DATA.it]
        top = np.argsort(-sm, kind="stable")[:TOP_SHOW]
        return {**out, "student": flag_stats(sm, ym), "test": flag_stats(st, yt), "flagged": sorted(flagged_rows(sm).tolist()),
                "top": [{"i": int(i), "score": round(float(sm[i]), 1)} for i in top]}
    lab, lab_t = r["lab"], r["lab_t"]
    out["labels"] = lab.tolist()
    out["clusters"] = [{"n": int((lab == c).sum()), **cluster_seg._profile(DATA.im[lab == c])} for c in range(k)]
    out["overall"] = cluster_seg.describe(DATA.im)
    sizes = np.bincount(lab, minlength=k)
    odd = int(np.flatnonzero(sizes > 0)[-1])       # 群照人數由多到少排，所以最後一個有人的群就是人數最少的
    fm, ft = lab == odd, lab_t == odd
    student, test = _plain_stats(fm, ym), _plain_stats(ft, yt)
    if student["n_flag"] < cluster_seg.MIN_N:
        # 學生手機上這一群不到 20 人、顯示「人太少不算分」；考題人數是 74 倍，同一群常常超過 20 人。
        # 兩邊要一致：學生資料上不算，排行榜上也不算。
        test = {**test, "eta": 0.0}
    return {**out, "pick": [odd], "student": student, "test": test, "flagged": np.flatnonzero(fm).tolist(), "top": []}


def public(res: dict) -> dict:
    """給學生：拿掉考題分數。"""
    return {k: v for k, v in res.items() if k != "test"}


def size_curve() -> dict:
    """揭曉用：挑 1–10 欄時，考題鑑別度的最高與平均（全部 1,023 種挑法，不做 PCA、不分群）。約 5 秒。"""
    best, mean = {}, {}
    for r in range(1, 11):
        f = [score(c)["test"]["eta"] for c in itertools.combinations(range(10), r)]
        best[r], mean[r] = round(max(f), 1), round(float(np.mean(f)), 1)
    return {"best": best, "mean": mean}


def cases() -> dict:
    """揭曉「異常≠違約」：十欄全用時，考題裡最異常、卻沒違約的人；違約者中從沒逾期過的比例；收入填 0 的人。"""
    cols = list(CLASS_COLS)
    s = mvn_score(DATA.Z[DATA.im][:, cols], DATA.Z[:, cols])
    it, y, raw = DATA.it, DATA.y, DATA.raw
    st = s[it]
    order = np.argsort(-st, kind="stable")
    odd_ok = [int(it[i]) for i in order if y[it[i]] == 0][:3]
    late = raw[:, [KEYS.index(k) for k in ("late30", "late60", "late90")]]
    never_late = np.nan_to_num(late).sum(axis=1) == 0
    bad = y[it] == 1
    flag = np.zeros(len(it), bool)
    flag[flagged_rows(st)] = True
    inc0 = raw[it, KEYS.index("income")] == 0
    def person(r):
        return {"raw": [None if np.isnan(v) else float(v) for v in raw[r]], "default": int(y[r])}
    return {
        "odd_not_default": [person(r) for r in odd_ok],
        "defaulters_never_late_pct": round(float(never_late[it][bad].mean()) * 100, 1),
        "defaulters_never_late_caught_pct": round(float(flag[bad & never_late[it]].mean()) * 100, 1),
        "income0_n_test": int(inc0.sum()), "income0_flagged_pct": round(float(flag[inc0].mean()) * 100, 1),
        "income0_rate_test": round(float(y[it][inc0].mean()) * 100, 2),
        "base_rate_test": round(float(y[it].mean()) * 100, 2),
    }
