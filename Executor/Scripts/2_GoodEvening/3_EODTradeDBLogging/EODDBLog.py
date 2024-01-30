import sqlite3
from datetime import datetime

import pandas as pd
import os, sys
from dotenv import load_dotenv

DIR = os.getcwd()
sys.path.append(DIR)

ENV_PATH = os.path.join(DIR, '.env')
load_dotenv(ENV_PATH)

db_dir = os.getenv('DB_DIR')


from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import fetch_collection_data_firebase
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import dump_df_to_sqlite, get_db_connection
from Executor.ExecutorUtils.BrokerCenter.BrokerUtils.TaxAndBrokerageCalculations.taxnbrok_calc import calculate_taxes


def process_n_log_trade():
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument as instru
    active_users = fetch_collection_data_firebase('new_clients')
    
    for user in active_users.values():
        db_path = os.path.join(db_dir, f"{user['Tr_No']}.db")
        conn = get_db_connection(db_path)
        if not user.get('Active'):
            continue

        strategies = user.get('Strategies', [])
        for strategy_name, strategy_details in strategies.items():
            trade_state = strategy_details.get('TradeState', {})
            orders = trade_state.get('orders', [])
            processed_trades = {}
            holdings = {}

            for order in orders:
                trade_id_prefix = order['trade_id'].split('_')[0]
                entry_orders = [o for o in orders if trade_id_prefix in o['trade_id'] and 'EN' in o['trade_id'] and 'HO' not in o['trade_id']]
                exit_orders = [o for o in orders if trade_id_prefix in o['trade_id'] and 'EX' in o['trade_id'] and 'HO' not in o['trade_id']]
                hedge_orders = [o for o in orders if trade_id_prefix in o['trade_id'] and 'HO' in o['trade_id']]
                signal = 'Short' if '_SH_' in order['trade_id'] else 'Long'
                corresponding_exit_trade_id = order['trade_id'].replace('EN', 'EX')
                
                # Check if holding or completed trade
                is_holding = not any(corresponding_exit_trade_id == exit_order['trade_id'] for exit_order in orders)

                if is_holding:
                    entry_price = sum([o['avg_prc'] for o in entry_orders]) / len(entry_orders)
                    hedge_entry_price = sum([o['avg_prc'] for o in hedge_orders if 'EN' in o['trade_id']]) / len([o for o in hedge_orders if 'EN' in o['trade_id']]) if hedge_orders else 0.0

                    holdings[strategy_name] = {
                        'trade_id': order['trade_id'],
                        'trading_symbol': instru().get_trading_symbol_by_exchange_token(order['exchange_token']),
                        'entry_time': datetime.strptime(order['time_stamp'], '%Y-%m-%d %H:%M'),
                        'qty': order['qty'],
                        'entry_price': entry_price,
                        'hedge_entry_price': hedge_entry_price,
                        'signal': signal,
                    }
                    continue

                # Process completed trades
                entry_time = min([o['time_stamp'] for o in entry_orders])
                exit_time = max([o['time_stamp'] for o in exit_orders])
                entry_price = sum([o['avg_prc'] for o in entry_orders]) / len(entry_orders)
                exit_price = sum([o['avg_prc'] for o in exit_orders]) / len(exit_orders)
                hedge_entry_price = sum([o['avg_prc'] for o in hedge_orders if 'EN' in o['trade_id']]) / len([o for o in hedge_orders if 'EN' in o['trade_id']])
                hedge_exit_price = sum([o['avg_prc'] for o in hedge_orders if 'EX' in o['trade_id']]) / len([o for o in hedge_orders if 'EX' in o['trade_id']])
                short_trade = (exit_price - entry_price) + (hedge_exit_price - hedge_entry_price)
                long_trade = (entry_price - exit_price) + (hedge_entry_price - hedge_exit_price)
                trade_points = short_trade if signal == 'Short' else long_trade
                qty = sum([o['qty'] for o in entry_orders])
                pnl = trade_points * qty
                tax = calculate_taxes(user['Broker']['BrokerName'], signal, qty, entry_price, exit_price, len(orders))
                net_pnl = pnl - tax
                trading_symbol = instru().get_trading_symbol_by_exchange_token(order['exchange_token'])

                processed_trade = {
                    'trade_id': trade_id_prefix,
                    'trading_symbol': trading_symbol,
                    'signal': signal,
                    'entry_time': datetime.strptime(entry_time, '%Y-%m-%d %H:%M'),
                    'exit_time': datetime.strptime(exit_time, '%Y-%m-%d %H:%M'),
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'hedge_entry_price': hedge_entry_price,
                    'hedge_exit_price': hedge_exit_price,
                    'trade_points': trade_points,
                    'qty': qty,
                    'pnl': pnl,
                    'tax': tax,
                    'net_pnl': net_pnl
                }
                processed_trades[strategy_name] = processed_trade

            for data in processed_trades.values():
                print(data)
                df = pd.DataFrame([data])
                decimal_columns = ['pnl', 'tax', 'entry_price', 'exit_price', 'hedge_entry_price', 'hedge_exit_price', 'trade_points', 'net_pnl']
                dump_df_to_sqlite(conn, df, strategy_name, decimal_columns)
            
            # Check if holdings dict is not empty
            if holdings:
                for data in holdings.values():
                    print(data)
                    df = pd.DataFrame([data])
                    decimal_columns = ['entry_price', 'hedge_entry_price']
                    dump_df_to_sqlite(conn, df, 'holdings', decimal_columns)

        conn.close()

# Example usage
process_n_log_trade()


#TODO: Update holdings table in user db
#TODO: function to update dtd table in user
#TODO: function to update signal db using primary account db values


