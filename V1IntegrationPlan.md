Backend:
1. Place SL orders in the morning





Good Morning:
1. Place SL and update order details in firebase


Strategy:
1. Get market info params
2. Get strategy params and prepare base signal and send discord message
3. Get user params to create user specific signal and order details
4. Send tickers for monitoring with HL values and alert to discord when tickers hit the prices
5. Place orders and log user orders to firebase

Good Evening:
1. Get open orders from firebase and prepare sweep order list
2. Place sweep orders
3. Log user orders to firebase


Session 1:
1. Get Cheeti, V1 Celery, V1 React, BMS

Session 2:
1. Get Cheeti automated with current running chit

Session 3:
1. Debug issues in V1 Celery

Session 4:
1. Make V1 React presentable

