import pandas as pd

# Define a function to load sheets from both files and compare the 'trade_points'
def compare_trade_points(user_file, signal_file):
    # Load Excel files and obtain sheet names
    user_xl = pd.ExcelFile(user_file)
    signal_xl = pd.ExcelFile(signal_file)
    
    # Identify common sheet names in both files
    common_sheets = set(user_xl.sheet_names).intersection(signal_xl.sheet_names)
    
    # Initialize an empty dataframe to collect discrepancies from all sheets
    all_discrepancies = pd.DataFrame()
    
    # Loop through each common sheet and perform the comparison
    for sheet in common_sheets:
        # Load data from the current sheet of both files
        user_df = user_xl.parse(sheet)
        signals_df = signal_xl.parse(sheet)
        
        # Identify the first 'trade_id' in user data
        first_trade_id = user_df['trade_id'].iloc[0]
        
        # Filter both dataframes to include only entries from the first 'trade_id' onwards
        user_df = user_df[user_df['trade_id'] >= first_trade_id]
        signals_df = signals_df[signals_df['trade_id'] >= first_trade_id]
        
        # Merge dataframes on 'trade_id'
        merged_df = pd.merge(user_df, signals_df, on='trade_id', how='outer', suffixes=('_user', '_signal'))
        
        # Calculate percentage difference between trade_points from both files
        merged_df['perc_diff'] = (abs(merged_df['trade_points_user'] - merged_df['trade_points_signal']) / merged_df['trade_points_signal']) * 100
        
        # Filter out discrepancies where percentage difference is more than 5% or trades are missing
        discrepancies = merged_df[((merged_df['trade_points_user'].isnull()) | (merged_df['trade_points_signal'].isnull())) | (merged_df['perc_diff'] > 5)]
        
        # Selecting relevant columns for the final output
        discrepancies = discrepancies[['trade_id', 'trade_points_user', 'trade_points_signal', 'perc_diff']]
        
        # Append discrepancies from current sheet to the collective dataframe
        all_discrepancies = pd.concat([all_discrepancies, discrepancies], ignore_index=True)
    
    return all_discrepancies

# File paths (assuming these are the paths to the uploaded files)
user_file = r'C:\Users\user\Desktop\Kaas\StrategyAdmin\userexcel\omkar.xlsx'
signal_file = r'C:\Users\user\Desktop\Kaas\StrategyAdmin\userexcel\Signals.xlsx'

# Run the comparison function and retrieve the compiled discrepancies
compiled_discrepancies = compare_trade_points(user_file, signal_file)

# Displaying a snippet of the compiled discrepancies for validation purposes
print('Testing snippet of compiled discrepancies:')
compiled_discrepancies.to_csv('compiled_discrepancies.csv', index=False)
