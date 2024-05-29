Name: ExpiryTrader
Status: In Progress(High Priority)
Description: Sells weekly OTM options of respective Instruments on its expiry day
SampleData: StrategyCard
Dependencies: StrategyUtils
Functions:  1. Create a ExpiryTrader obj using the StrategyUtils pass strategy name from env file
            2. Call the Executor Utils to calculate qty
            3. Assign order details and create order_details_dict. Use InstrumentCenterUtils to fetch all the related values.
            4. Use OrderCenterUtils to place the orders for the order_details_dict 
            5. Use NotificationCenterUtils to send a notification for the signal generated
            6. Main function to wait till the start time. Once start time is surpassed all the calculations need to be calculated and orders should be placed 
