# pragma pylint: disable=missing-docstring, invalid-name
"""4h trend / momentum: fast EMA above slow EMA, RSI not stretched for long entries."""

from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy


class MajorsTrend4h(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "4h"
    can_short = False

    minimal_roi = {
        "0": 0.12,
        "720": 0.06,
        "1680": 0.03,
    }
    stoploss = -0.10

    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count = 50

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=12)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=26)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["ema_fast"] > dataframe["ema_slow"])
                & (dataframe["rsi"] < 68)
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema_fast"] < dataframe["ema_slow"]),
            "exit_long",
        ] = 1
        return dataframe
