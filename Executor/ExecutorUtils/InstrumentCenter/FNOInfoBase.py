import pandas as pd
import os
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

fno_info_csv_path = os.getenv("FNO_INFO_PATH")


class FNOInfo:
    def __init__(self, file_path=fno_info_csv_path):
        """
        Initialize the FNOInfo class with the given file path.

        Args:
            file_path (str): The path to the CSV file containing FNO information.
        """
        self.file_path = file_path
        self.data = None  # Initialize data as None

    def _ensure_data_loaded(self):
        """
        Internal method to load data from the CSV file if it hasn't been loaded yet.

        This method checks if the data attribute is None, and if so, it loads the data
        from the CSV file into a pandas DataFrame and then converts it to a list of
        dictionaries.
        """
        if self.data is None:
            self.df = pd.read_csv(self.file_path)
            self.data = self.df.to_dict(orient="records")

    def get_data_by_base_symbol(self, base_symbol):
        """
        Get data by 'base_symbol'.

        Args:
            base_symbol (str): The base symbol to filter the data.

        Returns:
            list: A list of dictionaries containing the records with the specified base symbol.
        """
        self._ensure_data_loaded()  # Ensure data is loaded
        return [record for record in self.data if record["base_symbol"] == base_symbol]

    def get_lot_size_by_base_symbol(self, base_symbol):
        """
        Get the 'lot_size' for a given 'base_symbol'.

        Args:
            base_symbol (str): The base symbol to filter the data.

        Returns:
            int or None: The lot size for the specified base symbol, or None if not found.
        """
        self._ensure_data_loaded()  # Ensure data is loaded
        qty = [
            record["lot_size"]
            for record in self.data
            if record["base_symbol"] == base_symbol
        ]
        return qty[0] if qty else None

    def get_max_order_qty_by_base_symbol(self, base_symbol):
        """
        Get the 'max_order_qty' for a given 'base_symbol'.

        Args:
            base_symbol (str): The base symbol to filter the data.

        Returns:
            int or None: The maximum order quantity for the specified base symbol, or None if not found.
        """
        self._ensure_data_loaded()  # Ensure data is loaded
        qty = [
            record["max_order_qty"]
            for record in self.data
            if record["base_symbol"] == base_symbol
        ]
        return qty[0] if qty else None
