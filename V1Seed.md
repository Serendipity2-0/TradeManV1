http://admin:admin@localhost:8081/db/trademan/trademan_clients/
http://admin:admin@localhost:8081/db/trademan/strategies

http://admin@trademan.com:admin@localhost:8082/
docker exec -it trademan_postgres psql -U admin -d trademan 
-c "SELECT * FROM financials LIMIT 5;"


Plan of action:
1. Keep only omkar, Venkatesh first stock accounts and omkar kite accounts and try logging in.
   1.1 Active = false for rest of the accounts.
   1.2 Add admin collection to get primary account details for all brokers.
   1.3 store all mongo queries in a separate mongo_queries colection.
2. Sell Dharmpur sugars from omkar first stock account. Buy 1 stock through midterm stock for venkatesh.
   2.1 Test API calls for all active users.
   2.2 Fix midterm script and fire dummy orders.
3. Make sure the EOD scripts are working via telegram message.
   3.1 Add telegram bot to send messages to all active users.
   3.2 Verify with office account on prankster.
4. Note down all the areas of improvement.
5. Implement bit by bit.
   5.1 Attach frontend to the backend.
   5.2 Robust testig scripts
   5.3 Strategic User Onboarding from 18th Dec.

Areas of improvement:
1. Remove Shell scripts.
2. Remove all broker related hardcoding apart from the brokerutils folder
3. Remove all hardcoding of the strategy apart from the strategyutils folder.