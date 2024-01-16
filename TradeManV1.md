Description: TradeMan

Folder Structure For TradeMan

TradeMan.env
1. User
    1.1 UserDashboard
        1.1.1 Register
        1.1.1 LoginPage
        1.1.2 ProfileViewer
        1.1.3 PortfolioViewer
        1.1.4 StrategyViewer
        1.1.5 TransactionViewer
   
    1.2 UserUtils
        1.2.1 Validators
            1.2.1.1 LedgerTransactionsValidator
            1.2.1.2 SignalsTradebookValidator
        1.2.2 UserTemplates
            1.2.2.1 TelegramMessageTemplates
            1.2.2.2 UserDocumentationPDF
        1.2.3 UserDButils
            1.2.3.1 UserFirebaseUtils
            1.2.3.2 UserSQLUtils
        1.2.4 UserStreamlitUtils
            1.2.4.1 PortfolioViewerUtils
            1.2.4.2 StrategyViewerUtils
            1.2.4.3 TransactionViewerUtils

3. Executor
    2.1 ExecutorDashBoard
        2.1.1 LoginPage
        2.1.1 OrderExecutionPage
        2.1.2 LiveTradeViewer
        2.1.3 LoggingPage
            2.1.3.1 ErrorLogProcessor
        2.1.4 ModifyStrategy

    2.2 ExecutorUtils
        2.2.1 NotificationCenter
            2.2.1.1 Telegram
            2.2.1.2 Discord
            2.2.1.3 Whatsapp
            2.2.1.4 NotificationCenterUtils
                2.2.1.4.1 EmergencyNotifications
        2.2.2 LoggingCenter
            2.2.2.1 LoggingValidator
            2.2.2.2 SignalLogging
            2.2.2.3 UserLogging
            2.2.2.4 ErrorLogging
            2.2.2.5 SignalInfoLogAdapter
            2.2.2.6 LoggingAdapter
            2.2.2.7 OrderSegregator
        2.2.3 OrderCenter
            2.2.3.1 QtyCalculator
            2.2.3.2 OrderAdapter
        2.2.4 BrokerCenter
            2.2.4.1 Brokers
               2.2.4.1.1 AliceBlue
               2.2.4.1.2 Zerodha
            2.2.4.2 BrokerUtils
                2.2.4.2.1 TaxAndBrokerageCalculations
        2.2.5 InstrumentCenter
            2.2.5.1 InstrumentMonitor
            2.2.5.2 DailyInstrumentAggregator
            2.2.5.3 InstrumentBase
        2.2.6 DBInterface
            2.2.6.1 FirebaseUtils
            2.2.6.2 SQLUtils
    2.3 Strategies
        2.3.1 AmiPy
        2.3.2 ExpiryTrader
        2.3.3 MPWizard
        2.3.4 OvernightFutures
        2.3.5 Coin
        2.3.6 PyStocks
        2.3.7 VPOCOptions
        2.3.8 StrategyBase
    2.4 Scripts
        2.4.1 DailyLogin(Login and Validator)
            2.4.1.1 Login
            2.4.1.2 FundsValidator
            2.4.1.3 DailyInstrumentAggregator
            2.4.1.4 AmiplifierUpdate
        2.4.2 StrategyScripts
        2.4.3 EODScripts
            2.4.3.1 SweepOrders
            2.4.3.2 ValidateData
            2.4.3.3 SignalsLogging
            2.4.3.4 UserTradeLogging
                2.4.3.4.1 DTDUpdate
                2.4.3.4.2 UpdateDB
            2.4.3.5 SendReports
            2.4.3.6 TickerDB
        2.4.4 RestartScripts
        2.4.5 WeekklyReports
            2.4.5.1 LedgerTransactionsValidator
    2.5 OrderBot
        2.5.1 TelegramOrderBot
        2.5.2 OrderBotUtils


3. MarketInfo
    3.1 MarketInfoDashBoard
        3.1.1 Backtest
        3.1.2 MarketInfoViewer
        3.1.3 MachineLearning
    3.2 MarketInfoUtils
    3.3 Backtest
        3.3.1 MarketSimulator
        3.3.2 GFDLIngest
    3.4 DataCenter
        3.4.1 DBUtils


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
