import loguru as logger


def update_user_net_values_firebase(user, net_values):
    """
    Updates the user's net values in Firebase.

    This function takes the user's net values for deposits, withdrawals, charges, and trades,
    rounds them to two decimal places, and updates these values in the user's Firebase account.

    :param user: A dictionary containing user details, including the unique identifier 'Tr_No'.
    :param net_values: A dictionary containing the net values for 'Deposits', 'Withdrawals', 'Charges', and 'Trades'.
    """
    from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
        update_fields_firebase,
    )

    logger.debug(net_values)
    fields_to_update = {
        "NetAdditions": round(net_values["Deposits"], 2),
        "NetWithdrawals": round(net_values["Withdrawals"], 2),
        "NetCharges": round(net_values["Charges"], 2),
        "NetPnL": round(net_values["Trades"], 2),
    }
    logger.debug(f"fields_to_update: {fields_to_update}")
    # update_fields_firebase(
    #     user_collection_firebase, user["Tr_No"], fields_to_update, "Accounts"
    # )
    # update_fields_firebase(user_collection_firebase,user,fields_to_update,"Accounts")


def update_user_db(user, categorized_df):
    """
    Updates the user's database with categorized ledger data.

    This function connects to the user's SQLite database and appends categorized dataframes
    (containing transaction data) to the respective tables in the database.

    :param user: A dictionary containing user details, including the unique identifier 'Tr_No'.
    :param categorized_df: A dictionary of categorized dataframes to be appended to the user's database.
    """
    from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
        get_db_connection,
        append_df_to_sqlite,
    )

    # db_path = os.path.join(USR_TRADELOG_DB_FOLDER, f"{user}.db")
    # db_path = os.path.join(USR_TRADELOG_DB_FOLDER, f"{user['Tr_No']}.db")
    db_path = None
    conn = get_db_connection(db_path)

    for key, value in categorized_df.items():
        decimal_columns = ["debit", "credit", "net_balance"]
        append_df_to_sqlite(conn, value, key, decimal_columns)


def calculate_ledger_values_and_update_fb():
    """
    Calculates ledger values and updates them in Firebase.

    This function performs the following steps:
    1. Fetches active users from Firebase.
    2. Processes the ledger for each user using broker-specific adapters.
    3. Categorizes the ledger data and calculates net values.
    4. Updates the user's net values in Firebase.
    5. Updates the user's SQLite database with the categorized ledger data.

    Additionally, the function demonstrates processing example ledger files for two brokers:
    Zerodha and AliceBlue.

    # Existing comments and examples have been kept as they are for illustration purposes.
    """
    # Get ledger for all activer users
    # Call broker center utils to process broker ledgers
    # Update the processed dfs to the respective users.db under the transactions_charges, transactions_deposits, transactions_withdrawals, transactions_other, transactions_trades
    # Call the calculate_net_values function to calculate the net values for all users and update the values in thr firebase['Tr_no']['Accounts']

    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_active_users_from_firebase,
        get_ledger_for_user,
        process_user_ledger,
        calculate_user_net_values,
    )
    from Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter import (
        process_kite_ledger,
        calculate_kite_net_values,
    )
    from Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter import (
        process_alice_ledger,
        calculate_alice_net_values,
    )

    # Get the active users from the firebase
    # active_users = fetch_active_users_from_firebase()

    # for user in active_users:
    #     user_ledger = get_ledger_for_user(user)
    #     categorized_df = process_user_ledger(user, user_ledger)
    # net_values = calculate_user_net_values(user, categorized_df)

    # update_user_net_values_firebase(user, net_values)

    # update_user_db(user["Tr_No"], categorized_df)

    csv_file_path = r"/Users/amolkittur/Downloads/ledger-YY0222.csv"
    # Example usage
    kite_categorized_dfs = process_kite_ledger(csv_file_path)
    kite_net_values = calculate_kite_net_values(kite_categorized_dfs)
    update_user_net_values_firebase("Tr00", kite_net_values)
    # update_user_db("Tr00", kite_categorized_dfs)

    # # Print the net values
    print(kite_net_values)

    # # Example usage
    # excel_file_path = r'/Users/amolkittur/Downloads/924446_LedgerStatementofEquityDerivativeCurrency_12022024_013508.xlsx'  # Replace with your Excel file path
    # alice_cat_dfs= process_alice_ledger(excel_file_path)
    # alice_net_values = calculate_alice_net_values(alice_cat_dfs)

    # update_user_net_values_firebase("Tr03", alice_net_values)
    # update_user_db("Tr03", alice_cat_dfs)

    # # Print the net values
    # print(alice_net_values)
