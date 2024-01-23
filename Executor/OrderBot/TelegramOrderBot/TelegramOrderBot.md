Name: TelegramOrderBot
Status: In Progress
Description: create a framework which outputs the order_details_dict and passes it to the order center
SampleData: order_details_dict
Dependencies: [OrderCenterUtils]

Detailed Description:
1. Repair and New order
    If repair return me a list of strategies
    Fetch the trade_state for that strategy and search for failed orders with trade_ids in all the active_users for the selected strategy.
    Return me the list of all the failed orders with the reason for failure
    Input from the user should be how to repair the order
        1. Reduce qty
        2. Retry the order
    Prepare a counter order details to place the repair/failed order.
2. New order as usual 

