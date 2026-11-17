# -*- coding: utf-8 -*-
"""十個欄位：Give Me Some Credit（Kaggle 2011，Credit Fusion）的十個原始欄位，題目文字與第一天相同。

欄位定義照 Kaggle Data Dictionary.xls。第二天的前處理見 prep.py（96/98 當缺值、補中位數、7 欄取 log、標準化）。

每欄：
  key       程式用的名字
  col       原始欄名
  question  手機上顯示的問題
  short     短名（圖、卡片用）
  kind      pct＝比例（畫面寫 %）／money＝金額／age＝歲／count＝次數（unit 為單位）
  note      說明
"""
import math

TARGET = "SeriousDlqin2yrs"

QUESTIONS = [
    {"key": "util", "col": "RevolvingUtilizationOfUnsecuredLines", "question": "信用卡和信用貸款，欠款是額度的幾 %？",
     "short": "額度使用率", "kind": "pct",
     "note": "信用卡、信用貸款現在欠的錢，除以額度上限；不含房貸、車貸。多數人在 0–100%，少數人超過 100%（欠得比額度還多）"},
    {"key": "age", "col": "age", "question": "幾歲？", "short": "年齡", "kind": "age",
     "note": "借款人的年齡。資料裡有 1 人是 0 歲，原始資料就是這樣"},
    {"key": "late30", "col": "NumberOfTime30-59DaysPastDueNotWorse", "question": "過去 2 年，逾期 30–59 天的次數？",
     "short": "逾期30–59天", "kind": "count", "unit": "次",
     "note": "繳款晚了 30–59 天、但沒拖更久的次數。全部 15 萬人裡有 269 人填 96 或 98，原始資料沒說明，像是特殊代碼；第二天一律當「沒填」"},
    {"key": "debt", "col": "DebtRatio", "question": "負債比是幾 %？", "short": "負債比", "kind": "pct",
     "note": "每月要付的債務、贍養費、生活費，除以稅前月收入。沒填收入的人，這一欄常是很大的數字，原始資料沒說明"},
    {"key": "income", "col": "MonthlyIncome", "question": "月收入多少？", "short": "月收入", "kind": "money",
     "note": "每月收入，原始資料沒寫幣別。約 2 成的人沒填，畫面上寫「沒填」"},
    {"key": "nloans", "col": "NumberOfOpenCreditLinesAndLoans", "question": "現在有幾筆借款和信用卡？",
     "short": "借款筆數", "kind": "count", "unit": "筆",
     "note": "車貸、房貸這類分期借款，加上信用卡這類信用額度，一共幾筆"},
    {"key": "late90", "col": "NumberOfTimes90DaysLate", "question": "逾期 90 天以上的次數？",
     "short": "逾期90天以上", "kind": "count", "unit": "次",
     "note": "繳款晚了 90 天以上的次數；原始說明沒寫是過去多久。96、98 同「逾期 30–59 天」那題"},
    {"key": "realestate", "col": "NumberRealEstateLoansOrLines", "question": "有幾筆房貸或房屋抵押借款？",
     "short": "房貸筆數", "kind": "count", "unit": "筆",
     "note": "房貸，加上用房子抵押的信用額度，一共幾筆"},
    {"key": "late60", "col": "NumberOfTime60-89DaysPastDueNotWorse", "question": "過去 2 年，逾期 60–89 天的次數？",
     "short": "逾期60–89天", "kind": "count", "unit": "次",
     "note": "繳款晚了 60–89 天、但沒拖更久的次數。96、98 同「逾期 30–59 天」那題"},
    {"key": "dep", "col": "NumberOfDependents", "question": "要扶養幾個人？", "short": "扶養人數", "kind": "count",
     "unit": "人", "note": "家裡要養的人，不含自己（配偶、小孩等）。少數人沒填，畫面上寫「沒填」"},
]
KEYS = [q["key"] for q in QUESTIONS]
BY_KEY = {q["key"]: q for q in QUESTIONS}
SHORT = {q["key"]: q["short"] for q in QUESTIONS}


def fmt_value(key: str, v: float) -> str:
    """原始值寫成畫面上的字：沒填、百分比、金額、歲、次數。"""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "沒填"
    q = BY_KEY[key]
    if q["kind"] == "pct":
        return f"{v * 100:,.0f}%"
    if q["kind"] == "money":
        return f"{v:,.0f}"
    if q["kind"] == "age":
        return f"{v:.0f} 歲"
    return f"{v:.0f} {q['unit']}"
