

import fxcmpy
import time
import copy
import numpy as np
import pandas as pd

#establishing connection with FXCM's API
#Note: you need to have generated a token with your account to connect successfully
token_path = "D:\\Python Scripts\\Automated_Trading\\Fxcm_Token.txt"
con = fxcmpy.fxcmpy(access_token = open(token_path,'r').read(), log_level = 'error', server='demo')

#specifying instruments to be traded and position size (in pips) to be taken for each instrument
pairs = ['EUR/USD','EUR/JPY','USD/JPY','AUD/JPY','AUD/NZD','NZD/USD']
pos_size = 10 

def ATR(DF,n):
    "Calculates Average True Range over n time units"
    df = DF.copy()
    df['H-L']=abs(df['bidhigh']-df['bidlow'])
    df['H-PC']=abs(df['bidhigh']-df['bidclose'].shift(1))
    df['L-PC']=abs(df['bidlow']-df['bidclose'].shift(1))
    df['TR']=df[['H-L','H-PC','L-PC']].max(axis=1,skipna=False)
    df['ATR'] = df['TR'].rolling(n).mean()
    df2 = df.drop(['H-L','H-PC','L-PC'],axis=1)
    return df2['ATR']

def roll_avgs(df,n):
    "Calculates n-rolling averages for highs and lows of a given currency pair"
    df["ATR"] = ATR(df,n)
    df["roll_max_cp"] = df["bidhigh"].rolling(n).max()
    df["roll_min_cp"] = df["bidlow"].rolling(n).min()
    df.dropna(inplace=True)
    return df

def trade_signal(DF,l_s):
    "Generates trading signal if resistance levels are broken"
    "Inputs: dataframe containing prices for a given currency pair; current position for the pair"        
    "Output: Trading signal for the currency pair"
    signal = ""
    df = copy.deepcopy(DF)
    if l_s == "":
        if df["bidhigh"][-1]>=df["roll_max_cp"][-1]:
            signal = "Buy"
        elif df["bidlow"][-1]<=df["roll_min_cp"][-1]:
            signal = "Sell"
    elif l_s == "long":
        if df["bidclose"][-1]<=df["bidclose"][-2] - df["ATR"][-2]:
            signal = "Close"
        elif df["bidlow"][-1]<=df["roll_min_cp"][-1]:
            signal="Close_Sell"
    elif l_s == "short":
        if df["bidhigh"][-1]>=df["roll_max_cp"][-1]:
            signal = "Close_Buy"
        elif df["bidclose"][-1]>=df["bidclose"][-2] + df["ATR"][-2]:
            signal = "Close"
    return signal

def main(granularity,time_span):
    "Inputs: granularity of the strategy ('m1','m5','h1','d1', see fxcmpy documentation for all valid inputs)\
             time_span is the ratio of the time for which you want to calculate moving averages and the granularity\
             of the data frame (i.e. the minimum number of rows of the data frame needed to implement the strategy)"
    "Output: depending on the signal generated it may generate a long/short position for each currency pair"
    try:
        open_pos = con.get_open_positions() #gets current open positions from your account
        for currency in pairs:
            long_short = ""
            if len(open_pos)>0:
                open_pos_cur = open_pos[open_pos["currency"]==currency]
                if len(open_pos_cur)>0:
                    if open_pos_cur["isBuy"].tolist()[0]==True: 
                        long_short = "long"
                    elif open_pos_cur["isBuy"].tolist()[0]==False:
                        long_short = "short" 
            #Note that we are admitting only one open position at a time for each currency pair. 
            #When closing a position, since for 'closing' the exact position the API requires the transaction ID (it gets really fiddly),
            #we are simply opening a new opposite position and keeping track of it.
            data = con.get_candles(currency, period='m1', number=50)#puoi fare strategia in funzione di n e questo diventa n + 20 credo
            data = roll_avgs(data,20)
            signal = trade_signal(data,long_short)
    
            if signal == "Buy":
                con.open_trade(symbol=currency, is_buy=True, is_in_pips=True, amount=pos_size, 
                               time_in_force='GTC', stop=-8, trailing_step =False, order_type='AtMarket')
                print("New long position initiated for ", currency)
            elif signal == "Sell":
                con.open_trade(symbol=currency, is_buy=False, is_in_pips=True, amount=pos_size, 
                               time_in_force='GTC', stop=-8, trailing_step =False, order_type='AtMarket')
                print("New short position initiated for ", currency)
            elif signal == "Close":
                con.close_all_for_symbol(currency)
                print("All positions closed for ", currency)
            elif signal == "Close_Buy":
                con.close_all_for_symbol(currency)
                print("Existing Short position closed for ", currency)
                con.open_trade(symbol=currency, is_buy=True, is_in_pips=True, amount=pos_size, 
                               time_in_force='GTC', stop=-8, trailing_step =False, order_type='AtMarket')
                print("New long position initiated for ", currency)
            elif signal == "Close_Sell":
                con.close_all_for_symbol(currency)
                print("Existing long position closed for ", currency)
                con.open_trade(symbol=currency, is_buy=False, is_in_pips=True, amount=pos_size, 
                               time_in_force='GTC', stop=-8, trailing_step =False, order_type='AtMarket')
                print("New short position initiated for ", currency)
    except:
        print("error encountered....skipping this iteration")

"This section of the script runs the trading strategy for a certain time and frequency\
 Here I am running it for 1hr every 2 minutes as an example and using 20min moving averages"
starttime=time.time()
timeout = time.time() + 3600 #input must be in seconds
while time.time() <= timeout:
    try:
        print("passthrough at ",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        main('m1',20)
        time.sleep(120 - ((time.time() - starttime) % 120.0)) #2 minute interval
    except KeyboardInterrupt:
        print('\n\nKeyboard exception received. Exiting.')
        exit()


    