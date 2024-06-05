import re
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch
import os, sys
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

# Define constants and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

CONSOLIDATED_REPORT_PATH = os.getenv("CONSOLIDATED_REPORT_PATH")
ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
CLIENTS_TRADE_SQL_DB = os.getenv("DB_DIR")
CLIENTS_USER_FB_DB = os.getenv("FIREBASE_USER_COLLECTION")
today_string = datetime.now().strftime("%Y-%m-%d")

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    get_broker_pnl,
    get_broker_payin,
)
from Executor.ExecutorUtils.NotificationCenter.Telegram.telegram_adapter import (
    send_message_to_group,
)
from Executor.ExecutorUtils.ExeUtils import get_previous_trading_day
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import get_db_connection
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


def get_today_trades(user_tables, active_stratgies):
    """
    Fetch today's trades for active strategies from user tables.

    Args:
        user_tables (list): List of user tables.
        active_stratgies (list): List of active strategies.

    Returns:
        list: List of today's trades.
    """
    global today_string
    # got to user db and find table names matching Active Strategies and get trades for today
    today_trades = []
    try:
        for strategy in active_stratgies:
            logger.debug(f"Fetching today's trades for: {strategy}")
            for table in user_tables:
                if strategy in list(table.keys())[0]:
                    trades = table[strategy]
                    # if row is None or 'exit_time' not in row or pd.isnull(row['exit_time'])
                    if (
                        trades.empty
                        or "exit_time" not in trades.columns
                        or trades["exit_time"].isnull().all()
                    ):
                        continue
                    # in the table the exit_time column is in this format '2021-08-25 15:30:00'. so i want convert it to '2021-08-25' and then compare it with today_string if matched append it to today_trades
                    trades["exit_time"] = trades["exit_time"].apply(
                        lambda x: x.split(" ")[0]
                    )
                    if today_string in trades["exit_time"].values:
                        today_trades.extend(
                            trades[trades["exit_time"] == today_string].to_dict(
                                "records"
                            )
                        )
        return today_trades
    except Exception as e:
        logger.error(f"Error in get_today_trades: {e}")
        return today_trades


def get_additions_withdrawals(user_tables):
    """
    Calculate the sum of today's additions and withdrawals from the Transactions table.

    Args:
        user_tables (list): List of user tables.

    Returns:
        float: Sum of today's additions and withdrawals.
    """
    global today_string
    # key = Transactions and get the sum of the "amount" column for today under transaction_date which is in this format '2021-08-25 15:30:00
    additions_withdrawals = 0
    try:
        for table in user_tables:
            if list(table.keys())[0] == "Transactions":
                transactions = table["Transactions"]
                transactions["transaction_date"] = transactions[
                    "transaction_date"
                ].apply(lambda x: x.split(" ")[0])
                if today_string in transactions["transaction_date"].values:
                    additions_withdrawals = transactions[
                        transactions["transaction_date"] == today_string
                    ]["amount"].sum()
        return round(additions_withdrawals)
    except Exception as e:
        logger.error(f"Error in get_additions_withdrawals: {e}")
        return round(additions_withdrawals)


def get_new_holdings(user_tables):
    """
    Calculate the net sum of the MarginUtilized column from the Holdings table.

    Args:
        user_tables (list): List of user tables.

    Returns:
        float: Net sum of the MarginUtilized column.
    """
    new_holdings = 0
    try:
        for table in user_tables:
            if list(table.keys())[0] == "Holdings":
                holdings = table["Holdings"]
                # iterate through the rows and convert it to float and get the sum of the "MarginUtilized" column
                new_holdings = sum(
                    float(holding) for holding in holdings["margin_utilized"]
                )

        logger.info(f"new_holdings{new_holdings}")

        return round(float(new_holdings))
    except Exception as e:
        logger.error(f"Error in get_new_holdings: {e}")
        return round(new_holdings)


def update_account_keys_fb(tr_no, account_values):
    """
    Update account keys in Firebase.

    Args:
        tr_no (str): Transaction number.
        account_values (dict): Dictionary containing account values.
    """
    from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
        update_fields_firebase,
    )

    try:
        logger.debug(f"Updating account keys for {tr_no} in Firebase")
        # use this method to update the account keys in the firebase update_fields_firebase(collection, document, data, field_key=None)
        update_fields_firebase(
            CLIENTS_USER_FB_DB,
            tr_no,
            {
                f"{account_values['today_fb_format']}_AccountValue": account_values[
                    "new_account_value"
                ],
                f"{account_values['today_fb_format']}_FreeCash": account_values[
                    "new_free_cash"
                ],
                f"{account_values['today_fb_format']}_Holdings": account_values[
                    "new_holdings"
                ],
            },
            "Accounts",
        )
    except Exception as e:
        logger.error(f"Error in update_account_keys_fb: {e}")


def fetch_user_tables(user_db_conn):
    """
    Fetch all tables from a user's database connection.

    Args:
        user_db_conn: Database connection.

    Returns:
        list: List of user tables.
    """
    user_tables = []
    try:
        for table in user_db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall():
            user_table = {
                table[0]: pd.read_sql_query(f"SELECT * FROM {table[0]}", user_db_conn)
            }
            user_tables.append(user_table)
    except Exception as e:
        logger.error(f"Error in fetching user tables: {e}")
    return user_tables


def calculate_account_values(user, today_trades, user_tables):
    """
    Calculate account values based on today's trades and user data.

    Args:
        user (dict): User data.
        today_trades (list): List of today's trades.
        user_tables (list): List of user tables.

    Returns:
        dict: Dictionary containing calculated account values.
    """
    broker_pnl = get_broker_pnl(user)
    gross_pnl = sum(float(trade["pnl"]) for trade in today_trades)
    expected_tax = sum(float(trade["tax"]) for trade in today_trades)

    # if there is a difference of 3% between broker pnl and gross pnl, then send a message to the admin telegram channel
    if abs(broker_pnl - gross_pnl) > 0.03 * gross_pnl:
        logger.error(
            f"Broker PnL is different from Gross PnL. Broker PnL: {broker_pnl}, Gross PnL: {gross_pnl}"
        )
        group_id = os.getenv("TELEGRAM_REPORT_GROUP_ID")
        message = f"Broker PnL is different from Gross PnL. {round(broker_pnl,2)}, Gross PnL: {round(gross_pnl,2)} for user: {user['Broker']['BrokerUsername']}"
        send_message_to_group(int(group_id), message)

    today_fb_format = datetime.now().strftime("%d%b%y")
    previous_trading_day_fb_format = get_previous_trading_day(datetime.now().date())

    previous_free_cash = user["Accounts"][f"{today_fb_format}_FreeCash"]
    previous_holdings = user["Accounts"][f"{previous_trading_day_fb_format}_Holdings"]
    previous_account_value = user["Accounts"][
        f"{previous_trading_day_fb_format}_AccountValue"
    ]

    # Assuming no additions or withdrawals for simplicity
    broker_payin = get_broker_payin(user)
    broker_payout = 0  # As of now only zerodha is providing broker payout

    new_free_cash = previous_free_cash + gross_pnl - expected_tax + broker_payin
    # Placeholder for new holdings calculation; you might need additional info for this
    new_holdings = get_new_holdings(user_tables)

    new_account_value = round(
        previous_account_value + gross_pnl - expected_tax + broker_payin + broker_payout
    )
    net_change = new_account_value - previous_account_value
    net_change_percentage = (
        (net_change / previous_account_value * 100) if previous_account_value else 0
    )

    # Calculate drawdown, which is a placeholder here; you might need additional data for an accurate calculation
    drawdown = min(new_account_value - user["Accounts"]["CurrentBaseCapital"], 0)
    if user["Accounts"]["CurrentBaseCapital"] > 0 and drawdown < 0:
        drawdown_percentage = (
            (drawdown) / user["Accounts"]["CurrentBaseCapital"]
        ) * 100
    else:
        drawdown_percentage = 0

    account_values = {
        "today_fb_format": today_fb_format,
        "previous_free_cash": previous_free_cash,
        "previous_holdings": previous_holdings,
        "new_free_cash": new_free_cash,
        "new_holdings": new_holdings,
        "new_account_value": new_account_value,
        "net_change": net_change,
        "net_change_percentage": net_change_percentage,
        "drawdown": drawdown,
        "drawdown_percentage": drawdown_percentage,
    }
    if broker_payin != 0.0:
        account_values["additions"] = broker_payin

    return account_values


def get_today_trades_for_all_users(active_users, active_strategies):
    """
    Get today's trades for all active users.

    Args:
        active_users (list): List of active users.
        active_strategies (list): List of active strategies.

    Returns:
        list: List of today's trades for all users.
    """
    all_today_trades = []
    for user in active_users:
        try:
            user_db_path = os.path.join(CLIENTS_TRADE_SQL_DB, f"{user['Tr_No']}.db")
            user_db_conn = get_db_connection(user_db_path)
            user_tables = fetch_user_tables(user_db_conn)

            today_trades = get_today_trades(user_tables, active_strategies)
            for trade in today_trades:
                trade["user_tr_no"] = user[
                    "Tr_No"
                ]  # Optionally tag each trade with the user's TR number for identification
            all_today_trades.extend(today_trades)

        except Exception as e:
            logger.error(f"Error processing trades for user {user['Tr_No']}: {e}")
    return all_today_trades


def today_trades_data(active_users, today_trades):
    """
    Process today's trades data for all active users.

    Args:
        active_users (list): List of active users.
        today_trades (list): List of today's trades.

    Returns:
        list: List of consolidated trade data.
    """
    from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
        update_fields_firebase,
    )
    from datetime import datetime

    consolidated_data = []

    for user in active_users:
        strategy_pnl = {}
        user_name = user["Profile"]["Name"]
        tr_no = user["Tr_No"]
        base_capital = user["Accounts"]["CurrentBaseCapital"]
        base_capital_str = f"{base_capital:.2f}"
        today_fb_format = datetime.now().strftime("%d%b%y")
        current_capital = user["Accounts"].get(
            f"{today_fb_format}_AccountValue", 0
        )  # Use get for safety
        current_capital_str = f"{current_capital:.2f}"
        drawdown_amount = min(current_capital - base_capital, 0)
        drawdown_amount_str = f"{drawdown_amount:.2f}"
        drawdown_percentage = (
            (drawdown_amount / base_capital * 100) if base_capital else 0
        )
        drawdown = f"{float(drawdown_amount):.2f} ({float(drawdown_percentage):.2f}%)"
        logger.debug(f"Drawdown for {user_name} is {drawdown}")

        # Initialize net_pnl_amount for each user
        net_pnl_amount = 0  # Reset to 0 for each user

        for trade in today_trades:
            if trade["user_tr_no"] == tr_no:
                strategy_amount = float(trade["net_pnl"])
                strategy_percentage = (
                    (strategy_amount / base_capital * 100) if base_capital else 0
                )
                strategy_pnl[
                    trade["trade_id"]
                ] = f"{float(strategy_amount):.2f} ({float(strategy_percentage):.2f}%)"

                # Accumulate net_pnl for the user
                net_pnl_amount += float(trade["net_pnl"])

        net_pnl_percentage = (
            (net_pnl_amount / base_capital * 100) if base_capital else 0
        )
        net_pnl = f"{float(net_pnl_amount):.2f} ({float(net_pnl_percentage):.2f}%)"
        current_week_pnl_amount = (
            user["Accounts"].get("CurrentWeekPnL", 0) + net_pnl_amount
        )
        current_week_pnl_percentage = (
            (current_week_pnl_amount / base_capital * 100) if base_capital else 0
        )
        current_week_pnl = f"{float(current_week_pnl_amount):.2f} ({float(current_week_pnl_percentage):.2f}%)"

        # Update the user's current_week_pnl in Firebase (not shown, assume similar to update_account_keys_fb)
        update_fields_firebase(
            CLIENTS_USER_FB_DB,
            tr_no,
            {"CurrentWeekCapital": current_week_pnl_amount},
            "Accounts",
        )

        consolidated_data.append(
            [
                tr_no,
                user_name,
                base_capital_str,
                current_capital_str,
                drawdown_amount_str,
                current_week_pnl,
                net_pnl,
                strategy_pnl,
            ]
        )

    return consolidated_data


# Define constants for the document layout
standard_margin = 0.5 * inch  # Standard margin around the content
header_height = 20  # Estimated height of the header
space_below_header = 0.25 * inch  # Space between the header and the content
top_margin = (
    standard_margin + header_height + space_below_header
)  # Calculate the top margin to include space for the header


def df_to_table(df, column_widths=None):
    """
    Convert a DataFrame to a ReportLab Table.

    Args:
        df (DataFrame): DataFrame to convert.
        column_widths (list, optional): List of column widths.

    Returns:
        Table: ReportLab Table object.
    """
    if column_widths is None:
        # Set the width of each column to proportionally fill the page width
        page_width = landscape(A4)[0]
        standard_margin = 0.5 * inch  # Standard margin for readability
        usable_width = (
            page_width - 2 * standard_margin
        )  # Subtract margins from both sides
        column_width = usable_width / len(df.columns)  # Divide by number of columns
        column_widths = [column_width] * len(df.columns)
        # if the column name is Tr_No the width should be 12 and if the column name is Strategy PnL the width should be 30
        if "Tr_No" in df.columns:
            column_widths[0] = 35

        if "Strategy PnL" in df.columns:
            column_widths[7] = 156

    data = [df.columns.tolist()] + df.values.tolist()
    table = Table(data, colWidths=column_widths)

    # Define and apply a basic table style
    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.gray),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("TOPPADDING", (0, 1), (-1, -1), 6),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("BOX", (0, 0), (-1, -1), 2, colors.black),
        ]
    )

    # Column indices for "Current Week PnL", "Net PnL", and "Strategy PnL"
    indices = [
        df.columns.get_loc(col)
        for col in [
            "Current Week PnL",
            "Net PnL",
            "Strategy PnL",
            "Today",
            "Week",
            "Month",
            "Year",
            "Drawdown",
        ]
        if col in df.columns
    ]

    # Apply text color based on value (positive in green, negative in red)
    for row_index, row in enumerate(data[1:], 1):  # Skip header row, hence data[1:]
        for col_index in indices:
            value = row[col_index]

            # Check if the cell contains negative values
            if isinstance(value, str) and ("-" in value):
                style.add(
                    "TEXTCOLOR",
                    (col_index, row_index),
                    (col_index, row_index),
                    colors.red,
                )
            elif isinstance(value, float) and value < 0:
                style.add(
                    "TEXTCOLOR",
                    (col_index, row_index),
                    (col_index, row_index),
                    colors.red,
                )
            elif isinstance(value, float) and value == 0.00:
                style.add(
                    "TEXTCOLOR",
                    (col_index, row_index),
                    (col_index, row_index),
                    colors.black,
                )
            elif isinstance(value, str) and value[:4] == "0.00":
                style.add(
                    "TEXTCOLOR",
                    (col_index, row_index),
                    (col_index, row_index),
                    colors.black,
                )
            else:
                style.add(
                    "TEXTCOLOR",
                    (col_index, row_index),
                    (col_index, row_index),
                    colors.green,
                )

    table.setStyle(style)
    return table


def convert_dfs_to_pdf(
    trade_df,
    movement_df,
    signal_with_market_info_df,
    user_pnl,
    errorlog_df,
    output_path,
):
    """
    Convert multiple DataFrames to a PDF document.

    Args:
        trade_df (DataFrame): Trade data DataFrame.
        movement_df (DataFrame): Movement data DataFrame.
        signal_df (DataFrame): Signal data DataFrame.
        market_info_df (DataFrame): Market info DataFrame.
        user_pnl (DataFrame): User PnL DataFrame.
        errorlog_df (DataFrame): Error log DataFrame.
        output_path (str): Output path for the PDF.
    """
    # Setup document with appropriate margins
    standard_margin = 0.5 * inch
    pdf = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        leftMargin=standard_margin,
        rightMargin=standard_margin,
        topMargin=top_margin,
        bottomMargin=standard_margin,
    )
    elements = []
    # Convert the movement DataFrame to a ReportLab Table and add it to elements
    if not movement_df.empty:
        movement_table = df_to_table(movement_df)
        elements.append(movement_table)
        elements.append(PageBreak())  # Adds a new page break for the blank page
    else:
        elements.append(
            Spacer(1, 50)
        )  # Add a spacer if there's no movement data, for consistency
        elements.append(PageBreak())  # Still add a page break even if no movement data

    # Convert the signal DataFrame to a ReportLab Table and add it to elements
    if not signal_with_market_info_df.empty:
        signal_table = df_to_table(signal_with_market_info_df)
        elements.append(signal_table)
    else:
        elements.append(Spacer(1, 50))  # Add a spacer if there's no signal data

    # Assuming a blank page is desired between the movement and trade data
    elements.append(
        Spacer(1, 50)
    )  # This spacer is just to simulate content on the blank page
    elements.append(
        PageBreak()
    )  # Add another page break to start trade data on a new page

    # Convert the user PnL DataFrame to a ReportLab Table and add it to elements
    if not user_pnl.empty:
        user_pnl_table = df_to_table(user_pnl)
        elements.append(user_pnl_table)
    else:
        elements.append(Spacer(1, 50))  # Add a spacer if there's no user PnL data

    elements.append(
        Spacer(1, 50)
    )  # This spacer is just to simulate content on the blank page
    elements.append(
        PageBreak()
    )  # Add another page break to start trade data on a new page

    # Convert the trade DataFrame to a ReportLab Table and add it to elements
    if not trade_df.empty:
        trade_table = df_to_table(trade_df)
        elements.append(trade_table)

    elements.append(
        Spacer(1, 50)
    )  # This spacer is just to simulate content on the blank page
    elements.append(
        PageBreak()
    )  # Add another page break to start trade data on a new page

    # Convert the error log DataFrame to a ReportLab Table and add it to elements
    if not errorlog_df.empty:
        errorlog_table = df_to_table(errorlog_df)
        elements.append(errorlog_table)

    # Build the PDF with all elements (movement data, blank page, trade data)
    pdf.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)


def header_footer(canvas, doc):
    """
    Define header and footer for the PDF document.

    Args:
        canvas: ReportLab canvas object.
        doc: ReportLab document object.
    """
    canvas.saveState()

    # Define constants
    standard_margin = 0.5 * inch  # Set standard margin
    header_height = 30  # Set header height

    # Header text based on the page number
    if doc.page == 1:
        header_text = "MARKET INFO"
    elif doc.page == 2:
        header_text = "SIGNAL INFO"
    elif doc.page == 3:
        header_text = "MARKET PARAMS INFO"
    elif doc.page == 4:
        header_text = "USER INFO"
    elif doc.page == 5:
        header_text = "USER STRATEGY DATA"
    elif doc.page == 6:
        header_text = "ERROR LOG DATA"
    else:
        header_text = "Additional Data"

    # Set the font for the header text
    canvas.setFont("Helvetica-Bold", 14)
    text_width = canvas.stringWidth(header_text, "Helvetica-Bold", 14)

    # Calculate page and content dimensions
    page_width, page_height = landscape(A4)
    content_width = page_width - (
        2 * standard_margin
    )  # Content width matches header width

    # Calculate the text's x position (centered within the header)
    text_x = (page_width - text_width) / 2

    # Calculate the text's y position
    text_y = (
        page_height - standard_margin - header_height / 2 - 7
    )  # Center text vertically in the header

    # Draw the dark gray rectangle for the header background
    canvas.setFillColor(colors.darkgray)
    canvas.setStrokeColor(colors.black)
    canvas.rect(
        standard_margin,
        page_height - standard_margin - header_height,
        content_width,
        header_height,
        stroke=1,
        fill=1,
    )

    # Draw the header text
    canvas.setFillColor(colors.black)
    canvas.drawString(text_x, text_y, header_text)

    canvas.restoreState()


def format_df_data(df):
    """
    Format DataFrame data for PDF output.

    Args:
        df (DataFrame): DataFrame to format.

    Returns:
        DataFrame: Formatted DataFrame.
    """
    styles = getSampleStyleSheet()

    # Regular expression to find numbers in a string
    number_finder = re.compile(r"[-+]?\d*\.\d+|[-+]?\d+")

    # Check if 'Strategy PnL' column exists to prevent errors
    if "Strategy PnL" in df.columns:
        for i, row in df.iterrows():
            if isinstance(row["Strategy PnL"], dict):
                formatted_text = ""
                for k, v in row["Strategy PnL"].items():
                    # Find numbers in the string
                    numbers = number_finder.findall(v)
                    if numbers:
                        # Assume first number is the relevant one for coloring
                        value = float(numbers[0])
                        color = "green" if value >= 0 else "red"
                    else:
                        # Default color if no number found
                        color = "black"
                    formatted_text += f'<font color="{color}">{k}: {v}</font><br/>'
                df.at[i, "Strategy PnL"] = Paragraph(formatted_text, styles["Normal"])
            else:
                # Non-dict values handling; attempting to find a number
                numbers = number_finder.findall(str(row["Strategy PnL"]))
                if numbers:
                    value = float(numbers[0])
                    color = "green" if value >= 0 else "red"
                    df.at[i, "Strategy PnL"] = Paragraph(
                        f'<font color="{color}">{row["Strategy PnL"]}</font>',
                        styles["Normal"],
                    )
                else:
                    # Handling strings with no numbers
                    df.at[i, "Strategy PnL"] = Paragraph(
                        str(row["Strategy PnL"]), styles["Normal"]
                    )

    for column_name in ["Location", "Message"]:
        if column_name in df.columns:
            for i, row in df.iterrows():
                if isinstance(row[column_name], str):
                    formatted_text = f'<para align="center">{row[column_name]}</para>'
                    df.at[i, column_name] = Paragraph(formatted_text, styles["Normal"])

    return df
