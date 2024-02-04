import yfinance as yf
import os
import time
import requests
import numpy as np
import keras
import joblib
import sys


class SuppressOutput:
    def __init__(self, suppress_stdout=False, suppress_stderr=False):
        self.suppress_stdout = suppress_stdout
        self.suppress_stderr = suppress_stderr
        self._stdout = None
        self._stderr = None

    def __enter__(self):
        devnull = open(os.devnull, "w")
        if self.suppress_stdout:
            self._stdout = sys.stdout
            sys.stdout = devnull
        if self.suppress_stderr:
            self._stderr = sys.stderr
            sys.stderr = devnull

    def __exit__(self, *args):
        if self.suppress_stdout:
            sys.stdout = self._stdout
        if self.suppress_stderr:
            sys.stderr = self._stderr


def fetchLatestNiftyDaily(proxyServer=None):
    return yf.download(
        tickers="^NSEI",
        period="5d",
        interval="1d",
        proxy=proxyServer,
        progress=False,
        timeout=10,
    )


def getNiftyModel(proxyServer=None):
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
    import warnings

    warnings.filterwarnings("ignore")
    model, pkl = getNiftyModel(proxyServer=proxyServer)
    with SuppressOutput(suppress_stderr=True, suppress_stdout=True):
        data = data[pkl["columns"]]
        ### v2 Preprocessing
        data["High"] = data["High"].pct_change() * 100
        data["Low"] = data["Low"].pct_change() * 100
        data["Open"] = data["Open"].pct_change() * 100
        data["Close"] = data["Close"].pct_change() * 100
        data = data.iloc[-1]
        ###
        data = pkl["scaler"].transform([data])
        pred = model.predict(data)[0]
    if pred > 0.5:
        out = "Bearish"
        sug = "Hold your Short position!"
    else:
        out = "Bullish"
        sug = "Stay Bullish!"
    return out, pred
