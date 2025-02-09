from re import T
from django.http import HttpResponse, HttpResponseRedirect
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import get_template, render_to_string
from django.template import Context
from django.contrib.auth.models import User
from django.core.mail import EmailMessage

import pandas as pd
from plotly.offline import plot
from statsmodels.tsa.seasonal import seasonal_decompose, STL
from plotly.subplots import make_subplots
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from datetime import date

# print(f"Name: {__name__}")
# print(f"Package: {__package__}")

from predicts.models import Predicts
from .forms import UserRegisterForm
from .token import account_activation_token
from .models import Router
from .Volatility import Volality_Cone
# from .dataUtil import load_eod_price, get_Max_Options_date, load_df_SQL,get_Max_date
from .DDSClient import *
from main import dataUtil
from main import weights

import logging
from dotenv import load_dotenv
from os import environ
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.signal import medfilt

import os

from django.http import JsonResponse
import json
import yfinance as yf

# Import HttpResponse module
# from django.http.response import HttpResponse

# Create your views here.

windows = [30, 60, 90, 120]
quantiles = [0.25, 0.75]

from requests_cache import CacheMixin, SQLiteCache, CachedSession
import json
import re

session = CachedSession(cache_name='yfinance.cache', expire_after=300)

def printJSON(jobj):
    print('Type is: ', type(jobj))
    for r in jobj:
        print('R Type is: ', type(r), '\t', r)

# Function to recursively convert numeric values from string to float
def convert_numeric_values(data):
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = convert_numeric_values(value)
    elif isinstance(data, list):
        for i in range(len(data)):
            data[i] = convert_numeric_values(data[i])
    elif isinstance(data, str):
        if re.match(r'^-?\d+(?:\.\d+)?$', data):
            print(f'detect-{data}')
            data = float(data)
    
    return data

def getOptions(ticker, PnC, strike, expiration):
    exp_dt = datetime.strptime(expiration, "%Y-%m-%d")
    today = date.today()
    print(f'-->getOptions({ticker},{PnC},{strike},{expiration},{exp_dt},{today})')
    pclose = -0.001
    op_price = -0.001
    if (today > exp_dt.date()):
        print(f'  expiration: {exp_dt} is old\n')
        return op_price, pclose
    
    asset = yf.Ticker(ticker, session=session)
    histdata = asset.history()
    if len(histdata)>0:
        pclose = asset.history().iloc[-1].Close
        pclose = float("{:.2f}".format(pclose))
        try:
            opts = asset.option_chain(expiration)
            if PnC == 'P':
                op = opts.puts[opts.puts['strike'] == strike]
                # print(opts.puts)
            else:
                op = opts.calls[opts.calls['strike'] == strike]
                # print(opts.calls)
            if len(op)>0:
                opt = op.head(1).reset_index()
                op_price = op.iloc[0].bid
            else:
                print(f'{ticker} {strike}{PnC} not found\n')
        except Exception as error:
            print(error)
    return op_price, pclose

def getStopPercent(sym, stop, last, op_type):
    if last != 0:
        if op_type == 'P':
            stopperc =  (last-stop)/last
        else:
            stopperc = (stop-last)/last
    else:
        stopperc = 0.0
    res = round(stopperc * 100,1)
    print(f'{sym} - {stop} - {op_type} - {last} - {stopperc} -> {res}')
    return res
    
def IsOTM(last, strike, pnc):
    if ((pnc=='P') and (last < strike)) or ((pnc =='C') and (last > strike)):
        return True
    else:
        return False
def adjValue(last, strike, pnc, oprice):
    if pnc=='P':
        return oprice-(strike-last)
    else:
        return oprice-(last-strike)

def etfoptionsmon(request):
    showCol = ['Date','Type','Trend','Symbol','Expiration','PnC','L_Strike','H_Strike','Entry','Target','Stop','Stop%','Last','OPrice','Reward%','adjOPrice','AdjReward%']
    # df = load_df_SQL(f'call Trading.sp_etf_trades;')
    df = dataUtil.load_df_Trade('ETF', f'call Trading.sp_etf_trades_v2;')
    logging.info(df)
    df['Date'] = df['Date'].astype(str)
    df['Expiration'] = df['Expiration'].astype(str)
    df['Stop%'] = np.nan
    df['OPrice'] = df['O_bid']
    df['Reward%'] = np.nan
    # df['Last'] = np.nan
    df['adjOPrice'] = np.nan
    df['AdjReward%'] = np.nan
    # DataSVR = defaultTCPClient()
    for ix, row in df.iterrows():
        logging.debug(f"ix:{ix}, row:{row}")
        if pd.isnull(row.L_Strike):
            # op_bid, last = getOptions(row.Symbol, row.PnC, row.H_Strike, row.Expiration)
            # rec = DataSVR.snapshot(row.Symbol)
            # if rec['header'] != 'error':
            #     last = float(rec['137'])
            # df.at[ix, 'OPrice'] = op_bid
            # df.at[ix, 'Last'] = last
            df.at[ix, 'Stop%'] = getStopPercent(row.Symbol, row.Stop, row.Last, row.PnC)
    df['adjOPrice'] = df.apply(lambda row: adjValue(row['Last'],row['H_Strike'],row['PnC'], row['OPrice']) if IsOTM(row['Last'], row['H_Strike'], row['PnC']) else row['OPrice'], axis=1)
    df['AdjReward%'] = round(df['adjOPrice']/df['H_Strike']*100, 2)
    df['Reward%'] = round(df['OPrice']/df['H_Strike']*100, 2)

    df = df[showCol]
    js_str = df.to_json(orient='records')
    stock_data = json.loads(js_str)
    stock_json = json.dumps(stock_data)
    logging.debug(f'stock_data_json:  {stock_json}')
    return render(request, 'main/etfoptionsmon.html', {'stock_data_json': stock_json})

def optionsmon(request):
    # messages.info(request, f'Start Process Data!')
    showCol = ['Date','Symbol','Expiration','PnC','Strike','Entry1','Entry2','Target','Stop','Stop%','Trade_Status','Description', 'OPrice','Reward%','Last']
    df = dataUtil.load_df_Trade('STK', f'call Trading.sp_stock_trades_V3;')
    print(df.info())
    df['Date'] = df['Date'].astype(str)
    df['Expiration'] = df['Expiration'].astype(str)
    df['Stop%'] = np.nan
    df['OPrice'] = df['O_bid']
    df['Reward%'] = np.nan
    # df['Last'] = np.nan
    df['adjOPrice'] = np.nan
    df['AdjReward%'] = np.nan
    # DataSVR = defaultTCPClient()
    for ix, row in df.iterrows():
        # op_bid, last = getOptions(row.Symbol, row.PnC, row.Strike, row.Expiration)
        # rec = DataSVR.snapshot(row.Symbol)
        # if rec['header'] != 'error':
        #     last = float(rec['last'])
        # df.at[ix, 'OPrice'] = op_bid
        # df.at[ix, 'Last'] = last
        # print(f"ix:{ix}, row:{row}")
        df.at[ix, 'Stop%'] = getStopPercent(row.Symbol, row.Stop, row.Last, row.PnC)
    df['adjOPrice'] = df.apply(lambda row: adjValue(row['Last'],row['Strike'],row['PnC'], row['OPrice']) if IsOTM(row['Last'], row['Strike'], row['PnC']) else row['OPrice'], axis=1)
    df['AdjReward%'] = round(df['adjOPrice']/df['Strike']*100, 2)
    df['Reward%'] = round(df['OPrice']/df['Strike']*100, 2)
    
    df = df[showCol]
    js_str = df.to_json(orient='records')
    stock_data = json.loads(js_str)
    stock_json = json.dumps(stock_data)
    logging.debug(f'stock_data_json:  {stock_json}')
    # messages.info(request, f'Retreive data done!')
    return render(request, 'main/optionsmon.html', {'stock_data_json': stock_json})

def go_Option_featuresV2(ticker, eod_draw, pdraw, cdraw, h=800, w=1000):
    fig = make_subplots(rows=5, cols=1, row_heights=[0.35, 0.1,0.35,0.1,0.1],  shared_xaxes=True,
                    subplot_titles=(f'{ticker} Put options',f'{ticker} Put ImpVol',f'{ticker} Call options',
                                    f'{ticker} Call ImpVol',f'{ticker} Put/Call ratio'),
                    vertical_spacing=0.02)
    fig.add_trace(go.Scatter(x=eod_draw.Date.values, y=eod_draw["AdjClose"].values,mode="lines",
                            line=dict(width=4),name="last"), row=1, col=1)
    fig.add_trace(go.Scatter(x=pdraw.Date.values, y=pdraw.MaxVolStrike.values,mode="lines",line=dict(width=2,dash="dot"),
                            name="max. Vol put strike"), row=1, col=1)
    fig.add_trace(go.Scatter(x=pdraw.Date.values, y=pdraw.MaxOIStrike.values,mode="lines",line=dict(width=1),
                            name="max. OI put strike"), row=1, col=1)

    fig.add_trace(go.Scatter(x=pdraw.Date.values, y=pdraw.MaxVolImpVol.values,mode="lines",line=dict(width=2,dash="dot"), 
                             name="Put Max Vol Strike ImpVol"), row=2, col=1)
    fig.add_trace(go.Scatter(x=pdraw.Date.values, y=pdraw.MaxOIImpVol.values,mode="lines",name="Put Max OI Strike ImpVol"),
                row=2, col=1)
    
    fig.add_trace(go.Scatter(x=eod_draw.Date.values, y=eod_draw["AdjClose"].values,mode="lines",
                            line=dict(width=4),name="last"), row=3, col=1)
    fig.add_trace(go.Scatter(x=cdraw.Date.values, y=cdraw.MaxVolStrike.values,mode="lines",line=dict(width=2,dash="dot"),
                            name="max. Vol call strike"), row=3, col=1)
    fig.add_trace(go.Scatter(x=cdraw.Date.values, y=cdraw.MaxOIStrike.values,mode="lines",line=dict(width=1),
                            name="max. OI call strike"), row=3, col=1)

    fig.add_trace(go.Scatter(x=cdraw.Date.values, y=cdraw.MaxVolImpVol.values,mode="lines",line=dict(width=2,dash="dot"), 
                             name="Call Max OI Strike ImpVol"), row=4, col=1)
    fig.add_trace(go.Scatter(x=cdraw.Date.values, y=cdraw.MaxOIImpVol.values,mode="lines",name="Call MaxStrike ImpVol"),
                row=4, col=1)

    fig.add_trace(go.Scatter(x=cdraw.Date.values, y=cdraw.PutCallratio.values,mode="lines",name="Put Call ratio"),
                row=5, col=1)
    fig.add_trace(go.Scatter(x=[cdraw.Date.values[0],cdraw.Date.values[-1]], y=[0.7, 0.7],mode="lines",
                             line=dict(width=2,dash="dash",color="black"), name="0.7 P/C ratio"),row=5, col=1)

    fig.update_layout(
                    dragmode='pan', 
                    hovermode='x unified',
                    height=1200, width=1000,
                    margin=dict(b=20, t=0, l=0, r=40))

    fig.update_traces(xaxis='x')

    return fig

def go_Option_features(ticker, eod_draw, pdraw, cdraw, h=800, w=1000):
    fig = make_subplots(rows=4, cols=1, row_heights=[0.65,0.15,0.1,0.1],  shared_xaxes=True,
                            subplot_titles=[f'{ticker} last vs max. Strike of OI for Put/Call',
                                            f'{ticker} Put/Call ratio', f'{ticker}: ImpVol of max. Strike of OI for Put',
                                            f'{ticker}: ImpVol of max. Strike of OI for Call'],
                            vertical_spacing=0.02)
    fig.add_trace(go.Scatter(x=eod_draw.Date.values, y=eod_draw["AdjClose"].values,mode="lines",line=dict(width=4),name="last"),
                row=1, col=1)
    fig.add_trace(go.Scatter(x=pdraw.Date.values, y=pdraw.MaxOIStrike.values,mode="lines",line=dict(width=1),
                            name="max. put strike"), row=1, col=1)
    fig.add_trace(go.Scatter(x=cdraw.Date.values, y=cdraw.MaxOIStrike.values,mode="lines",line=dict(width=1),
                            name="max. call strike"), row=1, col=1)
    fig.add_trace(go.Scatter(x=cdraw.Date.values, y=cdraw.PutCallratio.values,mode="lines",name="Put Call ratio"),
                row=2, col=1)
    fig.add_trace(go.Scatter(x=[cdraw.Date.values[0],cdraw.Date.values[-1]], y=[0.7,0.7],mode="lines",name="0.7 P/C ratio"),
                row=2, col=1)
    fig.add_trace(go.Scatter(x=cdraw.Date.values, y=pdraw.MaxOIImpVol.values,mode="lines",name="Put MaxStrike ImpVol"),
                row=3, col=1)
    fig.add_trace(go.Scatter(x=cdraw.Date.values, y=cdraw.MaxOIImpVol.values,mode="lines",name="Call MaxStrike ImpVol"),
                row=4, col=1)
    fig.update_layout(height=h, width=w)
    return fig

def go_DC_SLT(decomp, STL, titles, h, w):
    # fig = make_subplots(rows=4, cols=1, row_heights =[0.35, 0.15, 0.35, 0.15], shared_xaxes=True,
    fig = make_subplots(rows=3, cols=1, row_heights =[0.5, 0.25,0.25], shared_xaxes=True,
                        subplot_titles=titles,
                        vertical_spacing=0.02)

    ser = decomp.trend
    fig.add_trace(
        go.Scatter(x=ser.index, y=ser.values, name="Decomp Trend"),
        row=1, col=1
    )
    ser = decomp.observed
    fig.add_trace(
        go.Scatter(x=ser.index, y=ser.values, name="Decomp Close"),
        row=1, col=1
    )
    ser = decomp.seasonal
    fig.add_trace(
        go.Scatter(x=ser.index, y=ser.values, name="Decomp Seasonal"),
        row=2, col=1
    )
    # ser = STL.trend
    # fig.add_trace(
    #     go.Scatter(x=ser.index, y=ser.values, name="STL Trend"),
    #     row=3, col=1
    # )
    # ser = STL.observed
    # fig.add_trace(
    #     go.Scatter(x=ser.index, y=ser.values, name="STL Close"),
    #     row=3, col=1
    # )
    ser = STL.seasonal
    fig.add_trace(
        go.Scatter(x=ser.index, y=ser.values, name="STL Seasonal"),
        row=3, col=1
    )
    fig.update_layout(height=h, width=w)
    return fig

def go_decomposit(decomp, titles, h, w):
    fig = make_subplots(rows=2, cols=1, row_heights =[0.7, 0.3], shared_xaxes=True,
                        subplot_titles=titles,
                        vertical_spacing=0.02)

    ser = decomp.trend
    fig.add_trace(
        go.Scatter(x=ser.index, y=ser.values, name="Trend"),
        row=1, col=1
    )
    ser = decomp.observed
    fig.add_trace(
        go.Scatter(x=ser.index, y=ser.values, name="Close"),
        row=1, col=1
    )
    ser = decomp.seasonal
    fig.add_trace(
        go.Scatter(x=ser.index, y=ser.values, name="Seasonal"),
        row=2, col=1
    )
    fig.update_layout(height=h, width=w)
    return fig

def Plot_Vol_Cone(symbol, data, startdt, enddt, win):
    res = Volality_Cone(symbol, data, win)
    lwidth = 4
    marksize=8
    layout=dict(title=f'{symbol} Volatility Cones ',
                xaxis=dict(tickvals=windows),
                margin=dict(l=30,r=30,b=30,t=50),
                width=800, height=600)
    realized=go.Scatter(x=windows, y=res["realized"], name="Realized",
                        mode="lines+markers", line=dict(dash='dash',width=lwidth),
                        marker=dict(symbol='square', size=int(marksize*1.3)))   # "star-diamond"
    minval = go.Scatter(x=windows, y=res["min"], name="Min",
                        mode="lines+markers", line=dict(width=lwidth),
                        marker=dict(symbol="circle", size=marksize))
    maxval = go.Scatter(x=windows, y=res["max"], name="Max",
                        mode="lines+markers", line=dict(width=lwidth),
                        marker=dict(symbol="circle", size=marksize))
    median = go.Scatter(x=windows, y=res["median"], name="Median",
                        mode="lines+markers", line=dict(width=lwidth),
                        marker=dict(symbol="circle", size=marksize))
    top_q = go.Scatter(x=windows, y=res["top_q"], name=f"{quantiles[1] * 100:.0f} Prctl",
                        mode="lines+markers", line=dict(width=lwidth),
                        marker=dict(symbol="circle", size=marksize))
    bottom_q = go.Scatter(x=windows, y=res["bottom_q"], name=f"{quantiles[0] * 100:.0f} Prctl",
                        mode="lines+markers", line=dict(width=lwidth),
                        marker=dict(symbol="circle", size=marksize))
    data=[maxval, top_q, median, bottom_q, minval, realized]
    fig = go.Figure(data=data, layout=layout)
    return fig

def strike_str(id, row, filterName):
    if filterName is None:
        filterName = "OI"
    r = '{} {}({})-{:,.0f}'.format(id, row['strike'],row['OptionType'],row[filterName])
    return r

def Trend_slow_fast(indf, title, h, w):
    marksize=8
    DFsize = 130
    indf['sma5'] = indf['Close'].rolling(5).mean()
    indf['sma20'] = indf['Close'].rolling(20).mean()
    indf['gf'] = gaussian_filter(indf['Close'], sigma=1)
    indf['med'] = medfilt(indf['Close'], 5)
    indf['gfsma5'] = indf['gf'].rolling(5).mean()
    indf['gfsma20'] = indf['gf'].rolling(20).mean()

    df=indf[-DFsize:]
    fig = make_subplots(rows=2, cols=1, 
                        vertical_spacing=0.02, shared_xaxes =True)

    fig.add_trace(
        go.Scatter(x=df['Date'], y=df['sma5'], name="SMA 5", line=dict(width=2, dash='dash', color="rgb(255,50,50)")),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['Date'], y=df['sma20'], name="SMA 20", line=dict(width=2, dash='dash', color='green')),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['Date'], y=df['Close'], name="PClose", line=dict(width=2)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['Date'], y=df['gfsma5'], name="SMA 5-gf", line=dict(width=3, dash='dash', color="rgb(255,50,50)")),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['Date'], y=df['gfsma20'], name="SMA 20-gf", line=dict(width=3, dash='dash', color='green')),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['Date'], y=df['gf'], name="Gaussian", line=dict(width=2)),
        row=2, col=1
    )
    # fig.add_trace(
    #     go.Scatter(x=df['Date'], y=df['Close'], name="PClose", line=dict(width=4)),
    #     row=2, col=1
    # )
    # fig.add_trace(
    #     go.Scatter(x=df['Date'], y=df['med'], name="Median", line=dict(width=1)),
    #     row=3, col=1
    # )
    # fig.add_trace(
    #     go.Scatter(x=df['Date'], y=df['Close'], name="PClose", line=dict(width=4)),
    #     row=3, col=1
    # )
    # fig.add_trace(
    #     go.Candlestick(x=df['Date'],
    #                 open=df['Open'],
    #                 high=df['High'],
    #                 low=df['Low'],
    #                 close=df['Close']),
    #     row=3, col=1
    # )
    fig.update_layout(height=h, width=w)
    return fig

def Trend_slow_fast_orig(indf, title):
    marksize=8
    DFsize = 130
    indf['sma5'] = indf['Close'].rolling(5).mean()
    indf['sma20'] = indf['Close'].rolling(20).mean()
       
    df=indf[-DFsize:]
    print(df.head(10))
    layout = dict(title_text=title, title_x=0.5,
                     width=1300,
                     height=600,
                     margin=dict(l=30,r=30,b=30,t=50),
                     paper_bgcolor="LightSteelBlue",
                     xaxis_rangeslider_visible=False)
    g_data=[]
    g_data.append(go.Candlestick(x=df['Date'],
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close']))
    g_data.append(go.Scatter(x=df['Date'], y=df['sma5'], name="SMA 5", line=dict(width=3, color="rgb(50,150,200)")))
    g_data.append(go.Scatter(x=df['Date'], y=df['sma20'], name="SMA 20", line=dict(width=3, color='rgb(170,200,50)')))
    fig = go.Figure(data=g_data, layout=layout)
    return fig

def OptStrikes(df, title, cStrikeList, pStrikeList, strikeFilterN):
    marksize=8
    layout = dict(title_text=title, title_x=0.5,
                     width=900,
                     height=600,
                     margin=dict(l=30,r=30,b=30,t=50),
                     paper_bgcolor="LightSteelBlue",
                     xaxis_rangeslider_visible=False)
    g_data=[]
    g_data.append(go.Candlestick(x=df['Date'],
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close']))
    g_data.append(go.Scatter(x=[df.Date.iloc[0], df.Date.iloc[-1]], y=[cStrikeList.iloc[0].strike,cStrikeList.iloc[0].strike], name=strike_str("+1", cStrikeList.iloc[0], strikeFilterN),
                        mode="lines+markers", line=dict(width=5, color="green"),
                        marker=dict(symbol="circle", size=marksize)))
    for i in range(1, len(cStrikeList)):
        g_data.append(go.Scatter(x=[df.Date.iloc[0], df.Date.iloc[-1]], y=[cStrikeList.iloc[i].strike,cStrikeList.iloc[i].strike], name=strike_str(f"+{i+1}", cStrikeList.iloc[i], strikeFilterN),
                            mode="lines+markers", line=dict(width=1, dash="dash", color="green"),
                            marker=dict(symbol="circle", size=marksize)))

    g_data.append(go.Scatter(x=[df.Date.iloc[0], df.Date.iloc[-1]], y=[pStrikeList.iloc[0].strike,pStrikeList.iloc[0].strike], name=strike_str("-1", pStrikeList.iloc[0], strikeFilterN),
                        mode="lines+markers", line=dict(width=5, color="red"),
                        marker=dict(symbol="circle", size=marksize)))
    for i in range(1, len(pStrikeList)):
        g_data.append(go.Scatter(x=[df.Date.iloc[0], df.Date.iloc[-1]], y=[pStrikeList.iloc[i].strike,pStrikeList.iloc[i].strike], name=strike_str(f"-{i+1}",pStrikeList.iloc[i], strikeFilterN),
                            mode="lines+markers", line=dict(width=1, dash="dash", color="red"),
                            marker=dict(symbol="circle", size=marksize)))

    fig = go.Figure(data=g_data, layout=layout)

    return fig

def OptStrikes_old(df, title, cStrikeList, pStrikeList):
    layout = dict(title_text=title, title_x=0.5,
                     width=800,
                     height=600,
                     margin=dict(l=30,r=30,b=30,t=50),
                     paper_bgcolor="LightSteelBlue",
                     xaxis_rangeslider_visible=False)
    g_data=[]
    g_data.append(go.Candlestick(x=df['Date'],
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close']))

    fig = go.Figure(data=g_data, layout=layout)

    # 1st strike is large width line
    text_size = 25
    fig.add_hline(y=cStrikeList[0], line_color="green", line_width=5,
                  annotation_text=f"+1 {cStrikeList[0]} CALL", annotation_font_size=text_size)
    for i in range(1, len(cStrikeList)):
        fig.add_hline(y=cStrikeList[i], line_color="green", line_width=2, line_dash="dash",
                      annotation_text=f"+{i+1} {cStrikeList[i]} CALL", annotation_font_size=text_size)
    fig.add_hline(y=pStrikeList[0], line_color="red", line_width=5,
                  annotation_text=f"-1 {pStrikeList[0]} PUT", annotation_font_size=text_size)
    for i in range(1, len(pStrikeList)):
        fig.add_hline(y=pStrikeList[i], line_color="red", line_width=2, line_dash="dash",
                      annotation_text=f"-{i+1} {pStrikeList[i]} PUT", annotation_font_size=text_size)
    return fig

def ConvertWeekly(inDF):
    logic = {'Open'  : 'first',
         'High'  : 'max',
         'Low'   : 'min',
         'Close' : 'last',
         'AdjClose': 'last',
         'Volume': 'sum'}

    df = inDF.resample('W').apply(logic)
    df.index = df.index - pd.tseries.frequencies.to_offset("6D")
    return df

def simpleTop(inDf):
    strike_l = list(inDf['strike'].unique())
    strike_l.sort()
    rows = []
    for stk in strike_l:
        s_df = inDf[inDf['strike']==stk].reset_index()
        oi_amount = s_df.apply(lambda row: row['lastPrice'] * row['openInterest'], axis=1)
        # print(f"{stk} Amount : ", oi_amount)
        totalOI = int(s_df[['openInterest']].sum())
        totalAmt = oi_amount.sum()
        rec = {'strike': stk, 'OptionType': s_df['OptionType'].iloc[0], 'OI': totalOI, 'lDate': s_df['Date'].iloc[0], 'Amount':totalAmt, }
        # display(rec)
        rows.append(rec)
    OI_info = pd.DataFrame(rows).sort_values(by='strike', ascending=False)
    return OI_info

def strikeFilter(ticker, limit):
    DBMKTDATA=environ.get("DBMKTDATA")
    TBLOPTCHAIN=environ.get("TBLOPTCHAIN")

    mktdate = dataUtil.get_Max_date(f'{DBMKTDATA}.{TBLOPTCHAIN}')
    query=f"select * from {DBMKTDATA}.{TBLOPTCHAIN} where Date=\'{mktdate}\' and UnderlyingSymbol=\'{ticker}\';"
    logging.info(f"strikeFilter.{query}")
    i_df = dataUtil.load_df_SQL(query)
    df = i_df[i_df['lastPrice'] > 0.05]
    putdata = df[(df['OptionType'] == 'put') & (df['strike'] < df['UnderlyingPrice'])]
    print("Put data size: ", len(putdata))
    calldata = df[(df['OptionType'] == 'call') & (df['strike'] > df['UnderlyingPrice'])]
    print("Call data size: ", len(calldata))
    OI75 = i_df['openInterest'].quantile(0.25)
    logging.info(f"75% : {OI75}")
    put75 = putdata[putdata['openInterest']>OI75]
    logging.info(f"75% Put data threshold: {len(put75)}")
    call75 = calldata[calldata['openInterest']>OI75]
    logging.info(f"75% Call data threshold: {len(call75)}")
    StrikeFilter = environ.get("StrikeFilter")
    f_put_df = simpleTop(put75).sort_values(by=StrikeFilter, ascending=False).head(limit)
    f_call_df = simpleTop(call75).sort_values(by=StrikeFilter, ascending=False).head(limit)
    result = pd.concat([f_call_df, f_put_df])
    return result


def ProcessTickerOpChart(weeklyDF, ticker, strike_limit=3):
    StrikeFilter = environ.get("StrikeFilter")
    if StrikeFilter is not None:
        df = strikeFilter(ticker, strike_limit)
        label = f'{ticker} top {strike_limit} strikes-Weekly by {StrikeFilter}'
    else:
        df = dataUtil.load_df_Strike(ticker, f'call GlobalMarketData.max_options_strike_byticker(\'{ticker}\', {strike_limit});')
        label = f'{ticker} top {strike_limit} strikes-Weekly'
    # df = DU.load_df_SQL(f'call GlobalMarketData.max_options_strike_byticker(\'{ticker}\', {strike_limit});')

    CallS = df[df['OptionType'] == 'call']
    print("*** CALLS ***", CallS)
    PutS = df[df['OptionType'] == 'put']
    print("*** PUTS ***", PutS)
    if len(df)==0:
        title = f'{ticker} has no options data'
        return None
    elif 'lDate' in df.columns:
        title = f'{label} on ***{df.iloc[0].lDate}***'
    else:
        title = label
    return OptStrikes(weeklyDF.reset_index(), title, CallS, PutS, StrikeFilter)

def resume(request):
    pdffile =  Router.objects.last()
    return render(request, 'main/pdffile.html', context={'pdffile':pdffile})

def home(response):
    return render(response, "main/home.html", {})

def about(response):
    return render(response, "main/about.html", {})

def reports(response):
    # Define Django project base directory
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Define the full file path
    path = BASE_DIR + '/perfreports/Files/'
    file_list = sorted(os.listdir(path))
    print('reports(): ', file_list)
    return render(response, "main/reports.html", {'items': file_list})

def volreports(response):
    # Define Django project base directory
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Define the full file path

    path = BASE_DIR + '/perfreports/etf_list/'
    etf_list = sorted(os.listdir(path))
    path = BASE_DIR + '/perfreports/stock_list/'
    stock_list = sorted(os.listdir(path))
    path = BASE_DIR + '/perfreports/us-cn_stock_list/'
    cn_stock_list = sorted(os.listdir(path))
    context = {"etf_list":etf_list, "stock_list":stock_list, "cn_stock_list": cn_stock_list}
    print(f'volreports:  {context}')
    return render(response, "main/volatility.html", context)

def portrebalance(request):
    portfolio = request.GET.get('pid')
    port_value = request.GET.get('pvalue')
    print(f'portrebalance({portfolio}, {port_value})')
    # enddt = datetime.now().date() - timedelta(days = 1)
    # startdt = enddt - timedelta(days = 3*365)
    # startdt_2 = (enddt - timedelta(days = 365)).strftime('%Y-%m-%d')
    msg = 'Please enter Portfolio Name'
    port_w_data = None
    if portfolio is not None:
        we_df = weights.get_json_by_record_type(dataUtil.get_DBengine(), portfolio)
        if len(we_df)>0:
            logging.debug(we_df)
            msg = f'{portfolio} weights'
            js_str = we_df.to_json(orient='records')
            port_w_data = json.dumps(json.loads(js_str))
        else:
            msg = f'{portfolio} has no weighting data'
    else:
        return render(request, "main/portrebalance.html")

    context = {"chart_msg": msg, "weights_json": port_w_data}
    logging.debug(f'Port-Rebalance:  {context}')
    return render(request, "main/portrb_info.html", context=context)


def options(request):
    ticker = request.GET.get('q')
    print(f'index({ticker})')
    enddt = datetime.now().date() - timedelta(days = 1)
    startdt = enddt - timedelta(days = 3*365)
    startdt_2 = (enddt - timedelta(days = 365)).strftime('%Y-%m-%d')
    msg = 'Please enter stock symbol'
    chart_flag = False
    charts = dict()
    if ticker is not None:
   
        df = dataUtil.load_eod_price(ticker, startdt, enddt)
        if len(df) > 0:
            chart_flag = True
            df['Date'] = pd.to_datetime(df['Date'])
            SDF = df.set_index('Date')
            wkDF = ConvertWeekly(SDF)

            print(wkDF.info())
            print(wkDF.index)

            ywkDF = wkDF[wkDF.index>startdt_2]
            fig = ProcessTickerOpChart(ywkDF, ticker, 5)
            if fig:
                charts["Option Strikes Chart"] = plot(fig, output_type="div")

            ydyDF = SDF[SDF.index>startdt_2]
            if len(ydyDF)>0:
                cone_fig = Plot_Vol_Cone(ticker, ydyDF, startdt, enddt, windows)
                charts["Option Cones Chart"] = plot(cone_fig, output_type="div")

            # ddfo = pd.DataFrame()
            # ddfo[ticker] = wkDF["AdjClose"]
            # print('old head: ', ddfo.head(2))
            # print('old Index: ', ddfo.index)

            # plot for last 60 days
            dailydf = df[len(df)-88:-1]
            print('new head: ', dailydf.head(2))
            print('new tail: ', dailydf.tail(2))
            
            for sdays in [5, 22]:
                print(sdays)
                dataset = pd.DataFrame()
                dataset[ticker] = dailydf.reset_index()["AdjClose"]
                print('data list: ', dataset)
                dmode = "additive"
                decomposition_results = seasonal_decompose(
                    dataset,
                    model=dmode,
                    period=sdays
                )
                stl_decomposition = STL(dataset, period=sdays).fit()
                titles=[f'{ticker} Trend/Seasonal-{sdays} days in mode {dmode}', f'{dmode} Seasonal', 'STL Seasonal']
                fig = go_DC_SLT(decomposition_results, stl_decomposition, titles, h=800, w=1000)
                charts[f"Trend/Seasonal-{sdays} Chart"] = plot(fig, output_type="div")

            # fig = Trend_slow_fast(dailydf, f'{ticker}: Trend slow/fast daily.', h=1000, w=1000)
            # charts["Trend slow/fast"] = plot(fig, output_type="div")
            sql=f"SELECT * FROM GlobalMarketData.option_features where Symbol = \'{ticker}\'";
            draw = dataUtil.load_df_SQL(sql)
            if len(draw)>0:
                draw['Date'] = pd.to_datetime(draw['Date'])
                fig = px.scatter_3d(draw, x="Date", y="MaxOIStrike",z="last", color="OptionType")
                charts[f'{ticker} OpenInterest in 3D'] = plot(fig, output_type="div")
                pdraw = draw[draw.OptionType=="put"]
                cdraw = draw[draw.OptionType=="call"]
                begindt, enddt = draw['Date'].values[0], draw['Date'].values[-1]
                logging.debug(f' options features from {begindt} to {enddt}')
                eod_draw = df[(df['Date']>=begindt) & (df['Date']<=enddt)]
                fig = go_Option_featuresV2(ticker=ticker, eod_draw=eod_draw, pdraw=pdraw, cdraw=cdraw, h=800, w=1000)
                charts[" Options features summary"] = plot(fig, output_type="div")

            msg = 'Chart is created'
        else:
            msg = f'{ticker} has no option data'
    else:
        return render(request, "main/options.html")

    context = {"chart_msg": msg, "charts": charts, "chart_flag": chart_flag}
    # print('options.context: ', context)
    return render(request, "main/options_info.html", context=context)

def pyscript(request):
    return render(request, "main/pyscript.html")

def usstockpick(response):
    plist = Predicts.objects.all()
    print('plist type is ', type(plist))
    for item in plist:
        print(item.__str__())
    return render(response, "main/usstockpick.html", {'plist':plist})

########### register here #####################################
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)# Import mimetypes module
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            current_site = get_current_site(request)
            mail_subject = 'Activation link has been sent to your email id'
            message = render_to_string('main/acc_active_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            to_email = form.cleaned_data.get('email')
            ######################### mail system ####################################
            email = EmailMessage(
                mail_subject, message, to=[to_email], from_email='thomas.choi@neuralmatrixllc.com'
            )
            email.send()
            ##################################################################
            return HttpResponse('Please confirm your email address to complete the registration')
    else:
        form = UserRegisterForm()
    return render(request, 'main/register.html', {'form': form, 'title':'reqister here'})

    ################ login forms###################################################
def Login(request):
    if request.method == 'POST':

        # AuthenticationForm_can_also_be_used__
        print("In View.Login.")
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username = username, password = password)
        if user is not None:
            form = login(request, user)
            messages.success(request, f' wecome {username} !!')
            return redirect('home')
        else:
            messages.info(request, f'account done not exit plz sign in')
    form = AuthenticationForm()
    return render(request, 'main/login.html', {'form':form, 'title':'log in'})

def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return HttpResponse('Thank you for your email confirmation. Now you can login your account.')
    else:
        return HttpResponse('Activation link is invalid!')

def volatility(request, filename=''):
    print(f'volatility({filename})')
    x= filename.split('-')
    if x[0] == "etf":
        return download_file(request, x[1], f'/perfreports/etf_list/')
    elif x[0] == "us":
        return download_file(request, x[1], f'/perfreports/stock_list/')
    elif x[0] == "cn":
        return download_file(request, x[1], f'/perfreports/us-cn_stock_list/')

def performance(request, filename=''):
    print(f'performance({filename})')
    return download_file(request, filename, '/perfreports/Files/')

def download_file(request, filename='', sub_folder=''):
    if filename != '':
        # Define Django project base directory
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Define the full file path
        filepath = BASE_DIR + sub_folder + filename
        print('Try to open: ', filepath)
        try:
            response = FileResponse(open(filepath, 'rb'), content_type='application/pdf')
        except FileNotFoundError:
            raise Http404()
        # Return the response value
        return response
    else:
        # Load the template
        return render(request, 'main/reports.html')
