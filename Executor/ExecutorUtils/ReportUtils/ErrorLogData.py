import pandas as pd

# Load the log file
log_file_path = '/Users/amolkittur/Desktop/TradeManV1/TradeManError.log'  # Update this to your log file's path

# Function to extract and process errors
def process_errors(log_file_path):
    # Read the log file into a DataFrame
    with open(log_file_path, 'r') as file:
        errors = [line.strip() for line in file if "| ERROR" in line]
    
    df_errors = pd.DataFrame(errors, columns=['Error'])
    
    # Extract components of each error message
    error_components = df_errors['Error'].str.extract(
        r'(?P<Timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3}) \| (?P<Level>ERROR)    \| (?P<Location>[^:]+):(?P<Message>.+)')
    
    # Group by error message and location, then count occurrences
    grouped_errors = error_components.groupby(['Location', 'Message']).size().reset_index(name='Count')
    
    # Sort the errors by their frequency and drop duplicates
    sorted_grouped_errors = grouped_errors.sort_values(by='Count', ascending=False)
    unique_errors = sorted_grouped_errors.drop_duplicates(subset=['Message'], keep='first').reset_index(drop=True)
    
    return unique_errors

def main():
    # Process the errors and obtain unique errors with their counts
    unique_errors_df = process_errors(log_file_path)
    return unique_errors_df



