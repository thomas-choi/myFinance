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
import plotly.graph_objects as go
# import plotly.io as pio
from datetime import datetime, timedelta
# import matplotlib.pyplot as plt

from predicts.models import Predicts
from .forms import UserRegisterForm
from .token import account_activation_token
from .models import Router
from .Volatility import Volality_Cone
from .dataUtil import load_eod_price, get_Max_Options_date, load_df_SQL

import logging
from dotenv import load_dotenv
from os import environ

# Import mimetypes module
# import mimetypes
# import os module
import os
# Import HttpResponse module
# from django.http.response import HttpResponse

# Create your views here.

load_dotenv("/home/twmchoi2022/myFinData/Prod_config/Stk_eodfetch.env") #Check path for env variables
logging.getLogger().setLevel(logging.INFO)

windows = [30, 60, 90, 120]
quantiles = [0.25, 0.75]

def go_DC_SLT(decomp, STL, titles, h, w):
    fig = make_subplots(rows=4, cols=1, row_heights =[0.39, 0.11, 0.39, 0.11], shared_xaxes=True,
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
    ser = STL.trend
    fig.add_trace(
        go.Scatter(x=ser.index, y=ser.values, name="STL Trend"),
        row=3, col=1
    )
    ser = STL.observed
    fig.add_trace(
        go.Scatter(x=ser.index, y=ser.values, name="STL Close"),
        row=3, col=1
    )
    ser = STL.seasonal
    fig.add_trace(
        go.Scatter(x=ser.index, y=ser.values, name="STL Seasonal"),
        row=4, col=1
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

def OptStrikes(df, title, cStrikeList, pStrikeList):
    marksize=8
    layout = dict(title_text=title, title_x=0.5,
                     width=900,
                     height=700,
                     margin=dict(l=30,r=30,b=30,t=50),
                     paper_bgcolor="LightSteelBlue",
                     xaxis_rangeslider_visible=False)
    g_data=[]
    g_data.append(go.Candlestick(x=df['Date'],
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close']))
    g_data.append(go.Scatter(x=[df.Date.iloc[0], df.Date.iloc[-1]], y=[cStrikeList[0],cStrikeList[0]], name=f"+1 {cStrikeList[0]} CALL",
                        mode="lines+markers", line=dict(width=5, color="green"),
                        marker=dict(symbol="circle", size=marksize)))
    for i in range(1, len(cStrikeList)):
        g_data.append(go.Scatter(x=[df.Date.iloc[0], df.Date.iloc[-1]], y=[cStrikeList[i],cStrikeList[i]], name=f"+{i+1} {cStrikeList[i]} CALL",
                            mode="lines+markers", line=dict(width=1, dash="dash", color="green"),
                            marker=dict(symbol="circle", size=marksize)))

    g_data.append(go.Scatter(x=[df.Date.iloc[0], df.Date.iloc[-1]], y=[pStrikeList[0],pStrikeList[0]], name=f"-1 {pStrikeList[0]} PUT",
                        mode="lines+markers", line=dict(width=5, color="red"),
                        marker=dict(symbol="circle", size=marksize)))
    for i in range(1, len(cStrikeList)):
        g_data.append(go.Scatter(x=[df.Date.iloc[0], df.Date.iloc[-1]], y=[pStrikeList[i],pStrikeList[i]], name=f"-{i+1} {pStrikeList[i]} PUT",
                            mode="lines+markers", line=dict(width=1, dash="dash", color="red"),
                            marker=dict(symbol="circle", size=marksize)))

    fig = go.Figure(data=g_data, layout=layout)

    return fig

def OptStrikes_old(df, title, cStrikeList, pStrikeList):
    layout = dict(title_text=title, title_x=0.5,
                     width=800,
                     height=700,
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

def ProcessTickerOpChart(weeklyDF, ticker, stk_num=3):
    DBMKTDATA=environ.get("DBMKTDATA")
    TBLOPTCHAIN=environ.get("TBLOPTCHAIN")
    maxDate, sec = get_Max_Options_date(f'{DBMKTDATA}.{TBLOPTCHAIN}', symbol=ticker)
    print(f'MaxDate: {maxDate}, Section:{sec}')
    query=f"SELECT * FROM {DBMKTDATA}.{TBLOPTCHAIN} where UnderlyingSymbol = \'{ticker}\' and \
    Date=\'{maxDate}\' and section = \'{sec}\' and strike < UnderlyingPrice and OptionType = \'put\' order by openInterest desc \
    limit {stk_num};"
    print(query)
    putDF = load_df_SQL(query)
    putDF.head()
    Cquery=f"SELECT * FROM {DBMKTDATA}.{TBLOPTCHAIN} where UnderlyingSymbol = \'{ticker}\' and \
    Date=\'{maxDate}\' and section = \'{sec}\' and strike > UnderlyingPrice and OptionType = \'call\' order by openInterest desc \
    limit {stk_num};"
    print(Cquery)
    callDF = load_df_SQL(Cquery)
    CallS, PutS = callDF.strike.values, putDF.strike.values
    print(CallS, PutS)
    title = f'{ticker} top {stk_num} strikes-Weekly'
    return OptStrikes(weeklyDF.reset_index(), title, CallS, PutS)

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

def options(request):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ticker = request.GET.get('q')
    print(f'index({ticker})')
    enddt = datetime.now().date() - timedelta(days = 1)
    startdt = enddt - timedelta(days = 3*365)
    startdt_2 = (enddt - timedelta(days = 365)).strftime('%Y-%m-%d')
    msg = 'Please enter stock symbol'
    chart_flag = False
    charts = dict()
    if ticker is not None:
        path = os.path.join(BASE_DIR, 'main', 'data', f'{ticker}.csv')
        if os.path.exists(path):
            df = pd.read_csv(path)
        else:
            df = load_eod_price(ticker, startdt, enddt)
            df.to_csv(path, index=False)
        if len(df) > 0:
            chart_flag = True
            df['Date'] = pd.to_datetime(df['Date'])
            SDF = df.set_index('Date')
            wkDF = ConvertWeekly(SDF)

            print(wkDF.info())
            print(wkDF.index)

            ywkDF = wkDF[wkDF.index>startdt_2]
            fig = ProcessTickerOpChart(ywkDF, ticker, 5)
            charts["Option Strikes Chart"] = plot(fig, output_type="div")

            ydyDF = SDF[SDF.index>startdt_2]
            cone_fig = Plot_Vol_Cone(ticker, ydyDF, startdt, enddt, windows)
            charts["Option Cones Chart"] = plot(cone_fig, output_type="div")

            ddf = pd.DataFrame()
            ddf[ticker] = wkDF["AdjClose"]

            dmode = "additive"
            decomposition_results = seasonal_decompose(
                ddf[ticker],
                model=dmode
            )
            stl_decomposition = STL(ddf[ticker]).fit()
            titles=[f'{ticker} Trend vs Close in mode {dmode}', f'{dmode} Seasonal', 'Trend vs Close in STL', 'STL Seasonal']
            fig = go_DC_SLT(decomposition_results, stl_decomposition, titles, h=1200, w=1100)
            charts["Trend/Seasonal Chart"] = plot(fig, output_type="div")

            msg = 'Chart is created'
        else:
            msg = f'{ticker} has no option data'
    else:
        return render(request, "main/options.html")

    context = {"chart_msg": msg, "charts": charts, "chart_flag": chart_flag}
    return render(request, "main/options_info.html", context=context)

def pyscript(request):
    return render(request, "main/pyscript.html")

def usstockpick(response):
    plist = Predicts.objects.all()
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
