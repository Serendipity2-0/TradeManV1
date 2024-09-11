# Trading Strategies Variables

## TFMomentum Strategy Variables

1. **TFMomentumEMAThreshold**
   - Description: Threshold for the Exponential Moving Average (EMA) used in the TFMomentum strategy.
   - Impact:
     - Increase: May result in fewer stocks meeting the criteria, potentially selecting stocks with stronger trends.
     - Decrease: May result in more stocks meeting the criteria, potentially including stocks with weaker trends.

2. **TFMomentumGrossProfitGrowth**
   - Description: Minimum growth rate of gross profit required for a stock to be considered.
   - Impact:
     - Increase: Selects companies with higher profitability growth, potentially reducing the number of eligible stocks.
     - Decrease: Selects more companies, including those with lower profitability growth.

3. **TFMomentumNetIncome**
   - Description: Minimum net income required for a stock to be considered.
   - Impact:
     - Increase: Filters for more financially stable companies, reducing the number of eligible stocks.
     - Decrease: Allows more companies, including those with lower net income.

4. **TFMomentumRSILowerThreshold**
   - Description: Lower threshold for the Relative Strength Index (RSI).
   - Impact:
     - Increase: Makes the strategy less sensitive to oversold conditions, potentially missing some buy opportunities.
     - Decrease: Makes the strategy more sensitive to oversold conditions, potentially including more buy opportunities.

5. **TFMomentumRSIUpperThreshold**
   - Description: Upper threshold for the Relative Strength Index (RSI).
   - Impact:
     - Increase: Allows more stocks to pass the RSI filter, including potentially overbought stocks.
     - Decrease: Filters out more overbought stocks, potentially reducing the number of eligible stocks.

6. **TFMomentumSMAValue**
   - Description: Value for the Simple Moving Average (SMA) used in the TFMomentum strategy.
   - Impact:
     - Increase: Smooths out price data more, identifying longer-term trends.
     - Decrease: Makes the SMA more sensitive to short-term price movements.

7. **TFMomentumTotalRevenue**
   - Description: Minimum total revenue required for a stock to be considered.
   - Impact:
     - Increase: Filters for larger companies with higher revenue, reducing the number of eligible stocks.
     - Decrease: Allows more companies, including those with lower revenue.

## TFEMA Strategy Variables

1. **TFEMALargeValue**
   - Description: Value for the large Exponential Moving Average (EMA) used in the TFEMA strategy.
   - Impact:
     - Increase: Makes the EMA more sensitive to long-term price movements.
     - Decrease: Makes the EMA more sensitive to short-term price movements.

2. **TFEMAMarketCapThreshold**
   - Description: Minimum market capitalization required for a stock to be considered.
   - Impact:
     - Increase: Filters for larger companies, reducing the number of eligible stocks.
     - Decrease: Allows smaller companies, increasing the number of eligible stocks.

3. **TFEMAMediumValue**
   - Description: Value for the medium Exponential Moving Average (EMA) used in the TFEMA strategy.
   - Impact: Similar to TFEMALargeValue.

4. **TFEMAROEThreshold**
   - Description: Minimum Return on Equity (ROE) required for a stock to be considered.
   - Impact:
     - Increase: Filters for more profitable companies, reducing the number of eligible stocks.
     - Decrease: Allows more companies, including those with lower profitability.

5. **TFEMARSIUpperThreshold**
   - Description: Upper threshold for the Relative Strength Index (RSI).
   - Impact: Similar to TFMomentumRSIUpperThreshold.

6. **TFEMASMAValue**
   - Description: Value for the Simple Moving Average (SMA) used in the TFEMA strategy.
   - Impact: Similar to TFMomentumSMAValue.

7. **TFEMAShortValue**
   - Description: Value for the short Exponential Moving Average (EMA) used in the TFEMA strategy.
   - Impact: Similar to TFEMALargeValue.

8. **TFEMASmallValue**
   - Description: Value for the small Exponential Moving Average (EMA) used in the TFEMA strategy.
   - Impact: Similar to TFEMALargeValue.

9. **TFEMAVolumeMultiplier**
   - Description: Multiplier for volume used to compare with the volume Simple Moving Average (SMA).
   - Impact:
     - Increase: Requires higher trading volume to meet the criteria, reducing the number of eligible stocks.
     - Decrease: Allows stocks with lower trading volume, increasing the number of eligible stocks.

## Ratio Strategy Variables

1. **RatioDividendYieldThreshold**
   - Description: Minimum dividend yield required for a stock to be considered.
   - Impact:
     - Increase: Filters for higher-yielding dividend stocks, reducing the number of eligible stocks.
     - Decrease: Allows more stocks with lower yields, increasing the number of eligible stocks.

2. **RatioMarketCapThreshold**
   - Description: Minimum market capitalization required for a stock to be considered.
   - Impact: Similar to TFEMAMarketCapThreshold.

3. **RatioPBThreshold**
   - Description: Maximum Price-to-Book (P/B) ratio allowed for a stock to be considered.
   - Impact:
     - Increase: Allows more stocks with higher P/B ratios, potentially including overvalued stocks.
     - Decrease: Filters for lower P/B ratio stocks, reducing the number of eligible stocks.

4. **RatioPEThreshold**
   - Description: Maximum Price-to-Earnings (P/E) ratio allowed for a stock to be considered.
   - Impact:
     - Increase: Allows more stocks with higher P/E ratios, potentially including overvalued stocks.
     - Decrease: Filters for lower P/E ratio stocks, reducing the number of eligible stocks.

## Combo Strategy Variables

1. **ComboDebtToEquityThreshold**
   - Description: Maximum debt-to-equity ratio allowed for a stock to be considered.
   - Impact:
     - Increase: Allows more companies with higher leverage, potentially increasing financial risk.
     - Decrease: Filters for companies with lower leverage, reducing financial risk.

2. **ComboFScoreThreshold**
   - Description: Minimum Piotroski F-Score required for a stock to be considered.
   - Impact:
     - Increase: Filters for companies with stronger financial health, reducing the number of eligible stocks.
     - Decrease: Allows more companies, including those with weaker financial health.

3. **ComboGrossProfitThreshold**
   - Description: Minimum gross profit growth required for a stock to be considered.
   - Impact: Similar to TFMomentumGrossProfitGrowth.

4. **ComboMarketCapThreshold**
   - Description: Minimum market capitalization required for a stock to be considered.
   - Impact: Similar to TFEMAMarketCapThreshold.

5. **ComboOpProfitMarginThreshold**
   - Description: Minimum operating profit margin required for a stock to be considered.
   - Impact:
     - Increase: Filters for companies with higher profitability, reducing the number of eligible stocks.
     - Decrease: Allows more companies, including those with lower profitability.

6. **ComboPBThreshold**
   - Description: Maximum Price-to-Book (P/B) ratio allowed for a stock to be considered.
   - Impact: Similar to RatioPBThreshold.

7. **ComboPEThreshold**
   - Description: Maximum Price-to-Earnings (P/E) ratio allowed for a stock to be considered.
   - Impact: Similar to RatioPEThreshold.

## Mean Reversion Strategy Variables

1. **MeanReversionBBWindow**
   - Description: Window size for calculating Bollinger Bands in the mean reversion strategy.
   - Impact:
     - Increase: Smooths out the bands, identifying longer-term price deviations.
     - Decrease: Makes the bands more sensitive to short-term price deviations.

2. **MeanReversionRSILength**
   - Description: Length of the RSI period used in the mean reversion strategy.
   - Impact:
     - Increase: Makes the RSI less sensitive to short-term price movements.
     - Decrease: Makes the RSI more sensitive to short-term price movements.

3. **MeanReversionRSIUpperThreshold**
   - Description: Upper threshold for the RSI in the mean reversion strategy.
   - Impact: Similar to TFMomentumRSIUpperThreshold.

## Momentum Strategy Variables

1. **MomentumBBWindow**
   - Description: Window size for calculating Bollinger Bands in the momentum strategy.
   - Impact: Similar to MeanReversionBBWindow.

2. **MomentumRSILength**
   - Description: Length of the RSI period used in the momentum strategy.
   - Impact: Similar to MeanReversionRSILength.

3. **MomentumRSIUpperThreshold**
   - Description: Upper threshold for the RSI in the momentum strategy.
   - Impact: Similar to TFMomentumRSIUpperThreshold.