# -*- coding: utf-8 -*-
"""教學數字：投影片與系統用同一份前處理（prep.py）算出來的數字；跟 facts/FACTS-20-evidence/rerun.json 對帳。"""
import os
import sys
import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import prep           # noqa: E402
import pca_seg        # noqa: E402
import cluster_seg    # noqa: E402
import anomaly_seg    # noqa: E402
from features import KEYS   # noqa: E402

ALL = tuple(range(10))


@pytest.fixture(scope="module")
def D():
    d = prep.load()
    for m in (pca_seg, cluster_seg, anomaly_seg):
        m.load(d)
    return d


def idx(*keys):
    return tuple(prep.cols_index(keys))


def test_split_same_as_day1(D):
    assert (len(D.im), int(D.y[D.im].sum())) == (2000, 134)
    assert (len(D.it), int(D.y[D.it].sum())) == (148000, 9892)


def test_codes_9698(D):
    assert int(D.code_rows.sum()) == 269 and int(D.code_rows[D.im].sum()) == 6


def test_prep_clean(D):
    assert not np.isnan(D.Z).any()
    assert np.allclose(D.Z[D.im].mean(axis=0), 0, atol=1e-9)
    assert np.allclose(D.Z[D.im].std(axis=0), 1, atol=1e-9)
    assert prep.LOG_KEYS == ("util", "late30", "debt", "income", "late90", "realestate", "late60")


def test_transform_does_not_mutate(D):
    before = D.raw.copy()
    prep.transform(D.raw, D.im)
    assert np.array_equal(before, D.raw, equal_nan=True)


def test_pca_numbers(D):
    r = pca_seg.fit(ALL)
    assert r["cum"][:3] == [0.1948, 0.361, 0.4914]
    pc1 = r["loadings"][0]
    top = sorted(pc1, key=lambda k: -abs(pc1[k]))[:4]
    assert top == ["util", "late90", "late60", "age"]
    assert len(r["xyz"]) == 2000 and len(r["xyz"][0]) == 3


def test_pca_recon(D):
    """用前 k 個分數還原：整體＝累積資訊；只用 1 個分數時負債比完全還原不回來。"""
    r = pca_seg.fit(ALL)
    j = KEYS.index("debt")
    assert r["recon"][0][j] == 0 and r["recon"][2][j] == 46
    assert r["recon"][2][KEYS.index("util")] == 48 and all(v == 100 for v in r["recon"][-1])


def test_unscale_roundtrip(D):
    back = prep.unscale(D.Z[D.im], D.mu, D.sd)
    raw = D.raw[D.im]
    for k in ("util", "age", "nloans"):
        j = KEYS.index(k)
        assert np.allclose(back[:, j], raw[:, j])


def test_pca_codes_blow_up(D):
    """96/98 保留：PC1 的變異比例變大（被 6 個人撐開）。"""
    assert pca_seg.fit(ALL, True)["ev"][0] == 0.2517
    assert pca_seg.fit(ALL)["ev"][0] == 0.1948


def test_pca_one_col_pads(D):
    r = pca_seg.fit(idx("age"))
    assert r["cum"] == [1.0] and all(p[1] == 0 and p[2] == 0 for p in r["xyz"])


def test_cluster_class(D):
    r = cluster_seg.fit(**cluster_seg.CLASS_CFG)
    assert [c["n"] for c in r["clusters"]] == [1301, 528, 171]
    assert [c["rate_test"] for c in r["clusters"]] == [2.7, 7.1, 33.5]
    assert r["n_ambiguous"] == 1


def test_cluster_strip(D):
    r = cluster_seg.strip_answers(cluster_seg.fit(**cluster_seg.CLASS_CFG))
    assert all("rate_test" not in c and "k_student" not in c for c in r["clusters"])
    assert "desc" in r["clusters"][0]


def test_cluster_describe(D):
    r = cluster_seg.fit(**cluster_seg.CLASS_CFG)
    late = r["clusters"][2]["desc"]["late90"]["share"]
    assert late > r["overall"]["late90"]["share"] * 3          # 第 3 群（高違約）逾期 90 天以上的人多很多
    assert "median" in r["overall"]["util"] and "share" in r["overall"]["dep"]


def test_cluster_start_changes_result(D):
    """同一組設定換起點，GMM k=3 會分出不同的群（教材）。"""
    a = cluster_seg.fit(ALL, 3, "gmm", 0)["labels"]
    b = cluster_seg.fit(ALL, 3, "gmm", 1)["labels"]
    assert a != b


def test_cluster_sorted_by_size(D):
    for k in cluster_seg.KS:
        n = [c["n"] for c in cluster_seg.fit(ALL, k, "kmeans", 0)["clusters"]]
        assert n == sorted(n, reverse=True) and sum(n) == 2000


def test_anomaly_numbers(D):
    a = anomaly_seg.score(ALL)
    assert (a["student"]["f1"], a["test"]["f1"]) == (34.13, 33.87)
    assert a["student"]["n_flag"] == 200 and a["test"]["n_flag"] == 14800
    assert anomaly_seg.score(idx("late30", "late90", "late60"))["test"]["f1"] == 40.31
    # 畫面與排名用的是鑑別度（2026-11-17 起）；F1 仍算在結果裡
    assert a["test"]["eta"] == 8.3 and anomaly_seg.score(idx("late30", "late90", "late60"))["test"]["eta"] == 12.9
    assert len(a["flagged"]) == 200 and len(a["top"]) == 5


def test_anomaly_inverted_u(D):
    c = anomaly_seg.size_curve()["best"]
    assert max(c, key=c.get) == 3
    assert c[1] < c[3] and c[10] < c[3]


def test_anomaly_cases(D):
    c = anomaly_seg.cases()
    assert c["defaulters_never_late_pct"] == 32.6
    assert all(p["default"] == 0 for p in c["odd_not_default"])
    assert c["odd_not_default"][0]["raw"][KEYS.index("util")] > 1000     # 額度使用率上萬倍：資料錯


def test_flag_stats_ties():
    s = np.array([5, 4, 4, 4, 1, 1, 1, 1, 1, 1.0])
    y = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    r = anomaly_seg.flag_stats(s, y, q=0.2)       # 標 2 人：5 分的 1 人＋4 分的 3 人抽 1 人
    assert r["n_flag"] == 2 and r["tie_group"] == 3 and r["tie_drawn"] == 1
    assert r["tp"] == round(1 + 1 / 3, 1)
