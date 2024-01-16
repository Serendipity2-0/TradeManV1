

def get_exchange_token_for_option(base_symbol,main_strikeprc, main_option_type,today_expiry):
    pass

def get_single_ltp(self,token):
        kite = KiteConnect(api_key=Broker.get_primary_account()[0]) #####TODO pass directly apikey and accesstoken
        kite.set_access_token(access_token=Broker.get_primary_account()[1])
        ltp = kite.ltp(token)  # assuming 'kite' is accessible here or you may need to pass it
        return ltp[str(token)]['last_price']
    
def get_instoken_by_exchange_token(main_exchange_token):
    pass