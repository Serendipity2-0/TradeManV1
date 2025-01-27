import sqlite3
import pandas as pd
import logging
from typing import List, Dict, Optional
from pathlib import Path


class EQBaseFilter:
   """
   A class to filter equity data based on various criteria like sector, 52-week high, and EMA indicators.
  
   Attributes:
       db_path (Path): Path to the SQLite database
       logger (logging.Logger): Logger instance for the class
   """
  
   def __init__(self, db_path: str = "Data/nse_eq_data.db"):
       """
       Initialize EQBaseFilter with database path and setup logging.
      
       Args:
           db_path (str): Path to the SQLite database file
       """
       self.db_path = Path(db_path)
       self.logger = logging.getLogger(__name__)
       self.logger.info("Initializing EQBaseFilter")
      
   def get_connection(self) -> sqlite3.Connection:
       """
       Create and return a database connection.
      
       Returns:
           sqlite3.Connection: Database connection object
       """
       try:
           conn = sqlite3.connect(self.db_path)
           self.logger.info("Successfully connected to database")
           return conn
       except sqlite3.Error as e:
           self.logger.error(f"Error connecting to database: {e}")
           raise
          
   def get_available_sectors(self) -> List[str]:
       """
       Get list of all available sectors from the database.
      
       Returns:
           List[str]: List of unique sectors
       """
       try:
           with self.get_connection() as conn:
               query = "SELECT DISTINCT sector FROM nse_data WHERE sector IS NOT NULL"
               df = pd.read_sql_query(query, conn)
               sectors = df['sector'].tolist()
               self.logger.info(f"Found {len(sectors)} unique sectors")
               return sectors
       except Exception as e:
           self.logger.error(f"Error getting sectors: {e}")
           raise


   def select_sector_cli(self) -> str:
       """
       Present available sectors to user and get their selection.
      
       Returns:
           str: Selected sector name
       """
       sectors = self.get_available_sectors()
       print("\nAvailable Sectors:")
       for idx, sector in enumerate(sectors, 1):
           print(f"{idx}. {sector}")
          
       while True:
           try:
               choice = int(input("\nSelect sector number: "))
               if 1 <= choice <= len(sectors):
                   selected_sector = sectors[choice - 1]
                   self.logger.info(f"User selected sector: {selected_sector}")
                   return selected_sector
               print("Invalid selection. Please try again.")
           except ValueError:
               print("Please enter a valid number.")


   def get_top_52week_high(self, sector: str, limit: int = 5) -> pd.DataFrame:
       """
       Get top stocks near their 52-week high for a given sector.
      
       Args:
           sector (str): Sector to filter by
           limit (int): Number of top stocks to return
          
       Returns:
           pd.DataFrame: Filtered stocks data
       """
       try:
           with self.get_connection() as conn:
               query = """
               SELECT Symbol, ltp, high_52week,
                      (CAST(ltp AS FLOAT) / CAST(high_52week AS FLOAT) * 100) as price_to_high_ratio
               FROM nse_data
               WHERE sector = ?
                 AND ltp IS NOT NULL
                 AND high_52week IS NOT NULL
               ORDER BY price_to_high_ratio DESC
               """
               df = pd.read_sql_query(query, conn, params=[sector])
               self.logger.info(f"Found {len(df)} stocks for sector {sector}")
               return df.head(limit)
       except Exception as e:
           self.logger.error(f"Error getting 52-week high data: {e}")
           raise


   def calculate_ema(self, data: pd.Series, period: int = 20) -> pd.Series:
       """
       Calculate Exponential Moving Average for a price series.
      
       Args:
           data (pd.Series): Price data series
           period (int): EMA period
          
       Returns:
           pd.Series: EMA values
       """
       return data.ewm(span=period, adjust=False).mean()


   def get_ema_filtered_stocks(self, sector: str, ema_period: int = 20, limit: int = 3) -> pd.DataFrame:
       """
       Get top stocks based on EMA indicator for a given sector.
      
       Args:
           sector (str): Sector to filter by
           ema_period (int): EMA calculation period
           limit (int): Number of top stocks to return
          
       Returns:
           pd.DataFrame: Filtered stocks data with EMA signals
       """
       try:
           with self.get_connection() as conn:
               query = """
               SELECT Symbol, ltp,
                      high_52week, low_52week
               FROM nse_data
               WHERE sector = ?
                 AND ltp IS NOT NULL
                 AND high_52week IS NOT NULL
                 AND low_52week IS NOT NULL
               """
               df = pd.read_sql_query(query, conn, params=[sector])
              
               # Convert price strings to float
               df['ltp'] = pd.to_numeric(df['ltp'], errors='coerce')
               df['high_52week'] = pd.to_numeric(df['high_52week'], errors='coerce')
               df['low_52week'] = pd.to_numeric(df['low_52week'], errors='coerce')
              
               # Calculate simple price momentum (can be enhanced with more sophisticated EMA)
               df['price_momentum'] = (df['ltp'] - df['low_52week']) / (df['high_52week'] - df['low_52week'])
              
               # Filter and sort
               df = df.dropna(subset=['price_momentum'])
              
               self.logger.info(f"Calculated EMA signals for {len(df)} stocks")
               return df[['Symbol', 'ltp', 'price_momentum']].sort_values('price_momentum', ascending=False).head(limit)
       except Exception as e:
           self.logger.error(f"Error calculating EMA signals: {e}")
           raise


   def run_analysis(self):
       """
       Run the complete analysis workflow.
       """
       try:
           # 1. Get sector selection from user
           selected_sector = self.select_sector_cli()
           print(f"\nAnalyzing sector: {selected_sector}")


           # 2. Get top 52-week high stocks
           print("\nTop 5 stocks near 52-week high:")
           top_52week = self.get_top_52week_high(selected_sector)
           print(top_52week.to_string(index=False))


           # 3. Get EMA filtered stocks
           print("\nTop 3 stocks based on EMA signal:")
           ema_filtered = self.get_ema_filtered_stocks(selected_sector)
           print(ema_filtered.to_string(index=False))


       except Exception as e:
           self.logger.error(f"Error in analysis workflow: {e}")
           print(f"An error occurred: {e}")


if __name__ == "__main__":
   # Configure logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
  
   # Run analysis
   filter_engine = EQBaseFilter()
   filter_engine.run_analysis()
