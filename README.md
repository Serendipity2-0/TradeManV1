Description: TradeMan

TradeMan.env

1. **User**
   1.1. **UserDashBoard**
   1.1.1. **PortfolioViewer** - portfoliostats_view.py
   1.1.2. **ProfileViewer** - admin.py - script.py - styles.css
   1.1.3. **Register** - register.py
   1.1.4. **StrategyViewer** - stats.py - strategyapp.py
   1.2. **UserUtils**
   1.2.1. **UserDBUtils**
   1.2.1.1. **UserFirebaseAdapter** - UserFirebaseAdapter.md
   1.2.1.2. **UserSQLAdapter** - UserSQLAdapter.md
   1.2.2. **UserTemplates**
   1.2.2.1. **TelegramMessageTemplates** - TelegramMessageTemplates.md
   1.2.2.2. **UserDocumentationPDF** - UserDocumentationPDF.md

2. **Executor**
   2.1. **ExecutorDashBoard**
   2.1.1. **ErrorLoggingPage** - ErrorLogProcessor.md - error_logging_page.py
   2.1.2. **ExeLoginPage** - LoginPage.md - exe_login.py
   2.1.3. **LiveTradeViewer** - LiveTradeViewer.md - live_trade_viewer.py
   2.1.4. **ModifyStrategy** - ModifyStrategy.md - modify_strategy.py - usermanagerapp.py
   2.1.5. **OrderExecutionPage** - OrderExecutionPage.md - order_exe_page.py
   2.2. **ExecutorUtils**
   2.2.1. **BrokerCenter**
   2.2.1.1. **Brokers**
   2.2.1.1.1. **AliceBlue** - AliceBlue.md - alice_adapter.py - alice_login.py
   2.2.1.1.2. **Zerodha** - Zerodha.md - kite_login.py - zerodha_adapter.py
   2.2.1.2. **BrokerUtils**
   2.2.1.2.1. **TaxAndBrokerageCalculations** - TaxAndBrokerageCalculations.md - taxnbrok_calc.py
   2.2.2. **InstrumentCenter**
   2.2.2.1. **DailyInstrumentAggregator** - DailyInstrumentAggregator.md - DailyInstrumentAggregator.py
   2.2.2.2. **InstrumentMonitor** - InstrumentMonitor.md - instrument_monitor.py
   2.2.3. **LoggingCenter**
   2.2.3.1. **SignalInfoLogAdapter** - SignalInfoLogAdapter.md - signal_info_adapter.py
   2.2.4. **NotificationCenter**
   2.2.4.1. **Discord** - Discord.md - discord_adapter.py
   2.2.4.2. **Telegram** - Telegram.md - telegram_adapter.py
   2.2.5. **OrderCenter** - OrderCenter.md - OrderCenterUtils.py

   2.3. **Strategies**
   2.3.1. **AmiPy** - AmiPy.md - AmiPyLive.py - README.md - amipy_place_orders.py - chart.py - straddlecalculation.py
   2.3.2. **Coin** - Coin.md - Coin.py
   2.3.3. **ExpiryTrader** - ExpiryTrader.md - ExpiryTrader.py
   2.3.4. **MPWizard** - MPWizard.md - MPWizard.py - MPWizard_calc.py - MPWizard_monitor.py
   2.3.5. **OvernightFutures** - OvernightFutures.md - OvernightFutures_calc.py - Screenipy_futures_afternoon.py - Screenipy_futures_morning.py - nifty_model_v2.h5 - nifty_model_v2.pkl
   2.3.6. **PyStocks** - PyStocks.md - Readme.md - StopLoss.py - TA_indicators.py - fetcher.py - pystocks.py - strategies.py - strategies_temp - Mean_reversion.py - golden_crossover.py - momentumStrategy.py - nr4.py - rsiStrategy.py - volumeBO.py - test.py
   2.3.7. **VPOCOptions** - VPOCOptions.md

   2.4. **Scripts**
   2.4.1. **DailyLogin** - DailyLogin(Login and Validator).md
   2.4.1.1. **Login** - DailyLogin.md - DailyLogin.py
   2.4.1.2. **FundsValidator** - FundValidator.py - FundsValidator.md
   2.4.1.3. **DailyInstrumentAggregator** - DailyInstrumentAggregator.md
   2.4.1.4. **AmiplifierUpdate** - AmiplifierUpdate.md
   2.4.2. **StrategyScripts** - StrategyScripts.md - Various Shell Scripts (e.g., \*.sh)
   2.4.3. **EODScripts** - EODScripts.md
   2.4.3.1. **SweepOrders** - SweepOrders.md
   2.4.3.2. **ValidateData** - ValidateData.md
   2.4.3.3. **SignalsLogging** - SignalsLogging.md
   2.4.3.4. **UserTradeLogging** - UserTradeLogging.md
   2.4.3.4.1. **DTDUpdate** - DTDUpdate.md
   2.4.3.4.2. **UpdateDB** - UpdateDB.md
   2.4.3.5. **SendReports** - SendReports.md
   2.4.3.6. **TickerDB** - TickerDB.md
   2.4.4. **RestartScripts** - RestartScripts.md
   2.4.5. **WeeklyReports** - WeeklyReports.md
   2.4.5.1. **LedgerTransactionsValidator** - LedgerTransactionsValidator.md
   2.5. **OrderBot**
   2.5.1. **TelegramOrderBot** - TelegramOrderBot.md - teleorderbot.py
   2.5.2. **OrderBotUtils**

3. **MarketInfo**
   3.1. **MarketInfoDashBoard**
   3.1.1. **Backtest** - Backtest.md
   3.1.2. **MarketInfoViewer** - MarketInfoViewer.md
   3.1.3. **MachineLearning** - MachineLearning.md
   3.2. **Backtest** - Backtest.md
   3.2.1. **MarketSimulator** - MarketSimulator.md - MarketSim.py
   3.2.2. **GFDLIngest** - GFDLIngest.md
   3.3. **DataCenter** - DataCenter.md - DailyEODDB.py - KiteHistoricalDatatoCSV.ipynb - TimeScaleDBGFDLImport.py

Databases

1. Firebase
   1.1 UserProfile
   1.2 StrategyCard
   1.3 MarketInfoStudy

2. SQLite
   2.1 Signals
   2.2 UserTradeBook
   2.3 Instruments
   2.4 SignalsInfo
   2.5 ErrorLog
   2.6 FnOInfo

3. SQL
   3.1 TickerData

4. Templates
   4.1 Discord Templates
   4.2 Telegram Templates
5. Dict
   5.1 order_details_dict

Utils

1. FireBaseUtils
2. LoggingCenterUtils
3. BrokerUtils
4. DBUtils
5. OrderCenterUtils
6. StrategyUtils
7. UserDBUtils

NOTES

1. TradeStateImplementation: If the program stops abruptly It should run all the scripts under strategy folder and generate Signals for each strategy. It should check the strategyDB and match with the signals. If there is any mismatch notify us through telegram


TODO for TradeMan V1.1.1:

Bugs:
> Tradebook reconsilation with commission table and pnl withdrawal table
   > Add commissions withdrawal table and Pnl withdrawal table

Features:
> Trade Executer in stream lit using StrategySignals(TodayOrders)/ Telegram
> Streamlit hosting


TODO for TradeMan V1.2:

General:
> Onboarding Algotrain accounts
> Password clean up
> Organise office accounts
   > Remove extra Chatgpt account
   > Notion Clean up
   > Office Inventory
   > Github clean up
> Vim tutorial
> Warp vs code link
> Change the path of Data folder to one drive storage
> Chat with RTX
> Streamlit hosting


Bugs:
> Send if the order is Pass or Fail with order details to firebase 
> Add Try and except block in strategy util for freecash and holding
> DB free cash and broker freecash considering the tax changes overnight
> Morning msg after logged in 
   no of active users
   respective trade number : Broker free cash : difference between broker and db
> Trademan dasboard errors(singleton)
> counter for errors
> conslidated Report




Performance:
> Accept screen sharing request automatically
> Teamviewer installation


Features:
> PyStocks 1.0 with morning SL orders
> Selenium script for weekly ledger download
> Insurance Telegram bot
> Consolidated Reports - Weekly and Daily
> TradeMan GPT

WatchList
> MARKET
> Tax
> Account values
> DB
> Consolidated Report
> Signal info and Signal
> Error log




Longterm TODO:

> Fetch the margins from https://kite.trade/docs/connect/v3/margins/#basket-margins for overnight holdings
> Async Functionality
> Order assistant AI - Order Repair based on tradestate ,user and strategy 
> Docs
> pathlib integration
> Config files for paper trading
1. Refactor each strategy and add signal info for each strategy
2. Emergency notification system
   1. WatchDog the log files and send notifications for any code level errors via telegram
   2. Pingpong between the ISP if any one fails send notification via telegram and log
4. VPOC
6. MongoDB Migration

Bugs and Known Issues



