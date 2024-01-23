import sqlite3
from datetime import datetime

import pandas as pd
from exefirebase_adapter import fetch_collection_data_firebase
from exesql_adapter import dump_df_to_sqlite, get_db_connection
from taxnbrok_calc import calculate_taxes


def process_n_log_trade(user_db_path):
    conn = get_db_connection(user_db_path)
    active_users = fetch_collection_data_firebase('new_clients')
    
    for user in active_users.values():
        if not user.get('Active'):
            continue

        strategies = user.get('Strategies', [])
        for strategy_name, strategy_details in strategies.items():
            trade_state = strategy_details.get('TradeState', {})
            orders = trade_state.get('orders', [])
            processed_trades = []

            for order in orders:
                trade_id_prefix = order['trade_id'].split('_')[0]
                signal = 'Short' if '_SH_' in order['trade_id'] else 'Long'
                entry_time = min([o['timestamp'] for o in orders if trade_id_prefix in o['trade_id'] and 'EN' in o['trade_id']])
                exit_time = max([o['timestamp'] for o in orders if trade_id_prefix in o['trade_id'] and 'EX' in o['trade_id']])
                entry_orders = [o for o in orders if trade_id_prefix in o['trade_id'] and 'EN' in o['trade_id']]
                exit_orders = [o for o in orders if trade_id_prefix in o['trade_id'] and 'EX' in o['trade_id']]
                hedge_orders = [o for o in orders if trade_id_prefix in o['trade_id'] and 'HO' in o['trade_id']]

                entry_price = sum([o['avg_prc'] for o in entry_orders]) / len(entry_orders)
                exit_price = sum([o['avg_prc'] for o in exit_orders]) / len(exit_orders)
                hedge_entry_price = sum([o['avg_prc'] for o in hedge_orders if 'EN' in o['trade_id']]) / len([o for o in hedge_orders if 'EN' in o['trade_id']])
                hedge_exit_price = sum([o['avg_prc'] for o in hedge_orders if 'EX' in o['trade_id']]) / len([o for o in hedge_orders if 'EX' in o['trade_id']])
                trade_points = (exit_price - entry_price) + (hedge_exit_price - hedge_entry_price)
                qty = sum([o['qty'] for o in entry_orders])
                pnl = trade_points * qty
                tax = calculate_taxes(user['Broker']['BrokerName'], 'regular', qty, entry_price, exit_price, len(orders))
                net_pnl = pnl - tax

                processed_trade = {
                    'trade_id': trade_id_prefix,
                    'trading_symbol': order['main_trading_symbol'],
                    'signal': signal,
                    'entry_time': datetime.strptime(entry_time, '%Y-%m-%d %H:%M:%S.%f'),
                    'exit_time': datetime.strptime(exit_time, '%Y-%m-%d %H:%M:%S.%f'),
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

                processed_trades.append(processed_trade)
            
            df = pd.DataFrame(processed_trades)
            if not df.empty:
                dump_df_to_sqlite(df, strategy_name, conn)

    conn.close()

#TODO: Update holdings table in user db
#TODO: function to update dtd table in user
#TODO: function to update signal db using primary account db values

# Example usage
process_n_log_trade('path_to_your_user_db.db')
