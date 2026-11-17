# -*- coding: utf-8 -*-
"""API：答案（違約者、每群違約比例、考題分數）只在老師開關後才給；投票、取名、提交的規則。"""
import os
import sys
import pytest
from fastapi.testclient import TestClient

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import server                       # noqa: E402

ALL = ",".join(server.KEYS)


@pytest.fixture()
def client():
    c = TestClient(server.app)
    c.post("/api/clear")
    return c


def test_meta(client):
    m = client.get("/api/meta").json()
    assert (m["sample_n"], m["sample_k"], m["test_n"]) == (2000, 134, 148000)
    assert m["phase"] == "pca" and m["labels"] is False
    assert m["anomaly"]["n_flag_student"] == 200 and m["anomaly"]["n_flag_test"] == 14800
    assert all("answer_id" not in v for v in m["votes"])
    assert m["name_slots"] == {"pca": ["PC1", "PC2"]}      # 分群不取名（2026-11-16）
    assert m["cluster"]["min_n"] == 20 and len(m["cluster"]["pc_axes"]) == 3 and m["epoch"]


def test_people_no_labels(client):
    r = client.get("/api/people").json()
    assert len(r["rows"]) == 2000 and len(r["rows"][0]) == 10 and "labels" not in r


def test_labels_gated(client):
    assert "error" in client.get("/api/labels").json()
    client.post("/api/labels/toggle")
    lab = client.get("/api/labels").json()["labels"]
    assert len(lab) == 2000 and sum(lab) == 134


def test_pca_errors(client):
    assert "error" in client.get("/api/pca?cols=").json()
    assert "error" in client.get("/api/pca?cols=age,hack").json()
    assert client.get("/api/pca?cols=age,util").json()["cols"] == ["util", "age"]


def test_pca_reveal_gated(client):
    assert "error" in client.get("/api/pca/reveal").json()
    client.post("/api/reveal", json={"seg": "pca"})
    r = client.get("/api/pca/reveal").json()
    assert [b["top10"] for b in r["by_pc"]] == [32.5, 15.5, 15.5] and r["base"] == 6.7


def test_pca_demo_and_person(client):
    d = client.get("/api/pca/demo").json()
    assert d["cols"] == ["util", "age"] and d["keep"] == 0.6457 and d["r"] == -0.29
    assert len(d["pts"]) == 2000 and len(d["restored"][0]) == 2
    assert d["keep_ev1"] > d["ev1"] and d["n_codes_student"] == 6
    p10 = client.get("/api/pca/person?i=5&k=10").json()
    raw = client.get("/api/people").json()["rows"][5]
    j = server.KEYS.index("age")
    assert abs(p10["restored"][j] - raw[j]) < 1e-6          # 10 個分數全用＝完整還原
    assert len(client.get("/api/pca/person?i=5&k=3").json()["scores"]) == 3
    assert "error" in client.get("/api/pca/person?i=2000&k=3").json()
    assert "error" in client.get("/api/pca/person?i=0&k=0").json()


def test_cluster_rates_gated(client):
    r = client.get(f"/api/cluster?cols={ALL}&k=3&method=gmm&start=0").json()
    assert "rate_test" not in r["clusters"][0]
    client.post("/api/reveal", json={"seg": "cluster"})
    r = client.get(f"/api/cluster?cols={ALL}&k=3&method=gmm&start=0").json()
    assert [c["rate_test"] for c in r["clusters"]] == [2.7, 7.1, 33.5]


def test_cluster_bad_args(client):
    assert "error" in client.get(f"/api/cluster?cols={ALL}&k=9").json()
    assert "error" in client.get(f"/api/cluster?cols={ALL}&method=dbscan").json()
    assert "error" in client.get(f"/api/cluster?cols={ALL}&start=99").json()


def test_anomaly_hides_test(client):
    r = client.get("/api/anomaly?cols=late30,late90,late60").json()
    assert "test" not in r and r["student"]["n_flag"] == 200


def test_submit_once_and_board(client):
    client.post("/api/phase", json={"phase": "anomaly"})
    assert client.post("/api/anomaly/submit", json={"nickname": "阿德", "cols": ["late90"]}).json()["ok"]
    r = client.post("/api/anomaly/submit", json={"nickname": "阿德", "cols": ["late30"]}).json()
    assert "只能提交一次" in r["error"]
    rows = client.get("/api/board").json()["rows"]
    assert rows[0]["cols"] == ["late90"] and rows[0]["test"] == 5.5      # 鑑別度（2026-11-17 起；原本是 F1 29.16）
    assert client.get("/api/me?nickname=阿德").json()["submitted"] == ["late90"]


def test_submit_needs_nick_and_cols(client):
    assert "暱稱" in client.post("/api/anomaly/submit", json={"nickname": " ", "cols": ["age"]}).json()["error"]
    assert "至少" in client.post("/api/anomaly/submit", json={"nickname": "a", "cols": []}).json()["error"]
    assert "error" in client.post("/api/anomaly/submit", json={"nickname": "a", "cols": ["x"]}).json()


def test_closed_and_revealed_block_submit(client):
    client.post("/api/phase", json={"phase": "closed"})
    assert "截止" in client.post("/api/anomaly/submit", json={"nickname": "b", "cols": ["age"]}).json()["error"]
    client.post("/api/phase", json={"phase": "anomaly", "reopen": True})
    client.post("/api/reveal", json={"seg": "anomaly"})
    assert "揭曉" in client.post("/api/anomaly/submit", json={"nickname": "b", "cols": ["age"]}).json()["error"]
    r = client.get("/api/anomaly/reveal").json()
    assert r["curve"]["best"]["3"] == 12.9 and r["cases"]["defaulters_never_late_pct"] == 32.6


def test_anomaly_reveal_gated(client):
    assert "error" in client.get("/api/anomaly/reveal").json()


def test_vote_flow(client):
    v = client.get("/api/votes").json()
    assert v["question"]["id"] == "pca_where" and v["answer"] is None
    assert client.post("/api/vote", json={"nickname": "a", "qid": "pca_where", "choice": "p1"}).json()["ok"]
    assert client.post("/api/vote", json={"nickname": "a", "qid": "pca_where", "choice": "p0"}).json()["ok"]  # 可改選
    assert client.get("/api/votes").json()["counts"] == {"p0": 1, "p1": 0, "p2": 0, "none": 0}
    assert "error" in client.post("/api/vote", json={"nickname": "a", "qid": "cluster_risk", "choice": "c0"}).json()
    r = client.post("/api/vote/reveal").json()
    assert r["answer"]["answer_id"] == "p0" and "PC1 32.5%" in r["answer"]["answer_text"]
    assert "不能投" in client.post("/api/vote", json={"nickname": "b", "qid": "pca_where", "choice": "p1"}).json()["error"]


def test_vote_answers(client):
    by = {v["id"]: v for v in server.VOTES}
    assert by["cluster_risk"]["answer_id"] == "c2"
    assert by["anomaly_ncols"]["answer_id"] == "n25"


def test_phase_moves_vote(client):
    client.post("/api/phase", json={"phase": "cluster"})
    assert client.get("/api/votes").json()["question"]["id"] == "cluster_risk"
    client.post("/api/phase", json={"phase": "closed"})
    assert client.get("/api/votes").json()["question"]["id"] == "anomaly_ncols"
    assert "error" in client.post("/api/phase", json={"phase": "zzz"}).json()


def test_names(client):
    assert "error" in client.post("/api/name", json={"nickname": "a", "seg": "pca", "names": {"PC9": "x"}}).json()
    assert "error" in client.post("/api/name", json={"nickname": "a", "seg": "pca", "names": {"PC1": "  "}}).json()
    client.post("/api/name", json={"nickname": "a", "seg": "pca", "names": {"PC1": "會不會還錢", "PC2": "家大業大"}})
    client.post("/api/name", json={"nickname": "b", "seg": "pca", "names": {"PC1": "會不會還錢"}})
    s = client.get("/api/names").json()
    assert s["pca"]["PC1"] == [["會不會還錢", 2]] and s["pca_n"] == 2
    assert "error" in client.post("/api/name", json={"nickname": "c", "seg": "cluster", "names": {"第 1 群": "x"}}).json()
    long = client.post("/api/name", json={"nickname": "c", "seg": "pca", "names": {"PC1": "一" * 30}}).json()
    assert len(long["names"]["PC1"]) == server.NAME_MAX


def test_clear_resets(client):
    client.post("/api/labels/toggle")
    client.post("/api/reveal", json={"seg": "cluster"})
    client.post("/api/name", json={"nickname": "a", "seg": "pca", "names": {"PC1": "x"}})
    client.post("/api/clear")
    m = client.get("/api/meta").json()
    assert m["labels"] is False and not any(m["reveal"].values())
    assert client.get("/api/names").json()["pca_n"] == 0


def test_invisible_nick(client):
    client.post("/api/phase", json={"phase": "anomaly"})
    client.post("/api/anomaly/submit", json={"nickname": "小明", "cols": ["age"]})
    r = client.post("/api/anomaly/submit", json={"nickname": "小​明", "cols": ["age"]}).json()
    assert "只能提交一次" in r["error"]


def test_anomaly_routes(client):
    """四條路線（2026-11-17）：學生拿不到考題分數；分群時電腦挑人數最少且有人的那一群；空群不會出錯。"""
    a = client.get("/api/anomaly?cols=late30,late60,late90").json()
    assert "test" not in a and a["student"]["eta"] == 12.6 and a["student"]["n_flag"] == 200
    b = client.get("/api/anomaly?cols=util,age,late30,debt,late90,realestate,late60&pca=2&k=3&method=kmeans").json()
    n = [c["n"] for c in b["clusters"]]
    assert b["pick"] == [2] and b["student"]["n_flag"] == n[2] == min(n) and b["student"]["eta"] == 16.8
    e = client.get("/api/anomaly?cols=late60&k=8&method=gmm").json()
    n = [c["n"] for c in e["clusters"]]
    assert 0 in n and n[e["pick"][0]] == min(x for x in n if x) and e["student"]["eta"] == 0.0
    assert "error" in client.get("/api/anomaly?cols=util,age&pca=3").json()
    assert "error" in client.get("/api/anomaly?cols=util,age&k=9").json()
    assert "error" in client.post("/api/anomaly/submit", json={"nickname": "z", "cols": ["util"]}).json()      # 不在異常偵測段


def test_cluster_score_gated(client):
    assert "score" not in client.get("/api/cluster").json()
    client.post("/api/reveal", json={"seg": "cluster"})
    assert client.get("/api/cluster").json()["score"] == 12.1
    assert client.get("/api/cluster?cols=util,late30,late90,late60&k=8&method=kmeans").json()["score"] == 18.7


def test_vote_stays_locked_after_hide(client):
    """老師揭曉又收起答案：不能改票（2026-11-17）。"""
    client.post("/api/vote", json={"nickname": "a", "qid": "pca_where", "choice": "p1"})
    client.post("/api/vote/reveal", json={"on": True})
    client.post("/api/vote/reveal", json={"on": False})
    v = client.get("/api/votes").json()
    assert v["answer"] is None and v["locked"] is True
    assert "error" in client.post("/api/vote", json={"nickname": "a", "qid": "pca_where", "choice": "p0"}).json()
    assert client.get("/api/votes").json()["counts"]["p1"] == 1


def test_leak_locks_vote(client):
    """單獨公布誰違約、或單獨揭曉某段：那一段的投票就不能再投。"""
    client.post("/api/labels/toggle", json={"on": True})
    assert client.get("/api/votes").json()["locked"] is True
    assert "error" in client.post("/api/vote", json={"nickname": "a", "qid": "pca_where", "choice": "p0"}).json()
    client.post("/api/phase", json={"phase": "cluster"})
    assert client.get("/api/votes").json()["locked"] is False
    client.post("/api/reveal", json={"seg": "cluster", "on": True})
    assert client.get("/api/votes").json()["locked"] is True
    client.post("/api/clear")
    assert client.get("/api/votes").json()["locked"] is False


def test_toggle_with_on_is_idempotent(client):
    """兩個老師分頁同時按：帶 on 的請求送兩次，結果一樣。"""
    for _ in range(2):
        s = client.post("/api/reveal", json={"seg": "pca", "on": True}).json()
    assert s["reveal"]["pca"] is True
    for _ in range(2):
        s = client.post("/api/labels/toggle", json={"on": True}).json()
    assert s["labels"] is True
    assert client.post("/api/labels/toggle").json()["labels"] is False       # 不帶 on＝切換


def test_closed_is_sticky(client):
    """截止後換到別段再回來，仍然截止；明講 reopen 才重開。"""
    client.post("/api/phase", json={"phase": "anomaly"})
    client.post("/api/phase", json={"phase": "closed"})
    client.post("/api/phase", json={"phase": "cluster"})
    s = client.post("/api/phase", json={"phase": "anomaly"}).json()
    assert s["phase"] == "closed" and s["closed"] is True
    assert "截止" in client.post("/api/anomaly/submit", json={"nickname": "b", "cols": ["age"]}).json()["error"]
    s = client.post("/api/phase", json={"phase": "anomaly", "reopen": True}).json()
    assert s["phase"] == "anomaly" and s["closed"] is False
    assert client.post("/api/anomaly/submit", json={"nickname": "b", "cols": ["age"]}).json()["ok"]


def test_board_ties_share_rank(client):
    """同分並列：10 欄不做 PCA 和 10 欄留 10 個分數，結果一樣。"""
    client.post("/api/phase", json={"phase": "anomaly"})
    client.post("/api/anomaly/submit", json={"nickname": "甲", "cols": list(server.KEYS)})
    client.post("/api/anomaly/submit", json={"nickname": "乙", "cols": list(server.KEYS), "pca": 10})
    client.post("/api/anomaly/submit", json={"nickname": "丙", "cols": ["late90"]})
    rows = client.get("/api/board").json()["rows"]
    by = {r["nickname"]: r for r in rows}
    assert by["甲"]["test"] == by["乙"]["test"] and by["甲"]["rank"] == by["乙"]["rank"]
    assert sorted(r["rank"] for r in rows) in ([1, 1, 3], [1, 2, 2])
