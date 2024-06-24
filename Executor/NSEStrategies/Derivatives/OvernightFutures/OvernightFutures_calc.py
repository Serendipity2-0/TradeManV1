import yfinance as yf
import os
import keras
import joblib
import sys


class SuppressOutput:
    def __init__(self, suppress_stdout=False, suppress_stderr=False):
        """
        Initialize the SuppressOutput class with options to suppress stdout and/or stderr.

        Args:
            suppress_stdout (bool): If True, suppress stdout.
            suppress_stderr (bool): If True, suppress stderr.
        """
        self.suppress_stdout = suppress_stdout
        self.suppress_stderr = suppress_stderr
        self._stdout = None
        self._stderr = None

    def __enter__(self):
        """
        Enter the runtime context related to this object and suppress output if needed.

        Returns:
            SuppressOutput: The instance of the context manager.
        """
        devnull = open(os.devnull, "w")
        if self.suppress_stdout:
            self._stdout = sys.stdout
            sys.stdout = devnull
        if self.suppress_stderr:
            self._stderr = sys.stderr
            sys.stderr = devnull

    def __exit__(self, *args):
        """
        Exit the runtime context related to this object and restore output if needed.
        """
        if self.suppress_stdout:
            sys.stdout = self._stdout
        if self.suppress_stderr:
            sys.stderr = self._stderr


def fetchLatestNiftyDaily(proxyServer=None):
    """
    Fetch the latest daily data for the Nifty index.

    Args:
        proxyServer (str): The proxy server URL if needed.

    Returns:
        pandas.DataFrame: The daily data for the Nifty index.
    """
    return yf.download(
        tickers="^NSEI",
        period="5d",
        interval="1d",
        proxy=proxyServer,
        progress=False,
        timeout=10,
    )


def getNiftyModel(proxyServer=None):
    """
    Load the Nifty model and scaler from disk.

    Args:
        proxyServer (str): The proxy server URL if needed.

    Returns:
        keras.Model: The loaded Keras model.
        dict: The loaded pickle file containing scaler and column information.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    utils_dir = os.path.join(script_dir, "Utils")
    os.makedirs(utils_dir, exist_ok=True)

    files = [
        os.path.join(utils_dir, "nifty_model_v2.h5"),
        os.path.join(utils_dir, "nifty_model_v2.pkl"),
    ]
    model = keras.models.load_model(files[0])
    pkl = joblib.load(files[1])
    return model, pkl


def getNiftyPrediction(data, proxyServer):
    """
    Get the Nifty index prediction based on the latest data.

    Args:
        data (pandas.DataFrame): The latest Nifty index data.
        proxyServer (str): The proxy server URL if needed.

    Returns:
        str: The prediction result ('Bullish' or 'Bearish').
        float: The prediction score.
    """
    import warnings

    warnings.filterwarnings("ignore")
    model, pkl = getNiftyModel(proxyServer=proxyServer)
    with SuppressOutput(suppress_stderr=True, suppress_stdout=True):
        data = data[pkl["columns"]]
        # v2 Preprocessing
        data["High"] = data["High"].pct_change() * 100
        data["Low"] = data["Low"].pct_change() * 100
        data["Open"] = data["Open"].pct_change() * 100
        data["Close"] = data["Close"].pct_change() * 100
        data = data.iloc[-1]
        data = pkl["scaler"].transform([data])
        pred = model.predict(data)[0]
    if pred > 0.5:
        out = "Bearish"
        # sug = "Hold your Short position!"
    else:
        out = "Bullish"
        # sug = "Stay Bullish!"
    return out, pred
