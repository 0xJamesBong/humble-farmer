# pragma pylint: disable=missing-docstring, invalid-name
"""4h mean reversion: long on RSI oversold, exit on RSI recovery."""

from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy


class MajorsRsiMeanRev4h(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "4h"
    can_short = False

    minimal_roi = {
        "0": 0.08,
        "480": 0.04,
        "960": 0.02,
    }
    stoploss = -0.08

    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count = 30

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            ((dataframe["rsi"] < 32) & (dataframe["volume"] > 0)),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["rsi"] > 52),
            "exit_long",
        ] = 1
        return dataframe
