
import yfinance as yf
import pandas as pd
import sqlite3
import logging
from typing import List, Dict, Optional, Tuple
import time
from tqdm import tqdm
import concurrent.futures
import asyncio
from concurrent.futures import ThreadPoolExecutor
from itertools import islice

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EquitySectorAnalyzer:
    """
    A class to analyze equity sectors using yfinance data.
    
    Attributes:
        db_path (str): Path to the SQLite database
        conn (sqlite3.Connection): Database connection object
    """
    
    def __init__(self, db_path: str = "Data/nse_eq_data.db"):
        """
        Initialize the EquitySectorAnalyzer.
        
        Args:
            db_path (str): Path to the SQLite database
        """
        self.db_path = db_path
        self.conn = None
        
    def __enter__(self):
        """Context manager entry point"""
        self.conn = sqlite3.connect(self.db_path)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point"""
        if self.conn:
            self.conn.close()

    def update_stock_info(self) -> None:
        """
        Update stock information by adding sector, ltp, 52weekhigh, and 52weeklow columns.
        """
        try:
            logger.info("Starting stock info update...")
            
            # Read existing data
            df = pd.read_sql_query("SELECT * FROM nse_data", self.conn)
            
            # Add new columns if they don't exist
            cursor = self.conn.cursor()
            for col in ['sector', 'ltp', 'high_52week', 'low_52week']:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM pragma_table_info('nse_data') 
                    WHERE name='{col}'
                """)
                if cursor.fetchone()[0] == 0:
                    cursor.execute(f"ALTER TABLE nse_data ADD COLUMN {col} TEXT")
            
            # Update stock info using yfinance
            total = len(df)
            logger.info(f"Starting to process {total} stocks...")
            
            # Create progress bar
            pbar = tqdm(total=total, desc="Updating stock info", unit="stock")
            
            for idx, row in df.iterrows():
                symbol = f"{row['Symbol']}.NS"  # Add .NS suffix for NSE stocks
                try:
                    logger.debug(f"Fetching data for {symbol}")
                    stock = yf.Ticker(symbol)
                    info = stock.info
                    
                    # Update database
                    cursor.execute("""
                        UPDATE nse_data 
                        SET sector = ?, 
                            ltp = ?, 
                            high_52week = ?, 
                            low_52week = ?
                        WHERE Symbol = ?
                    """, (
                        info.get('sector', 'Unknown'),
                        info.get('currentPrice', 0),
                        info.get('fiftyTwoWeekHigh', 0),
                        info.get('fiftyTwoWeekLow', 0),
                        row['Symbol']
                    ))
                    
                    # Update progress bar description with current stock
                    pbar.set_description(f"Processing {symbol}")
                    pbar.update(1)
                    
                    # Commit every 10 records
                    if idx % 10 == 0:
                        self.conn.commit()
                        logger.debug(f"Committed changes for batch ending at {symbol}")
                    
                    time.sleep(1)  # Respect API rate limits
                    
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {str(e)}")
                    continue
            
            self.conn.commit()
            logger.info("Stock info update completed successfully")
            
        except Exception as e:
            logger.error(f"Error in update_stock_info: {str(e)}")
            raise

    def get_available_sectors(self) -> List[str]:
        """
        Get list of available sectors from the database.
        
        Returns:
            List[str]: List of unique sectors
        """
        try:
            query = "SELECT DISTINCT sector FROM nse_data WHERE sector IS NOT NULL AND sector != 'Unknown'"
            df = pd.read_sql_query(query, self.conn)
            return df['sector'].tolist()
        except Exception as e:
            logger.error(f"Error getting available sectors: {str(e)}")
            raise

    def get_top_52week_stocks(self, sector: str, limit: int = 5) -> pd.DataFrame:
        """
        Get top stocks near their 52-week high for a given sector.
        
        Args:
            sector (str): Sector to filter stocks
            limit (int): Number of top stocks to return
            
        Returns:
            pd.DataFrame: Top stocks near their 52-week high
        """
        try:
            logger.info(f"Finding top {limit} stocks near 52-week high in {sector} sector")
            
            query = """
            SELECT Symbol, sector, ltp, high_52week, low_52week,
                   ROUND(((ltp - low_52week) / (high_52week - low_52week)) * 100, 2) as price_strength
            FROM nse_data
            WHERE sector = ?
                AND ltp > 0 
                AND high_52week > low_52week
            ORDER BY price_strength DESC
            LIMIT ?
            """
            
            df = pd.read_sql_query(query, self.conn, params=(sector, limit))
            logger.info(f"Found {len(df)} stocks matching criteria")
            return df
            
        except Exception as e:
            logger.error(f"Error in get_top_52week_stocks: {str(e)}")
            raise

    def get_ema_crossover_stocks(self, symbols: List[str], limit: int = 3) -> pd.DataFrame:
        """
        Get stocks showing EMA crossover signals from the given list of symbols.
        
        Args:
            symbols (List[str]): List of stock symbols to check
            limit (int): Number of top stocks to return
            
        Returns:
            pd.DataFrame: Stocks with EMA crossover signals
        """
        try:
            logger.info("Finding stocks with EMA crossover signals")
            
            results = []
            for symbol in symbols:
                try:
                    # Get historical data
                    stock = yf.Ticker(f"{symbol}.NS")
                    hist = stock.history(period="60d")
                    
                    if len(hist) < 50:  # Skip if not enough data
                        continue
                    
                    # Calculate EMAs
                    hist['EMA20'] = hist['Close'].ewm(span=20, adjust=False).mean()
                    hist['EMA50'] = hist['Close'].ewm(span=50, adjust=False).mean()
                    
                    # Check for crossover in last 3 days
                    last_3d = hist.tail(3)
                    if (last_3d['EMA20'] > last_3d['EMA50']).all() and \
                       (hist['EMA20'].shift(3) <= hist['EMA50'].shift(3)).iloc[-1]:
                        results.append({
                            'Symbol': symbol,
                            'Last_Close': hist['Close'].iloc[-1],
                            'EMA20': hist['EMA20'].iloc[-1],
                            'EMA50': hist['EMA50'].iloc[-1],
                            'Crossover_Strength': (hist['EMA20'].iloc[-1] / hist['EMA50'].iloc[-1] - 1) * 100
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {str(e)}")
                    continue
                
            # Convert results to DataFrame and sort by crossover strength
            if results:
                df_results = pd.DataFrame(results)
                return df_results.nlargest(limit, 'Crossover_Strength')
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error in get_ema_crossover_stocks: {str(e)}")
            raise

    def _fetch_stock_info(self, symbol: str) -> Tuple[str, Dict]:
        """
        Fetch stock information from yfinance with retries.
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            Tuple[str, Dict]: Symbol and stock info dictionary
        """
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                stock = yf.Ticker(f"{symbol}.NS")
                info = stock.info
                return symbol, {
                    'sector': info.get('sector', 'Unknown'),
                    'ltp': info.get('currentPrice', 0),
                    'high_52week': info.get('fiftyTwoWeekHigh', 0),
                    'low_52week': info.get('fiftyTwoWeekLow', 0)
                }
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch {symbol} after {max_retries} attempts: {str(e)}")
                    return symbol, {}
                time.sleep(retry_delay)
                retry_delay *= 2
    
    def _process_batch(self, symbols: List[str], pbar: tqdm) -> List[Tuple[str, Dict]]:
        """
        Process a batch of symbols concurrently.
        
        Args:
            symbols (List[str]): List of stock symbols
            pbar (tqdm): Progress bar object
            
        Returns:
            List[Tuple[str, Dict]]: List of symbol and info pairs
        """
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self._fetch_stock_info, symbol) for symbol in symbols]
            results = []
            
            for future in concurrent.futures.as_completed(futures):
                symbol, info = future.result()
                if info:  # Only include successful fetches
                    results.append((symbol, info))
                pbar.update(1)
                pbar.set_description(f"Processing {symbol}")
                
            return results

    def update_stock_info(self, batch_size: int = 10) -> None:
        """
        Update stock information by adding sector, ltp, high_52week, and low_52week columns.
        Uses batched processing and concurrent requests for better performance.
        
        Args:
            batch_size (int): Number of stocks to process in each batch
        """
        try:
            logger.info("Starting stock info update...")
            
            # Read existing data
            df = pd.read_sql_query("SELECT Symbol FROM nse_data", self.conn)
            symbols = df['Symbol'].tolist()
            
            # Add new columns if they don't exist
            cursor = self.conn.cursor()
            for col in ['sector', 'ltp', 'high_52week', 'low_52week']:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM pragma_table_info('nse_data') 
                    WHERE name='{col}'
                """)
                if cursor.fetchone()[0] == 0:
                    cursor.execute(f"ALTER TABLE nse_data ADD COLUMN {col} TEXT")
            
            # Process in batches
            total = len(symbols)
            logger.info(f"Starting to process {total} stocks in batches of {batch_size}...")
            
            with tqdm(total=total, desc="Updating stock info", unit="stock") as pbar:
                # Process symbols in batches
                for i in range(0, total, batch_size):
                    batch = symbols[i:i + batch_size]
                    results = self._process_batch(batch, pbar)
                    
                    # Batch update database
                    if results:
                        cursor.executemany("""
                            UPDATE nse_data 
                            SET sector = :sector,
                                ltp = :ltp,
                                high_52week = :high_52week,
                                low_52week = :low_52week
                            WHERE Symbol = :symbol
                        """, [
                            {
                                'symbol': symbol,
                                'sector': info['sector'],
                                'ltp': info['ltp'],
                                'high_52week': info['high_52week'],
                                'low_52week': info['low_52week']
                            }
                            for symbol, info in results
                        ])
                        self.conn.commit()
                        
            logger.info("Stock info update completed successfully")
            
        except Exception as e:
            logger.error(f"Error in update_stock_info: {str(e)}")
            raise

def main():
    """
    Main function to run the equity sector analysis.
    """
    try:
        with EquitySectorAnalyzer() as analyzer:
            # 1. Update stock info
            logger.info("Step 1: Updating stock information...")
            analyzer.update_stock_info()
            
            # 2. Get available sectors and let user select
            sectors = analyzer.get_available_sectors()
            print("\nAvailable sectors:")
            for idx, sector in enumerate(sectors, 1):
                print(f"{idx}. {sector}")
            
            while True:
                try:
                    choice = int(input("\nSelect sector number: "))
                    if 1 <= choice <= len(sectors):
                        selected_sector = sectors[choice - 1]
                        break
                    else:
                        print("Invalid choice. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")
            
            # 3. Get top 5 stocks near 52-week high for selected sector
            logger.info(f"\nStep 2: Finding top 5 stocks near 52-week high in {selected_sector} sector...")
            top_52week = analyzer.get_top_52week_stocks(selected_sector)
            print("\nTop 5 stocks near 52-week high:")
            print(top_52week.to_string(index=False))
            
            # 4. Get EMA crossover signals from these 5 stocks
            logger.info("\nStep 3: Checking for EMA crossovers...")
            ema_stocks = analyzer.get_ema_crossover_stocks(top_52week['Symbol'].tolist())
            
            if not ema_stocks.empty:
                print("\nStocks with EMA crossover signals:")
                print(ema_stocks.to_string(index=False))
            else:
                print("\nNo stocks found with EMA crossover signals")
                
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()