# -*- coding: utf-8 -*-
"""應用機率・第二天：非監督式學習（PCA → 分群 → 異常偵測）課堂互動後端（FastAPI + WebSocket）。

骨架改自第一天 app/backend/server.py。啟動：python server.py（:52014）。前端 build 後放 ../frontend/dist。
資料、切法、前處理：prep.py（三段共用一份）。

老師頁控制：
  phase    pca／cluster／anomaly／closed（closed＝異常偵測截止提交；截止過就一直截止，明講 reopen 才重開）
  step     每段第幾步；學生手機跟著跳
  labels   違約者的顏色開關（非監督先不看答案；老師開了，手機上的點才分顏色）
  投票     每段一題，換段就換題。答案揭曉過、或那一段的答案露出來過，就不能再投（_locked）
  reveal   每段的揭曉：pca＝各主成分高分端的違約比例；cluster＝每群的違約比例與鑑別度；
           anomaly＝排行榜（考題的鑑別度，同分並列）、欄位數曲線、「異常≠違約」
  開關類的請求可以帶 on（設成開或關），兩個老師分頁同時按也不會開了又關。
取名：只有 PCA 段替 PC1、PC2 取名。老師頁看全班取的名字。
抓異常提交：每個暱稱一次（欄位、要不要 PCA、要不要分群）；截止、揭曉後不收。清除會把輪次 +1（同第一天）。
"""
import asyncio
import hmac
import json
import os
import re
import threading
import time

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import anomaly_seg
import cluster_seg
import pca_seg
import prep
from features import QUESTIONS, KEYS

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "52014"))
BOOT = format(int(time.time()), "x")      # 這次啟動的代號；配上清除的次數，學生頁用來判斷「手機上存的東西是不是上一輪的」

# ===== 資料 =====
DATA = prep.load()
for _m in (pca_seg, cluster_seg, anomaly_seg):
    _m.load(DATA)
SAMPLE_N = len(DATA.im)
SAMPLE_K = int(DATA.y[DATA.im].sum())
TEST_N = len(DATA.it)
TEST_K = int(DATA.y[DATA.it].sum())
ALL = tuple(range(len(KEYS)))
# 用位置參數呼叫：lru_cache 把關鍵字參數和位置參數當成不同的 key，請求進來走的是位置參數（先前用 ** 等於沒預先算到）
_C = cluster_seg.CLASS_CFG
CLASS_CLUSTER = cluster_seg.fit(_C["cols"], _C["k"], _C["method"], _C["start"])
for _m in cluster_seg.METHODS:          # 分群第 1 步全班會一起點的那幾份（換方法、換起點）也先算好
    for _s in cluster_seg.STARTS:
        cluster_seg.fit(_C["cols"], _C["k"], _m, _s)
PCA_ALL = pca_seg.fit(ALL)
DEMO2 = pca_seg.demo2()
SIZE_CURVE = anomaly_seg.size_curve()       # 約 5 秒；揭曉用
CASES = anomaly_seg.cases()
PEOPLE = [[None if v != v else float(v) for v in row] for row in DATA.raw[DATA.im]]   # 2,000 人原始值（NaN→None）
LABELS = DATA.y[DATA.im].tolist()

SEGMENTS = ("pca", "cluster", "anomaly")
NAME_SLOTS = {"pca": ["PC1", "PC2"]}     # 只有 PCA 取名字；分群的取名 2026-11-16 拿掉（跟 PCA 重複）
NAME_MAX = 12
STEP_MAX = {"pca": 4, "cluster": 3, "anomaly": 3}   # 每段老師可以帶學生跳的步數（學生頁的分頁；「自己試」不算）

# 參考名字：老師按「看幾個例子」後才給。概念＝照權重／各群特徵讀出來的一句話；名字是讀完自己取的，不是文獻上的名稱。
# 寫法（2026-11-16 三方審查後定）：只描述畫面上看得到的欄位，不寫評價（吃緊、困難、良好）也不寫資料沒有的東西（支出）；
# PC 是一把尺，用「分數越高：越…」；群是一批人，用「多數…」；只有 PCA 有（分群不取名）。
# 文字是照預設結果寫的，所以先核對結果沒變（PC 的最大權重欄、各群人數）；對不上就不給，免得文字和圖不合。
_REF_TEXT = {
    "pca": {
        "PC1": {"concept": "分數越高：額度用得越多、逾期越多次、年紀越輕",
                "names": ["額度用滿又常逾期", "年輕、用滿、常逾期", "逾期多、往來少"]},
        "PC2": {"concept": "分數越高：房貸和借款筆數越多、收入越高、要扶養的人越多，也帶一點短期逾期",
                "names": ["借款多、收入高", "有房貸、要養家", "筆數多、偶爾逾期"]},
    },
}


def _ref_ok(seg: str) -> bool:
    top = [max(w, key=lambda k: abs(w[k])) for w in PCA_ALL["loadings"][:2]]
    return top == ["util", "realestate"] and all(w[t] > 0 for w, t in zip(PCA_ALL["loadings"], top))


# 分群段的圖用 PCA 的分數當座標：每個軸給一個名字和一句概念，免得只看到「PC1、PC2」。
# PC1、PC2 沿用上面的參考名字（三個 agent 審過的那一套）；PC3 是 2026-11-17 照權重補的（負債比 +0.58、扶養人數 −0.49、年齡 +0.35），沒有另外審。
_PC_AXES = [
    {"key": "util", "short": _REF_TEXT["pca"]["PC1"]["names"][0], "concept": _REF_TEXT["pca"]["PC1"]["concept"]},
    {"key": "realestate", "short": _REF_TEXT["pca"]["PC2"]["names"][0], "concept": _REF_TEXT["pca"]["PC2"]["concept"]},
    {"key": "debt", "short": "負債比高、扶養少", "concept": "分數越高：負債比越高、要扶養的人越少、年紀越大"},
]


def _pc_axes() -> list:
    """權重最大的那一欄對得上、方向為正，才給名字；資料或前處理變了就整組不給（畫面退回只寫 PC1、PC2、PC3）。"""
    ws = PCA_ALL["loadings"][:3]
    ok = all(max(w, key=lambda k: abs(w[k])) == a["key"] and w[a["key"]] > 0 for w, a in zip(ws, _PC_AXES))
    return [{"short": a["short"], "concept": a["concept"]} for a in _PC_AXES] if ok else []


NAME_REFS = {seg: (_REF_TEXT[seg] if _ref_ok(seg) else {}) for seg in _REF_TEXT}


def _pct(x):
    return round(x * 100)


# 每段一題投票。答案用上面算好的數字，不手寫。
_byPC = pca_seg.by_pc_default()
_base = round(float(DATA.y[DATA.im].mean()) * 100, 1)
VOTES = [
    {"id": "pca_where", "seg": "pca", "question": "公布誰違約之後，違約的人會集中在哪裡？",
     "options": [{"id": f"p{j}", "text": f"{b['pc']} 分數高的那頭"} for j, b in enumerate(_byPC)]
                + [{"id": "none", "text": "散在各處，沒有規律"}],
     "answer_id": "p" + str(max(range(len(_byPC)), key=lambda j: _byPC[j]["top10"])),
     "answer_text": "各主成分分數最高的 10% 人，違約比例：" + "、".join(f"{b['pc']} {b['top10']}%" for b in _byPC)
                    + f"（全部 {_base}%）"},
    {"id": "cluster_risk", "seg": "cluster", "question": "全班這一份分群，哪一群最會違約？",
     "options": [{"id": f"c{i}", "text": f"第 {i + 1} 群（{c['n']:,} 人）"} for i, c in enumerate(CLASS_CLUSTER["clusters"])],
     "answer_id": "c" + str(max(range(CLASS_CLUSTER["k"]), key=lambda i: CLASS_CLUSTER["clusters"][i]["rate_test"])),
     "answer_text": "　".join(f"第 {i + 1} 群 {c['rate_test']}%" for i, c in enumerate(CLASS_CLUSTER["clusters"])) + "（考題 148,000 人）"},
    {"id": "anomaly_ncols", "seg": "anomaly", "question": "抓異常（最少見的 10%），挑幾個欄位，鑑別度最高？",
     "options": [{"id": "n1", "text": "只挑 1 欄最高"}, {"id": "n25", "text": "挑 2–5 欄最高"},
                 {"id": "n69", "text": "挑 6–9 欄最高"}, {"id": "n10", "text": "10 欄全用最高"}],
     "answer_id": {1: "n1", 10: "n10"}.get(max(SIZE_CURVE["best"], key=SIZE_CURVE["best"].get),
                                            "n25" if max(SIZE_CURVE["best"], key=SIZE_CURVE["best"].get) <= 5 else "n69"),
     "answer_text": "每種欄位數最高的鑑別度（考題）：" + "、".join(f"{k} 欄 {v}" for k, v in SIZE_CURVE["best"].items())},
]
VOTE_BY_ID = {v["id"]: v for v in VOTES}


# ===== 狀態（單程序記憶體）=====
_lock = threading.Lock()
_state = {"phase": "pca", "labels": False, "vote_idx": 0, "vote_revealed": False, "round": 0, "closed": False,
          "reveal": {s: False for s in SEGMENTS}, "name_ref": {s: False for s in NAME_SLOTS}, "step": {s: 1 for s in SEGMENTS}}
_votes = {}      # vote id -> {nick -> option id}
_shown = set()   # 答案現在是揭曉狀態的投票
_locked = set()  # 不能再投的投票：答案揭曉過、或這一段的答案已經露出來過（公布誰違約、揭曉某段）。老師收起答案也不會重開，清除才重開
_names = {s: {} for s in NAME_SLOTS}    # seg -> {nick -> {slot -> name}}
_board = {}      # nick -> 異常偵測提交

_INVISIBLE = re.compile(r"[​-‏ -‮⁠-⁯﻿\x00-\x1f\x7f]")


# ===== 老師頁密碼 =====
# 老師端的操作（切段、切步、揭曉、清除）和排行榜、全班取名，都要帶密碼。學生頁不受影響。
# 預設不設密碼（使用者 2026-11-17 決定不加）。之後想加：設環境變數 DAY2_TEACHER_KEY，或放一個 backend/teacher_key.txt（不進 repo）再重啟。
def _load_teacher_key() -> str:
    k = os.environ.get("DAY2_TEACHER_KEY", "").strip()
    if not k:
        try:
            k = open(os.path.join(HERE, "teacher_key.txt"), encoding="utf-8").read().strip()
        except OSError:
            k = ""
    return k


TEACHER_KEY = _load_teacher_key()


def key_ok(key) -> bool:
    return not TEACHER_KEY or (isinstance(key, str) and hmac.compare_digest(key.encode(), TEACHER_KEY.encode()))


def teacher_only(x_teacher_key: str = Header(default="")):
    if not key_ok(x_teacher_key):
        raise HTTPException(status_code=401, detail="需要老師頁密碼")


def clean_nick(s: str) -> str:
    return _INVISIBLE.sub("", s).strip()[:20]


def clean_name(s: str) -> str:
    return _INVISIBLE.sub("", s).strip()[:NAME_MAX]


def public_state():
    return {"phase": _state["phase"], "labels": _state["labels"], "vote_idx": _state["vote_idx"],
            "vote_revealed": _state["vote_revealed"], "reveal": dict(_state["reveal"]),
            "name_ref": dict(_state["name_ref"]), "step": dict(_state["step"]),
            "n_submitted": len(_board), "closed": _state["closed"], "epoch": f"{BOOT}-{_state['round']}"}


def public_vote(v):
    return {k: v[k] for k in ("id", "seg", "question", "options")}


def vote_tally():
    v = VOTES[_state["vote_idx"]]
    with _lock:
        c = {o["id"]: 0 for o in v["options"]}
        for ch in _votes.get(v["id"], {}).values():
            if ch in c:
                c[ch] += 1
    ans = {"answer_id": v["answer_id"], "answer_text": v["answer_text"]} if _state["vote_revealed"] else None
    return {"idx": _state["vote_idx"], "n_questions": len(VOTES), "question": public_vote(v),
            "counts": c, "total": sum(c.values()), "answer": ans, "locked": v["id"] in _locked}


def names_summary():
    """老師頁：每個位置，全班取的名字由多到少。"""
    out = {}
    with _lock:
        for seg, slots in NAME_SLOTS.items():
            out[seg] = {}
            for slot in slots:
                cnt = {}
                for d in _names[seg].values():
                    if d.get(slot):
                        cnt[d[slot]] = cnt.get(d[slot], 0) + 1
                out[seg][slot] = sorted(cnt.items(), key=lambda x: (-x[1], x[0]))
            out[seg + "_n"] = len(_names[seg])
    return out


def board_rows():
    with _lock:
        rows = [{"nickname": n, "cols": r["cols"], "n_cols": len(r["cols"]),
                 "pca_k": r.get("pca_k", 0), "k": r.get("k", 0), "method": r.get("method", ""), "pick": r.get("pick", []),
                 "test_n_flag": r["test"]["n_flag"],
                 "student": r["student"]["eta"], "test": r["test"]["eta"], "test_lift": r["test"]["lift"],
                 "test_rate_flag": r["test"]["rate_flag"], "test_rate_rest": r["test"]["rate_rest"],
                 "test_tp": r["test"]["tp"], "test_recall": r["test"]["recall"], "test_precision": r["test"]["precision"]}
                for n, r in _board.items()]
    rows = sorted(rows, key=lambda x: (-x["test"], x["nickname"]))
    for r in rows:      # 同分並列：名次＝分數比他高的人數＋1（1、1、3…）；分數本來就只到小數 1 位
        r["rank"] = 1 + sum(o["test"] > r["test"] for o in rows)
    return rows


# ===== WebSocket =====
SEND_TIMEOUT = 2.0


class Manager:
    """conns: ws -> role（student／teacher）。排行榜與全班取名只送老師端。"""
    def __init__(self):
        self.conns = {}

    async def connect(self, ws, role):
        await ws.accept()
        self.conns[ws] = role

    def disconnect(self, ws):
        self.conns.pop(ws, None)

    async def _send(self, ws, msg):
        try:
            await asyncio.wait_for(ws.send_json(msg), SEND_TIMEOUT)
        except Exception:
            self.disconnect(ws)

    async def broadcast(self, msg, role=None):
        targets = [ws for ws, r in list(self.conns.items()) if not role or r == role]
        await asyncio.gather(*(self._send(ws, msg) for ws in targets))


manager = Manager()


async def push_state():
    await manager.broadcast({"type": "state", **public_state()})


async def push_votes():
    await manager.broadcast({"type": "votes", **vote_tally()})


async def push_names():
    await manager.broadcast({"type": "names", **names_summary()}, role="teacher")


async def push_board():
    await manager.broadcast({"type": "board", "rows": board_rows(), "revealed": _state["reveal"]["anomaly"]}, role="teacher")


# ===== API：讀 =====
app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)      # 手機開頁約 418 KB，壓過約 139 KB

# 重運算（分群、抓異常）：同時最多算 HEAVY_MAX 個；同一組設定同時進來只算一次。
# 實測（FACTS-30）：50 人同一瞬間送最重的設定，不限制時每人等約 8 秒（執行緒互搶 GIL），限 4 個約 3.8 秒，同一組只算一次約 1 秒。
HEAVY_MAX = 4
_heavy_sem = None
_inflight = {}


async def heavy(fn, *args):
    global _heavy_sem
    if _heavy_sem is None:
        _heavy_sem = asyncio.Semaphore(HEAVY_MAX)
    key = (fn.__name__, args)
    task = _inflight.get(key)
    if task is None:
        async def _run():
            async with _heavy_sem:
                return await asyncio.to_thread(fn, *args)
        task = asyncio.ensure_future(_run())
        _inflight[key] = task
        task.add_done_callback(lambda _t: _inflight.pop(key, None))
    return await asyncio.shield(task)



def parse_cols(cols: str):
    keys = [k for k in cols.split(",") if k]
    try:
        idx = tuple(prep.cols_index(keys))
    except ValueError as e:
        return None, str(e)
    if not idx:
        return None, "至少挑一欄"
    return idx, None


@app.get("/api/meta")
def meta():
    return {"questions": QUESTIONS, "keys": KEYS, "sample_n": SAMPLE_N, "sample_k": SAMPLE_K,
            "test_n": TEST_N, "test_k": TEST_K, "n_codes_student": int(DATA.code_rows[DATA.im].sum()),
            "fill": DATA.fill, "log_keys": list(prep.LOG_KEYS),
            "cluster": {"ks": list(cluster_seg.KS), "methods": list(cluster_seg.METHODS), "starts": list(cluster_seg.STARTS),
                        "class_cfg": {**cluster_seg.CLASS_CFG, "cols": [KEYS[c] for c in cluster_seg.CLASS_CFG["cols"]]},
                        "ambiguous": cluster_seg.AMBIGUOUS, "min_n": cluster_seg.MIN_N, "pc_axes": _pc_axes()},
            "anomaly": {"q": anomaly_seg.Q, "n_flag_student": int(round(anomaly_seg.Q * SAMPLE_N)),
                        "n_flag_test": int(round(anomaly_seg.Q * TEST_N))},
            "name_slots": NAME_SLOTS, "name_max": NAME_MAX,
            "votes": [public_vote(v) for v in VOTES], **public_state()}


@app.get("/api/people")
def people():
    """學生 2,000 人的十欄原始值（點 3D 圖上的人看細節）。不含違約答案。"""
    return {"keys": KEYS, "rows": PEOPLE}


@app.get("/api/labels")
def labels():
    """老師開了「顯示違約」才給。"""
    if not _state["labels"]:
        return {"error": "老師還沒公布誰違約"}
    return {"labels": LABELS}


@app.get("/api/pca")
def pca(cols: str = ",".join(KEYS), keep_codes: bool = False):
    idx, err = parse_cols(cols)
    if err:
        return {"error": err}
    return pca_seg.fit(idx, bool(keep_codes))


@app.get("/api/pca/demo")
def pca_demo():
    """第 1 步的兩欄示範；附 96/98 對照（PC1 的資訊比例）。"""
    keep = pca_seg.fit(ALL, True)
    return {**DEMO2, "n_codes_student": int(DATA.code_rows[DATA.im].sum()), "ev1": PCA_ALL["ev"][0], "keep_ev1": keep["ev"][0]}


@app.get("/api/pca/person")
def pca_person(i: int, k: int = 3):
    """第 2 步：十欄全用，某人用前 k 個分數還原。"""
    if not 0 <= i < SAMPLE_N or not 1 <= k <= len(KEYS):
        return {"error": "人或分數個數不對"}
    return pca_seg.person(i, k)


@app.get("/api/pca/reveal")
def pca_reveal():
    """揭曉：各主成分分數高低兩半、最高 10% 的違約比例。"""
    if not _state["reveal"]["pca"]:
        return {"error": "老師還沒揭曉"}
    return {"by_pc": _byPC, "base": _base}


@app.get("/api/cluster")
async def cluster(cols: str = ",".join(KEYS), k: int = 3, method: str = "gmm", start: int = 0):
    idx, err = parse_cols(cols)
    if err:
        return {"error": err}
    if k not in cluster_seg.KS or method not in cluster_seg.METHODS or start not in cluster_seg.STARTS:
        return {"error": "群數、方法或起點不對"}
    res = await heavy(cluster_seg.fit, idx, k, method, start)
    return res if _state["reveal"]["cluster"] else cluster_seg.strip_answers(res)


def parse_route(idx: tuple, pca: int, k: int, method: str) -> tuple:
    """檢查路線設定。回傳 ((pca_k, k, method), None) 或 (None, 錯誤訊息)。"""
    if pca < 0 or pca > len(idx):
        return None, "PCA 留的分數要在 1 到挑的欄位數之間"
    if k and (k not in cluster_seg.KS or method not in cluster_seg.METHODS):
        return None, "群數或方法不對"
    return (pca, k, method if k else "kmeans"), None


@app.get("/api/anomaly")
async def anomaly(cols: str, pca: int = 0, k: int = 0, method: str = "kmeans"):
    idx, err = parse_cols(cols)
    if err:
        return {"error": err}
    route, err = parse_route(idx, pca, k, method)
    if err:
        return {"error": err}
    res = await heavy(anomaly_seg.run, idx, *route)
    return anomaly_seg.public(res)


@app.get("/api/anomaly/reveal")
def anomaly_reveal():
    if not _state["reveal"]["anomaly"]:
        return {"error": "老師還沒揭曉"}
    return {"curve": SIZE_CURVE, "cases": CASES, "rows": board_rows()}


@app.get("/api/votes")
def votes():
    return vote_tally()


@app.get("/api/me")
def me(nickname: str):
    nick = clean_nick(nickname)
    with _lock:
        return {"votes": {vid: d[nick] for vid, d in _votes.items() if nick in d},
                "names": {seg: d.get(nick, {}) for seg, d in _names.items()},
                "submitted": _board.get(nick, {}).get("cols")}


@app.get("/api/names", dependencies=[Depends(teacher_only)])
def names():
    return names_summary()


@app.get("/api/name_ref")
def name_ref(seg: str):
    """參考名字：老師公布後才回傳。"""
    if seg not in NAME_SLOTS:
        return {"error": "段落不對"}
    if not _state["name_ref"][seg]:
        return {"error": "還沒公布"}
    return {"seg": seg, "refs": NAME_REFS[seg]}


@app.get("/api/board", dependencies=[Depends(teacher_only)])
def board():
    return {"rows": board_rows(), **public_state()}


# ===== API：學生寫入 =====
class VoteReq(BaseModel):
    nickname: str
    qid: str
    choice: str


class NameReq(BaseModel):
    nickname: str
    seg: str
    names: dict[str, str]


class KeyReq(BaseModel):
    key: str = ""


@app.post("/api/teacher/login")
def teacher_login(req: KeyReq):
    """老師頁登入：密碼對不對。needed＝這台伺服器有沒有設密碼。"""
    return {"ok": key_ok(req.key), "needed": bool(TEACHER_KEY)}


class SubmitReq(BaseModel):
    nickname: str
    cols: list[str]
    pca: int = 0            # PCA 留前幾個分數；0＝不做 PCA
    k: int = 0              # 分幾群；0＝不分群（標最異常的 10%）
    method: str = "kmeans"


@app.post("/api/vote")
async def vote(req: VoteReq):
    nick = clean_nick(req.nickname)
    if not nick:
        return {"error": "先填暱稱"}
    v = VOTES[_state["vote_idx"]]
    if req.qid != v["id"]:
        return {"error": "老師已經換題了"}
    if _state["vote_revealed"] or v["id"] in _locked:
        return {"error": "這題已經不能投了"}
    if req.choice not in {o["id"] for o in v["options"]}:
        return {"error": "選項不對"}
    with _lock:
        _votes.setdefault(v["id"], {})[nick] = req.choice
    await push_votes()
    return {"ok": True}


@app.post("/api/name")
async def name(req: NameReq):
    nick = clean_nick(req.nickname)
    if not nick:
        return {"error": "先填暱稱"}
    if req.seg not in NAME_SLOTS:
        return {"error": "段落不對"}
    if set(req.names) - set(NAME_SLOTS[req.seg]):
        return {"error": "位置不對"}
    clean = {k: clean_name(v) for k, v in req.names.items() if clean_name(v)}
    if not clean:
        return {"error": "至少取一個名字"}
    with _lock:
        _names[req.seg][nick] = clean
    await push_names()
    return {"ok": True, "names": clean}


def submit_closed():
    if _state["phase"] == "closed":
        return "已經截止提交"
    if _state["reveal"]["anomaly"]:
        return "排行榜已經揭曉，不能再提交"
    return None


@app.post("/api/anomaly/submit")
async def anomaly_submit(req: SubmitReq):
    nick = clean_nick(req.nickname)
    if not nick:
        return {"error": "提交要先填暱稱"}
    try:
        idx = tuple(prep.cols_index(req.cols))
    except ValueError as e:
        return {"error": str(e)}
    if not idx:
        return {"error": "至少挑一欄"}
    if err := submit_closed():
        return {"error": err}
    route, err = parse_route(idx, req.pca, req.k, req.method)
    if err:
        return {"error": err}
    if _state["phase"] != "anomaly":
        return {"error": "現在不是抓異常的時間"}
    rnd = _state["round"]
    res = await heavy(anomaly_seg.run, idx, *route)
    with _lock:
        if err := submit_closed() or (rnd != _state["round"] and "老師剛清除資料，請重新提交"):
            return {"error": err}
        if nick in _board:
            return {"error": "這個暱稱已經提交過了（每人只能提交一次）"}
        _board[nick] = res
    await push_state()
    await push_board()
    return {"ok": True, "cols": res["cols"]}


# ===== API：老師 =====
class PhaseReq(BaseModel):
    phase: str
    reopen: bool = False     # 截止後要重新開放提交，必須明講（老師頁會先問一次）


class OnReq(BaseModel):
    on: bool | None = None   # 開關類的鈕：帶 on 就是「設成這樣」（兩個老師分頁同時按也不會開了又關）；不帶＝切換


def lock_vote(seg: str):
    """這一段的答案露出來了：那一題不能再投。"""
    for v in VOTES:
        if v["seg"] == seg:
            _locked.add(v["id"])


class SegReq(BaseModel):
    seg: str
    on: bool | None = None


@app.post("/api/phase", dependencies=[Depends(teacher_only)])
async def set_phase(req: PhaseReq):
    if req.phase not in SEGMENTS + ("closed",):
        return {"error": "phase 不對"}
    phase = req.phase
    if phase == "closed":
        _state["closed"] = True
    elif phase == "anomaly":
        if req.reopen:
            _state["closed"] = False
        elif _state["closed"]:
            phase = "closed"      # 截止過：回到這一段（例如按上一題再按下一題）仍然是截止，不會悄悄重開
    _state["phase"] = phase
    seg = "anomaly" if phase == "closed" else phase
    first = next(i for i, v in enumerate(VOTES) if v["seg"] == seg)   # 換段時投票跟著跳到那一段的題
    if VOTES[_state["vote_idx"]]["seg"] != seg:
        _state["vote_idx"], _state["vote_revealed"] = first, first in {i for i, v in enumerate(VOTES) if v["id"] in _shown}
        await push_votes()
    await push_state()
    return public_state()


@app.post("/api/labels/toggle", dependencies=[Depends(teacher_only)])
async def labels_toggle(req: OnReq | None = None):
    _state["labels"] = (not _state["labels"]) if req is None or req.on is None else req.on
    if _state["labels"]:
        if _state["phase"] in ("pca", "cluster"):     # 圖上看得到誰違約＝這一段的投票答案露出來了
            lock_vote(_state["phase"])
            await push_votes()
        await manager.broadcast({"type": "labels", "labels": LABELS})
    await push_state()
    return public_state()


@app.post("/api/vote/reveal", dependencies=[Depends(teacher_only)])
async def vote_reveal(req: OnReq | None = None):
    _state["vote_revealed"] = (not _state["vote_revealed"]) if req is None or req.on is None else req.on
    vid = VOTES[_state["vote_idx"]]["id"]
    if _state["vote_revealed"]:
        _shown.add(vid)
        _locked.add(vid)
    else:
        _shown.discard(vid)
    await push_votes()
    await push_state()
    return vote_tally()


@app.post("/api/reveal", dependencies=[Depends(teacher_only)])
async def reveal(req: SegReq):
    if req.seg not in SEGMENTS:
        return {"error": "段落不對"}
    _state["reveal"][req.seg] = (not _state["reveal"][req.seg]) if req.on is None else req.on
    if _state["reveal"][req.seg]:
        lock_vote(req.seg)
        await push_votes()
    await push_state()
    if req.seg == "anomaly":
        await push_board()
    return public_state()


@app.post("/api/name_ref", dependencies=[Depends(teacher_only)])
async def name_ref_toggle(req: SegReq):
    if req.seg not in NAME_SLOTS:
        return {"error": "段落不對"}
    _state["name_ref"][req.seg] = (not _state["name_ref"][req.seg]) if req.on is None else req.on
    await push_state()
    return public_state()


class StepReq(BaseModel):
    seg: str
    step: int


@app.post("/api/step", dependencies=[Depends(teacher_only)])
async def set_step(req: StepReq):
    """老師頁切到某一步：學生手機的分頁跟著跳。"""
    if req.seg not in SEGMENTS:
        return {"error": "段落不對"}
    if not 1 <= req.step <= STEP_MAX[req.seg]:
        return {"error": f"步數只能是 1–{STEP_MAX[req.seg]}"}
    _state["step"][req.seg] = req.step
    await push_state()
    return public_state()


@app.post("/api/clear", dependencies=[Depends(teacher_only)])
async def clear():
    with _lock:
        n = len(_board)
        _board.clear()
        _votes.clear()
        _shown.clear()
        _locked.clear()
        for d in _names.values():
            d.clear()
        _state.update(phase="pca", closed=False, labels=False, vote_idx=0, vote_revealed=False, round=_state["round"] + 1,
                      reveal={s: False for s in SEGMENTS}, name_ref={s: False for s in NAME_SLOTS}, step={s: 1 for s in SEGMENTS})
    await manager.broadcast({"type": "cleared"})
    await push_state()
    await push_votes()
    await push_names()
    await push_board()
    return {"cleared": n}


@app.websocket("/ws")
async def ws(ws: WebSocket):
    # 一律先當學生連進來；老師頁連上後送 {"type":"auth","key":...}，密碼對了才升成老師（才收得到排行榜與全班取名）
    await manager.connect(ws, "student")
    try:
        await ws.send_json({"type": "state", **public_state()})
        while True:
            txt = await ws.receive_text()
            if manager.conns.get(ws) != "teacher" and len(txt) < 300 and '"auth"' in txt:
                try:
                    msg = json.loads(txt)
                except ValueError:
                    continue
                if isinstance(msg, dict) and msg.get("type") == "auth" and key_ok(msg.get("key")):
                    manager.conns[ws] = "teacher"
                    await ws.send_json({"type": "auth", "ok": True})
    except WebSocketDisconnect:
        manager.disconnect(ws)


_DIST = os.path.join(HERE, "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
