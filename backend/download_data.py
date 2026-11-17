# -*- coding: utf-8 -*-
"""下載資料：Give Me Some Credit（Kaggle 2011，Credit Fusion）訓練檔，存成 data/gmsc.csv。

資料不放在這個 repo（Kaggle 頁面寫授權依比賽規則），改從 OpenML 46929 下載：
  https://www.openml.org/d/46929 （TabArena 整理的 Kaggle 訓練檔，150,000 人）
目標欄 FinancialDistressNextTwoYears（Yes／No）改回 Kaggle 原名 SeriousDlqin2yrs（1／0），其餘欄位照原樣。
列的順序不能動：學生的 2,000 人是照列號抽的（scoring.SAMPLE_SEED）。

用法：python download_data.py            # 已經有檔就不重抓
      python download_data.py --force    # 重抓並覆蓋
"""
import os
import sys
from sklearn.datasets import fetch_openml

OPENML_ID = 46929
OPENML_TARGET = "FinancialDistressNextTwoYears"
TARGET = "SeriousDlqin2yrs"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "gmsc.csv")
EXPECT = {"shape": (150000, 11), "default": 10026, "income_na": 29731, "dep_na": 3924}


def download():
    """回傳跟 Kaggle 訓練檔同欄名的表；筆數、違約數、缺值數對不上就報錯。"""
    d = fetch_openml(data_id=OPENML_ID, as_frame=True, parser="auto").frame
    y = d[OPENML_TARGET].map({"Yes": 1, "No": 0}).astype(int)
    out = d.drop(columns=[OPENML_TARGET])
    out.insert(0, TARGET, y)
    got = {"shape": out.shape, "default": int(y.sum()),
           "income_na": int(out["MonthlyIncome"].isna().sum()), "dep_na": int(out["NumberOfDependents"].isna().sum())}
    if got != EXPECT:
        raise SystemExit(f"下載的資料跟預期不同：{got}（預期 {EXPECT}）")
    return out


if __name__ == "__main__":
    if os.path.exists(OUT) and "--force" not in sys.argv:
        raise SystemExit(f"已經有 {OUT}，要重抓請加 --force")
    df = download()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"已存 {OUT}：{len(df):,} 人，違約 {int(df[TARGET].sum()):,}")
