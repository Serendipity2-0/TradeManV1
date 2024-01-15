Name: LoggingAdapter
Status:TBI
Description:1. Process trades in user strategy and log it to user/strategy log
            2. Validate user and eod broker order details and match them 
            3. If any mismatch notify through telegram
            4. Strategy log adapter method convert each strategy trades in standard format
SampleData: strategy_order_sample.json,broker_order.json(from broker end),user/strategy.csv
Dependencies:[BrokerUtils,DBUtils,FireBaseUtils]
