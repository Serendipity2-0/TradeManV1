import os
import sys

DIR = os.getcwd()
sys.path.append(DIR)

from Executor.ExecutorUtils.EquityCenter.EquityCenterUtils import (
    update_todaystocks_db,
    store_ohlcv_stock_data_sqldb,
    store_financial_data_sqldb,
)
from Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils import (
    get_shortterm_stocks_df,
)
from Executor.NSEStrategies.Equity.LongTerm.LongTermUtils import get_longterm_stocks_df
from Executor.NSEStrategies.Equity.MidTerm.MidTermUtils import get_midterm_stocks_df


def main():
    store_ohlcv_stock_data_sqldb()
    store_financial_data_sqldb()

    (
        momentum_stocks_df,
        mean_reversion_stocks_df,
        ema_bb_confluence_stocks_df,
    ) = get_shortterm_stocks_df()
    tfmomentum_stocks_df, tfema_stocks_df = get_midterm_stocks_df()
    combo_stocks_df, ratio_stocks_df = get_longterm_stocks_df()

    update_todaystocks_db(
        momentum_stocks_df,
        mean_reversion_stocks_df,
        ema_bb_confluence_stocks_df,
        ratio_stocks_df,
        combo_stocks_df,
        tfmomentum_stocks_df,
        tfema_stocks_df,
    )


if __name__ == "__main__":
    main()
