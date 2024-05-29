Name: SignalsLogging
Status:
Description:
SampleData:
Dependencies:

I need one more script that will process the the "TradeState" after validation and log it to {strategy} table in user.db (sqllite). the table headers for every strategy is [trade_id trading_symbol signal entry_time exit_time entry_price exit_price hedge_entry_price hedge_exit_price trade_points qty pnl tax net_pnl]. the script should use "trade_id" field to process.
Details:

1. trade_id: It the first part in "trade_id": "ET12_SH_MO_EN", 'ET12'
2. trading_symbol: get from "main_trading_symbol"
3. signal: "SH" means short, "LG" means Long
4. entry_time: earliest "entry_time" for "ET12" (means for a given trade_id)
5. exit_time: latest "exit_time" for "ET12" (means for a given trade_id)
6. entry_price: Net "avg_prc" for "EN" and "MO" orders ("EN" is entry orders, "EX" means exit orders)("MO" means main orders and "HO" means hedge order)
7. exit_price: Net "avg_prc" for "EX" and "MO" orders
8. hedge_entry_price: Net "avg_prc" for "HO" orders
9. hedge_exit_price: Net "avg_prc" for "HO" orders
10. trade_points: Net of "entry_price" ,"exit_price" and "hedge_entry_price" and "hedge_exit_price"
11. qty: Net "qty" for "EN" and "MO" orders
12. pnl: trade_points x qty
13. tax: use calculate_taxes(broker, trade_type, qty, net_entry_prc, net_exit_prc, no_of_orders) function to calculate taxes
14. net_pnl: pnl - tax

Reference:
def calculate_taxes(broker, trade_type, qty, net_entry_prc, net_exit_prc, no_of_orders):

    # Brokerage
    if broker == 'zerodha':
        brokerage_rate = 20 if trade_type == 'regular' else 0.03 / 100
    elif broker == 'aliceblue':
        brokerage_rate = 15 if trade_type == 'regular' else 0.03 / 100
    brokerage = brokerage_rate * no_of_orders

    # STT/CTT
    intrinsic_value = max(0, net_exit_prc - net_entry_prc) * qty
    stt_ctt_rate = 0.125 / 100 if trade_type == 'regular' else 0.0125 / 100
    stt_ctt = stt_ctt_rate * intrinsic_value

    # Transaction charges
    transaction_charges_rate = 0.05 / 100 if trade_type == 'regular' else 0.0019 / 100
    transaction_charges = transaction_charges_rate * net_exit_prc * qty

    # SEBI charges
    sebi_charges_rate = 10 / 10000000
    sebi_charges = sebi_charges_rate * net_exit_prc * qty

    # GST
    gst_rate = 18 / 100
    gst = gst_rate * (brokerage + sebi_charges + transaction_charges)

    # Stamp charges
    stamp_charges_rate = 0.003 / 100 if trade_type == 'regular' else 0.002 / 100
    stamp_charges = stamp_charges_rate * net_entry_prc * qty

    total_charges = brokerage + stt_ctt + transaction_charges + gst + sebi_charges + stamp_charges
    return total_charges

Sample trade entry for a strategy:
trade_id trading_symbol signal entry_time exit_time entry_price exit_price hedge_entry_price hedge_exit_price trade_points qty pnl tax net_pnl
AP1 Nifty 19400 Short 2023-07-10 05:02:24 2023-07-10 13:26:24 168.05 149.75 3.50 1.00 15.80 200 3160.00 226.49 2933.51
