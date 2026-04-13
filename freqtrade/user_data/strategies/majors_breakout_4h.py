# pragma pylint: disable=missing-docstring, invalid-name
"""4h breakout: close above prior N-bar high; exit below short EMA."""

from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy


class MajorsBreakout4h(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "4h"
    can_short = False

    breakout_period = 20

    minimal_roi = {
        "0": 0.15,
        "960": 0.06,
    }
    stoploss = -0.09

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
        dataframe["range_high"] = dataframe["high"].rolling(self.breakout_period).max().shift(1)
        dataframe["ema_exit"] = ta.EMA(dataframe, timeperiod=12)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["range_high"])
                & (dataframe["range_high"].notna())
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] < dataframe["ema_exit"]),
            "exit_long",
        ] = 1
        return dataframe
