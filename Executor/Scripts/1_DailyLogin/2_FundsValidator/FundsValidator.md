Name: FundsValidator
Status: TBI
Description:1.Compare the free cash balance from DB with the free cash available in the broker account
            2. Notify if there is any balance mismatch and is greater than 1% via telegram
SampleData: user_sample.json
Dependencies: [BrokerUtils,ExeFirebaseUtils,NotificationCenterUtils]
Notification : To be notified when there is a mismatch in the funds