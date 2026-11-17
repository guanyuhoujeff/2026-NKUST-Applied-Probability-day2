# -*- coding: utf-8 -*-
"""第二天三段（PCA、分群、異常偵測）共用的資料、切法與前處理。三段一律用這一份，不各自另做。

切法：跟第一天同一行程式 train_test_split(arange(150000), train_size=2000, stratify=y, random_state=4)
  → 學生 2,000 人（違約 134 人）＝第一天同一批；其餘 148,000 人當考題。

前處理（2026-11-14 統一；參數只用學生 2,000 人算，考題的人不參與）：
  1. 三個逾期欄的 96、98 當缺值。這是資料代碼不是次數（全部 269 人、學生資料 6 人）；
     保留的話 PC1 有 56.7% 的平方和來自這 6 人，K-means 會把他們分成獨立一群（facts/FACTS-19）。
  2. 缺值補學生 2,000 人的中位數。
  3. 固定 7 欄取 log1p（LOG_KEYS）：種子 0–9 各抽 2,000 人、偏態 >2 至少 9 次的欄位，
     也等於全部 150,000 人偏態 >2 的欄位。不照「這份樣本的偏態」挑：種子 4 剛好沒抽到額度使用率的極端值
     （偏態 1.24），照樣本挑會漏掉它，考題裡上萬倍的值就會把分數撐爆。
  4. 標準化：減學生 2,000 人的平均、除標準差。
"""
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from features import QUESTIONS, KEYS, TARGET

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "gmsc.csv")
SAMPLE_N = 2000
SAMPLE_SEED = 4
LATE_KEYS = ("late30", "late90", "late60")
CODES = (96, 98)
LOG_KEYS = ("util", "late30", "debt", "income", "late90", "realestate", "late60")


@dataclass(frozen=True)
class Data:
    raw: np.ndarray      # 150,000 × 10 原始值（沒填＝NaN，96/98 保留），畫面顯示用
    Z: np.ndarray        # 150,000 × 10 前處理後（96/98 當缺值）
    Z_keep: np.ndarray   # 對照版：96/98 保留原樣，其餘步驟相同（揭曉用）
    y: np.ndarray
    im: np.ndarray       # 學生 2,000 人的列號
    it: np.ndarray       # 考題 148,000 人的列號
    code_rows: np.ndarray  # 三個逾期欄任一欄是 96/98 的列（bool，150,000）
    fill: dict           # 補缺值用的中位數（原始單位）
    mu: np.ndarray       # 標準化用的平均（取 log 之後的單位；Z 版）
    sd: np.ndarray       # 標準化用的標準差（同上）


def load_csv(path: str = DATA) -> tuple[np.ndarray, np.ndarray]:
    d = pd.read_csv(path)
    assert d.shape == (150000, 11), d.shape
    raw = np.column_stack([d[q["col"]].to_numpy(float) for q in QUESTIONS])
    return raw, d[TARGET].to_numpy(int)


def split(y: np.ndarray, seed: int = SAMPLE_SEED) -> tuple[np.ndarray, np.ndarray]:
    im, it = train_test_split(np.arange(len(y)), train_size=SAMPLE_N, stratify=y, random_state=seed)
    assert not set(im) & set(it) and len(im) + len(it) == len(y), "考題混進學生資料"
    return np.sort(im), np.sort(it)


def code_mask(raw: np.ndarray) -> np.ndarray:
    late = raw[:, [KEYS.index(k) for k in LATE_KEYS]]
    return np.isin(late, CODES).any(axis=1)


def _prepare(raw: np.ndarray, im: np.ndarray, codes_as_missing: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """步驟 1–3（標準化前）。回傳（新陣列, 補值中位數）。不改 raw。"""
    X = raw.copy()
    if codes_as_missing:
        for k in LATE_KEYS:
            j = KEYS.index(k)
            X[np.isin(X[:, j], CODES), j] = np.nan
    fill = np.nanmedian(X[im], axis=0)
    X = np.where(np.isnan(X), fill, X)
    for k in LOG_KEYS:
        j = KEYS.index(k)
        X[:, j] = np.log1p(np.clip(X[:, j], 0, None))
    return X, fill


def _scale(X: np.ndarray, im: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mu, sd = X[im].mean(axis=0), X[im].std(axis=0)
    return mu, np.where(sd == 0, 1.0, sd)


def transform(raw: np.ndarray, im: np.ndarray, codes_as_missing: bool = True) -> tuple[np.ndarray, dict]:
    """回傳（標準化後的新陣列, 補值中位數）。不改 raw。"""
    X, fill = _prepare(raw, im, codes_as_missing)
    mu, sd = _scale(X, im)
    return (X - mu) / sd, dict(zip(KEYS, map(float, fill)))


def unscale(Z: np.ndarray, mu: np.ndarray, sd: np.ndarray, cols=None) -> np.ndarray:
    """標準化後的值 → 原始單位（取 log 的欄還原回來）。十欄都不會是負的，還原出負值就當 0。
    cols＝Z 各欄對應的欄號，預設十欄全部。"""
    cols = list(range(len(KEYS))) if cols is None else list(cols)
    X = np.clip(Z * sd[cols] + mu[cols], 0, None)
    for c, j in enumerate(cols):
        if KEYS[j] in LOG_KEYS:
            X[:, c] = np.expm1(X[:, c])
    return X


def load(path: str = DATA) -> Data:
    raw, y = load_csv(path)
    im, it = split(y)
    X, fill = _prepare(raw, im, codes_as_missing=True)
    mu, sd = _scale(X, im)
    Z_keep, _ = transform(raw, im, codes_as_missing=False)
    return Data(raw=raw, Z=(X - mu) / sd, Z_keep=Z_keep, y=y, im=im, it=it, code_rows=code_mask(raw),
                fill=dict(zip(KEYS, map(float, fill))), mu=mu, sd=sd)


def cols_index(keys) -> list[int]:
    """題目 key → 欄號（照 KEYS 順序，去重）；有不認得的 key 就報錯。"""
    bad = set(keys) - set(KEYS)
    if bad:
        raise ValueError(f"不認得的欄位：{sorted(bad)}")
    return [KEYS.index(k) for k in KEYS if k in set(keys)]
