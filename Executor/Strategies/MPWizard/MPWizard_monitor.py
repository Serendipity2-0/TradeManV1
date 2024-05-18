from time import sleep
import os, sys, json
import datetime as dt
import MPWizard_calc as MPWizard_calc

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

TRADE_MODE = os.getenv("TRADE_MODE")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

from Executor.ExecutorUtils.InstrumentCenter.InstrumentMonitor.instrument_monitor import (
    monitor,
)
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
    Instrument,
    get_single_ltp,
)
from Executor.Strategies.StrategiesUtil import (
    StrategyBase,
    assign_trade_id,
    calculate_trigger_price,
    calculate_stoploss,
    calculate_transaction_type_sl,
    calculate_target,
    place_order_strategy_users,
    update_stoploss_orders,
    update_qty_user_firebase,
    update_signal_firebase,
)
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)
from Executor.ExecutorUtils.InstrumentCenter.FNOInfoBase import (
    FNOInfo
)

strategy_obj = StrategyBase.load_from_db("MPWizard")

class MPWInstrument:
    def __init__(self, name, token, trigger_points, price_ref, ib_level=None):
        self.name = name
        self.token = token
        self.trigger_points = trigger_points
        self.price_ref = price_ref
        self.ib_level = ib_level

    def get_name(self):
        return self.name

    def get_token(self):
        return self.token

    def get_trigger_points(self):
        return self.trigger_points

    def get_price_ref(self):
        return self.price_ref

    def get_ib_level(self):
        return self.ib_level

def signal_log_firebase(orders_to_place,cross_type,trade_prefix):
    for order in orders_to_place:
        if order.get("order_mode") == "MO":
            main_trade_id = order.get("trade_id")
            main_trade_id_prefix = main_trade_id.split("_")[0]

    signal_to_log_firebase = {
        "Signal": "Long",
        "TradeId": main_trade_id,
        "Time": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Orders": orders_to_place,
        "StrategyInfo": {
            "trade_id" : main_trade_id_prefix,
            "trade_view": strategy_obj.MarketInfoParams.TradeView,
            "direction": cross_type,
            # "IBLevel": strategy_obj.EntryParams.InstrumentToday[self.get_index_name(order["exchange_token"])]["IBLevel"],
            "price_ref": str(order["price_ref"])
            # "TriggerPoints": strategy_obj.EntryParams.InstrumentToday[self.get_index_name(order["exchange_token"])]["TriggerPoints"],
        },
    }
    update_signal_firebase(strategy_obj.StrategyName, signal_to_log_firebase, trade_prefix)

class OrderMonitor:
    def __init__(self, json_data, max_orders):
        self.instruments = self._create_instruments(json_data)
        self.orders_placed_today = 0
        self.max_orders_per_day = max_orders
        self.today_date = dt.date.today()
        self.done_for_the_day = False
        self.indices_triggered_today = set()
        self.message_sent = {
            instrument.get_name(): {
                level: False for level in instrument.get_trigger_points().keys()
            }
            for instrument in self.instruments
        }
        self.instrument_monitor = monitor()
        self.instrument_monitor.set_callback(self.handle_trigger)
        self._add_tokens_to_instrument_monitor()

    def _add_tokens_to_instrument_monitor(self):
        for instrument in self.instruments:
            self.instrument_monitor.add_token(
                token=str(instrument.get_token()),
                trigger_points=instrument.get_trigger_points(),
                ib_level=instrument.get_ib_level(),
            )

    @staticmethod
    def _load_json_data(json_data):
        return json.loads(json_data)

    def _reset_daily_counters(self):
        self.today_date = dt.date.today()
        self.orders_placed_today = 0
        self.done_for_the_day = False
        self.indices_triggered_today = set()

    def create_single_instrument(self, instruments_data):
        name = instruments_data["Name"]
        token = instruments_data["Token"]
        trigger_points = instruments_data["TriggerPoints"]
        price_ref = instruments_data["PriceRef"]
        instrument = MPWInstrument(name, token, trigger_points, price_ref)
        return instrument

    def _create_instruments(self, instruments_data):
        instruments = []
        for name, data in instruments_data.items():
            # Skip entries that do not have the 'TriggerPoints' key
            if "TriggerPoints" not in data or "PriceRef" not in data:
                continue

            token = data["Token"]

            if token is None:
                logger.warning(f"Warning: Token not found for instrument {name}")
                continue

            trigger_points = data["TriggerPoints"]
            price_ref = data["PriceRef"]
            ib_level = data["IBLevel"]
            instrument = MPWInstrument(name, token, trigger_points, price_ref, ib_level)
            instruments.append(instrument)
        return instruments

    def _check_price_crossing(self, prev_ltp, ltp, levels):
        """Check if the price has crossed a certain level."""
        for level_name, level_price in levels.items():
            if prev_ltp is None:
                continue
            if prev_ltp < level_price <= ltp:
                return "UpCross", level_name
            elif prev_ltp > level_price >= ltp:
                return "DownCross", level_name
        return None, None

    def create_order_details(self, name, cross_type, ltp, price_ref):
        mood_data_entry = self._get_mood_data_for_instrument(name)
        ib_level = mood_data_entry["IBLevel"]
        instru_mood = strategy_obj.MarketInfoParams.TradeView
        if not mood_data_entry:
            return
        option_type = MPWizard_calc.calculate_option_type(
            ib_level, cross_type, instru_mood
        )
        if not option_type:
            return

        strikeprc = strategy_obj.round_strike_prc(ltp, name)
        expiry_date = Instrument().get_expiry_by_criteria(
            name, int(strikeprc), option_type, "current_week"
        )
        exchange_token = Instrument().get_exchange_token_by_criteria(
            name, strikeprc, option_type, expiry_date
        )
        new_base = strategy_obj.reload_strategy(strategy_obj.StrategyName)
        next_trade_prefix = new_base.NextTradeId
        logger.debug(f"Next trade prefix: {next_trade_prefix}")

        option_ltp = get_single_ltp(exchange_token=exchange_token)

        stoploss_transaction_type = calculate_transaction_type_sl(
            strategy_obj.GeneralParams.TransactionType
        )
        limit_prc = calculate_stoploss(
            option_ltp, strategy_obj.GeneralParams.TransactionType, price_ref=price_ref
        )
        trigger_prc = calculate_trigger_price(stoploss_transaction_type, limit_prc)
        target = calculate_target(option_ltp, price_ref=price_ref)

        orders_to_place = [
            {
                "strategy": strategy_obj.StrategyName,
                "signal": "Long",
                "base_symbol": name,
                "exchange_token": exchange_token,
                "transaction_type": strategy_obj.GeneralParams.TransactionType,
                "order_type": strategy_obj.GeneralParams.OrderType,
                "product_type": strategy_obj.GeneralParams.ProductType,
                "price_ref": price_ref,
                "order_mode": "Main",
                "trade_id": next_trade_prefix,
                "trade_mode": TRADE_MODE
            },
            {
                "strategy": strategy_obj.StrategyName,
                "price_ref": price_ref,
                "signal": "Long",
                "base_symbol": name,
                "exchange_token": exchange_token,
                "transaction_type": stoploss_transaction_type,
                "order_type": "Stoploss",
                "product_type": strategy_obj.GeneralParams.ProductType,
                "order_mode": "Trailing",
                "trade_id": next_trade_prefix,
                "limit_prc": limit_prc,
                "trigger_prc": trigger_prc,
                "target": target,
                "trade_mode": TRADE_MODE
            },
        ]
        orders_to_place = assign_trade_id(orders_to_place)
        return orders_to_place, next_trade_prefix

    def create_modify_order_details(self, order_details):
        modify_order_details = [
            {
                "strategy": strategy_obj.StrategyName,
                "base_symbol": order_details["base_symbol"],
                "exchange_token": int(order_details["exchange_token"]),
                "transaction_type": order_details["transaction_type"],
                "target": order_details["target"],
                "limit_prc": order_details["limit_prc"],
                "trigger_prc": order_details["trigger_prc"],
                "order_type": "Stoploss",
                "product_type": order_details["product_type"],
                "segment": Instrument().get_exchange_by_exchange_token(order_details["exchange_token"]),
                "strategy_mode": "MultipleInstruments",
            }
        ]
        return modify_order_details

    def _get_mood_data_for_instrument(self, name):
        for name, data in strategy_obj.EntryParams.InstrumentToday.items():
            if name.startswith(name):
                return data

    def get_index_name(self, token):
        index_tokens = strategy_obj.GeneralParams.IndicesTokens
        token_to_index = {str(v): k for k, v in index_tokens.items()}
        return token_to_index.get(token)

    def get_instrument_by_token(self, token):
        return Instrument().get_trading_symbol_by_exchange_token(token)

    def process_orders(self, instrument, cross_type, ltp, message=None):
        index_name = self.get_index_name(instrument)
        if index_name:
            name = index_name
            price_ref = MPWizard_calc.get_price_ref_for_today(name)
            lot_size = FNOInfo().get_lot_size_by_base_symbol(name)

            if self.orders_placed_today >= self.max_orders_per_day:
                logger.info(
                    "Daily signal limit reached. No more signals will be generated today."
                )
                return
            order_to_place, trade_prefix = self.create_order_details(name, cross_type, ltp, price_ref)
            logger.debug(f"Placing orders for {order_to_place}")
            update_qty_user_firebase(strategy_obj.StrategyName,price_ref,lot_size)
            signal_log_firebase(order_to_place,cross_type,trade_prefix)
            place_order_strategy_users(strategy_obj.StrategyName, order_to_place)


            if message:
                logger.debug(message)
                discord_bot(message, strategy_obj.StrategyName)

            self.indices_triggered_today.add(name)
            self.orders_placed_today += 1
            if name in self.message_sent:
                for level in self.message_sent[name]:
                    self.message_sent[name][level] = True
            # i want to send the order details having order_mode as Trailing to the monitor.add_token
            if order_to_place:
                for order in order_to_place:
                    if order["order_mode"] == "SL":
                        self.instrument_monitor.add_token(order_details=order)
        else:
            logger.error("Index name not found for token:", instrument)

    def process_modify_orders(self, order_details, message=None):
        logger.debug(f"Starting Modifying orders")
        # Update the limit_prc and the trigger_prc in the order_details and pass it to create_modify_order_details and then to modify_orders
        price_ref = order_details["price_ref"]
        order_details["limit_prc"] += (
            price_ref / 2
        )  # Adjust limit_prc by half of price_ref
        order_details["trigger_prc"] = order_details["limit_prc"] + 1.0

        order_to_modify = self.create_modify_order_details(order_details)
        logger.debug(f"Modifying orders for {order_to_modify}")
        update_stoploss_orders(strategy_obj.StrategyName, order_to_modify)

        order_details["target"] += price_ref / 2  # Adjust target by half of price_ref
        logger.debug(f"Order details after modifying")
        return (
            order_details["target"],
            order_details["limit_prc"],
            order_details["trigger_prc"],
        )

    def handle_trigger(self, instrument, data, order_details=None):
        ltp = self.instrument_monitor.fetch_ltp(instrument)
        instru_mood = strategy_obj.MarketInfoParams.TradeView
        index_name = self.get_index_name(instrument)
        if data["type"] == "trigger":
            cross_type = "UpCross" if data["name"] == "IBHigh" else "DownCross"
            message = f"Index : {index_name} \nCross Type : {cross_type} \nIB Level : {data['ib_level']} \nMood : {instru_mood} \nLTP : {ltp}"
            self.process_orders(instrument, cross_type, ltp, message)

        elif data["type"] == "target":
            if order_details:
                logger.debug("entering modify orders block at line 331")
                new_target, new_limit_prc, new_trigger_prc = self.process_modify_orders(
                    order_details=order_details
                )
                trading_symbol = self.get_instrument_by_token(
                    order_details["exchange_token"]
                )
                message = f"New target for {trading_symbol} set to {new_target} and new limit price set to {new_limit_prc} and new trigger price is {new_trigger_prc}."
                logger.debug(message)
                discord_bot(message, strategy_obj.StrategyName)
            else:
                logger.debug("No order details available to update target and limit prices.")

        elif data["type"] == "limit":
            trading_symbol = self.get_instrument_by_token(
                order_details["exchange_token"]
            )
            message = f"Stoploss reached for {trading_symbol}."
            logger.debug(message)
            discord_bot(message, strategy_obj.StrategyName)

    def monitor_index(self):
        logger.debug("Monitoring started...")
        if dt.date.today() != self.today_date:
            self._reset_daily_counters()
            self.message_sent = {
                instrument.get_name(): {
                    level: False for level in instrument.get_trigger_points().keys()
                }
                for instrument in self.instruments
            }
        self.instrument_monitor.start_monitoring()

        sleep(3)
