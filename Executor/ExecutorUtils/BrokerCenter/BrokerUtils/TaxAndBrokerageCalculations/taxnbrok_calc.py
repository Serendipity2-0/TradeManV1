
# This function calculates the taxes and brokerage for a given broker for a given set of orders
# trade_type is 'regular' for regular trades and 'futures' for future trades
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
