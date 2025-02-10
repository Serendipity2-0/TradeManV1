"""
Debt-related utility functions for processing transactions and managing debt data.
"""

import os
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from sqlalchemy import create_engine
from fastapi import HTTPException
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    update_fields_firebase,
)
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_utils import (
    get_tr_no_for_hl_id,
    get_principal_amount,
)
from User.UserApi import schemas
from User.UserApi.database import get_db_session, init_db
from .common_utils import safe_str, safe_float, safe_int

DIR_PATH = os.getcwd()
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

logger = LoggerSetup()

CLIENTS_COLLECTION = os.getenv("FIREBASE_USER_COLLECTION")
USER_DB_DEBT_PATH = os.getenv("USR_TRADELOG_DEBT_DB_FOLDER")
KAAS_EXCEL_FILE_PATH = os.getenv("KAAS_EXCEL_FILE_PATH")

def read_excel_file(file_path: str, sheet_name: str) -> pd.DataFrame:
    """
    Reads an Excel sheet and returns a DataFrame.

    Args:
        file_path (str): The path to the Excel file.
        sheet_name (str): The name of the sheet to read.

    Returns:
        pd.DataFrame: The DataFrame containing the sheet data.
    """
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        return df
    except FileNotFoundError:
        raise FileNotFoundError(f"Excel file not found at path: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading sheet '{sheet_name}': {str(e)}")

def validate_columns(df: pd.DataFrame, required_columns: List[str], sheet_name: str) -> None:
    """
    Validates that required columns are present in the DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame to validate.
        required_columns (list): The list of required columns.
        sheet_name (str): The name of the sheet.

    Raises:
        ValueError: If any required columns are missing.
    """
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Required columns {missing_columns} not found in {sheet_name} sheet."
        )

def filter_transactions_by_month(df: pd.DataFrame, month: str) -> pd.DataFrame:
    """
    Filters transactions where 'Comments' include the specified month.

    Args:
        df (pd.DataFrame): The DataFrame containing the transactions.
        month (str): The month to filter by.

    Returns:
        pd.DataFrame: The filtered DataFrame.
    """
    return df[df["Description"].str.contains(month, na=False)]

def get_engine_for_acc_id(acc_id: str):
    """
    Creates a database engine for a given AccID.

    Args:
        acc_id (str): The account ID.

    Returns:
        Engine: The database engine.
    """
    tr_no = get_tr_no_for_hl_id(acc_id, "Debt", "SixteenPlus")
    logger.info(f"TrNo for HL ID {acc_id} is {tr_no}")
    db_file = f"{tr_no}_debt.db"
    
    if not os.path.exists(os.path.join(USER_DB_DEBT_PATH, db_file)):
        os.makedirs(USER_DB_DEBT_PATH, exist_ok=True)
        open(os.path.join(USER_DB_DEBT_PATH, db_file), "a").close()
        logger.info(f"Created new database file: {db_file}")
    else:
        logger.info(f"Using existing database file: {db_file}")
    
    engine = create_engine(f"sqlite:///{USER_DB_DEBT_PATH}/{db_file}")
    return engine

def update_firebase_data(tr_no: str, total_interest_earned: float, final_current_balance: float) -> None:
    """
    Updates Firebase with the total interest earned and final current balance.

    Args:
        tr_no (str): The trader number.
        total_interest_earned (float): The total interest earned.
        final_current_balance (float): The final current balance.
    """
    try:
        update_fields_firebase(
            CLIENTS_COLLECTION,
            tr_no,
            {"InterestEarned": total_interest_earned},
            "Strategies/Debt/16+",
        )

        update_fields_firebase(
            CLIENTS_COLLECTION,
            tr_no,
            {"Debt_AccountValue": final_current_balance},
            "Accounts/Debt",
        )

        logger.info(
            f"Firebase updated for Tr_No {tr_no}: Interest Earned: {total_interest_earned}, Current Balance: {final_current_balance}"
        )
    except Exception as e:
        logger.error(f"Error updating Firebase for Tr_No {tr_no}: {str(e)}")

def process_acc_transactions(
    acc_id: str, transactions: pd.DataFrame, current_balance: float
) -> Tuple[int, List[str], float, float]:
    """
    Processes the transactions for a given account ID.

    Args:
        acc_id (str): The account ID.
        transactions (pd.DataFrame): The transactions DataFrame.
        current_balance (float): The current balance.

    Returns:
        tuple: (transactions_imported, errors, total_interest_earned, final_current_balance)
    """
    try:
        tr_no = get_tr_no_for_hl_id(acc_id, "Debt", "SixteenPlus")
        if not tr_no:
            raise ValueError(f"Could not find Tr_No for AccID {acc_id}")

        init_db(tr_no)
        session = get_db_session(tr_no)

        transactions_imported = 0
        errors = []
        final_current_balance = current_balance

        principal_amount = get_principal_amount(tr_no, "Debt", "SixteenPlus")
        logger.info(f"Principal amount for Tr_No {tr_no} is {principal_amount}")

        for _, transaction in transactions.iterrows():
            try:
                existing_transaction = (
                    session.query(schemas.Transaction)
                    .filter_by(transaction_id=transaction["TrNo"])
                    .first()
                )
                if existing_transaction:
                    logger.info(
                        f"Transaction TrNo {transaction['TrNo']} already exists. Skipping."
                    )
                    continue

                new_transaction = schemas.Transaction(
                    transaction_id=safe_int(transaction["TrNo"]),
                    date=safe_str(transaction["Date"]),
                    description=safe_str(transaction["Description"]),
                    amount=safe_float(transaction["Amount"]),
                    payment_mode=safe_str(transaction["PaymentMode"]),
                    acc_id=safe_str(transaction["AccID"]),
                    department=safe_str(transaction["Department"]),
                    comments=safe_str(transaction["Comments"]),
                    category=safe_str(transaction["Category"]),
                    deducted_received_through=safe_str(transaction["DeductedReceivedThrough"]),
                    zoho_match=safe_str(transaction["ZohoMatch"]),
                    expected_payment_date=safe_str(transaction["ExpectedPaymentDate"]),
                    current_balance=final_current_balance,
                )
                session.add(new_transaction)
                transactions_imported += 1

                final_current_balance += new_transaction.amount

            except Exception as e:
                error_message = f"Error processing transaction TrNo {transaction.get('TrNo')}: {str(e)}"
                logger.error(error_message)
                errors.append(error_message)
                continue

        session.commit()
        session.close()

        total_interest_earned = abs(final_current_balance) - principal_amount
        logger.info(f"Total interest earned for Tr_No {tr_no} is {total_interest_earned}")

        return (
            transactions_imported,
            errors,
            total_interest_earned,
            abs(final_current_balance),
        )

    except Exception as e:
        error_message = f"Error processing AccID {acc_id}: {str(e)}"
        logger.error(error_message)
        raise Exception(error_message)

def read_and_validate_excel_data(month: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Reads and validates the Excel data for transactions and accounts.

    Args:
        month (str): The month to filter transactions by.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: The filtered transactions and accounts DataFrames.
    """
    transactions_df = read_excel_file(KAAS_EXCEL_FILE_PATH, "Transactions(Past)")
    accounts_df = read_excel_file(KAAS_EXCEL_FILE_PATH, "Accounts(Present)")

    required_transaction_columns = [
        "TrNo", "Date", "Description", "Amount", "PaymentMode", "AccID",
        "Department", "Comments", "Category", "DeductedReceivedThrough",
        "ZohoMatch", "ExpectedPaymentDate"
    ]
    validate_columns(transactions_df, required_transaction_columns, "Transactions(Past)")

    required_account_columns = [
        "SLNo", "AccountName", "Type", "AccID", "CurrentBalance", "IntRate",
        "NextDueDate", "Bank", "Tenure", "EMIAmt", "Comments"
    ]
    validate_columns(accounts_df, required_account_columns, "Accounts(Present)")

    filtered_transactions = filter_transactions_by_month(transactions_df, month)
    return filtered_transactions, accounts_df

def import_transactions(month: str) -> Dict[str, any]:
    """
    Import transactions from Excel file for a given month.

    Args:
        month (str): The month to import transactions for.

    Returns:
        Dict[str, any]: Dictionary containing results of the import operation:
            - transactions_imported: Number of transactions imported
            - errors: List of any errors that occurred
    """
    try:
        # Read and validate Excel data
        filtered_transactions, accounts_df = read_and_validate_excel_data(month)
        
        # Process the transactions
        total_transactions_imported, total_errors = process_transactions_internal(filtered_transactions, accounts_df)
        
        return {
            "transactions_imported": total_transactions_imported,
            "errors": total_errors
        }
    except Exception as e:
        logger.error(f"Error importing transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def process_transactions(
    filtered_transactions: pd.DataFrame, accounts_df: pd.DataFrame
) -> Tuple[int, List[str]]:
    """
    Processes the transactions for all accounts.
    This function is maintained for backward compatibility.

    Args:
        filtered_transactions (pd.DataFrame): The filtered transactions DataFrame.
        accounts_df (pd.DataFrame): The accounts DataFrame.

    Returns:
        tuple[int, list[str]]: The number of transactions imported and the list of errors.
    """
    return process_transactions_internal(filtered_transactions, accounts_df)

def process_transactions_internal(
    filtered_transactions: pd.DataFrame, accounts_df: pd.DataFrame
) -> Tuple[int, List[str]]:
    """
    Processes the transactions for all accounts.

    Args:
        filtered_transactions (pd.DataFrame): The filtered transactions DataFrame.
        accounts_df (pd.DataFrame): The accounts DataFrame.

    Returns:
        tuple[int, list[str]]: The number of transactions imported and the list of errors.
    """
    total_transactions_imported = 0
    total_errors = []

    for acc_id, transactions in filtered_transactions.groupby("AccID"):
        try:
            if pd.isna(acc_id):
                raise ValueError("AccID is missing in transaction.")

            account_info_df = accounts_df[accounts_df["AccID"] == acc_id]
            if account_info_df.empty:
                raise ValueError(
                    f"Account with AccID '{acc_id}' not found in AccountsPresent sheet."
                )
            account_info = account_info_df.iloc[0]
            current_balance = account_info["CurrentBalance"]

            (
                transactions_imported,
                errors,
                total_interest_earned,
                final_current_balance,
            ) = process_acc_transactions(acc_id, transactions, current_balance)
            total_transactions_imported += transactions_imported
            total_errors.extend(errors)

            tr_no = get_tr_no_for_hl_id(acc_id, "Debt", "SixteenPlus")
            if tr_no:
                update_firebase_data(tr_no, total_interest_earned, final_current_balance)
            else:
                logger.warning(f"Could not find Tr_No for AccID {acc_id}. Firebase not updated.")

        except Exception as e:
            error_message = f"Error processing AccID {acc_id}: {str(e)}"
            logger.error(error_message)
            total_errors.append(error_message)

    return total_transactions_imported, total_errors
