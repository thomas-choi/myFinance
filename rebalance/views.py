# rebalance/views.py

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from .models import Weight
import main.dataUtil as DU
import pandas as pd
import logging
import json
import math

def weights_by_port_name(request):
    port_name = request.GET.get('pid')
    port_value = request.GET.get('pvalue')
    print(f'weights_by_port_name({port_name}, {port_value})')
    weights = Weight.objects.using('trading').filter(port_name=port_name)
    return render(request, 'weights_table.html', {'weights': weights})

def calc_shares(row):
    if row['last'] > 0:
        return round(row['amount'] / row['last'])
    else:
        return 0

def get_weights_details(request):
    id = request.GET.get('id')
    port_value = float(request.GET.get('pvalue'))
    logging.info(f'get_weights_details({id}, {port_value})')
    weight = get_object_or_404(Weight.objects.using('trading'), id=id)
    data = {
        'weights': weight.weights_list  # Use the property to get the parsed weights
    }
    w_df = weight.get_weights_df()
    logging.debug("=====  Pre-Process of Shares =====")
    logging.debug(w_df)
    w_sum = w_df['weight'].sum()
    if w_sum > 1:
        logging.error(f"Port_ID:({id}) has total weight: {w_sum} > 1")
    sym_list = ','.join(map("'{0}'".format, w_df.index.to_list()))
    # sql_str = f"SELECT Symbol, last FROM GlobalMarketData.snapshot  where Symbol in ({sym_list});"
    slist2 = sym_list.replace("'", "\\'")
    sql_str = f"call GlobalMarketData.Symbol_FX_rates(\'{slist2}\');"
    logging.debug(sql_str)
    last_df = DU.load_df_SQL(sql_str)
    last_df = last_df.set_index(['Symbol'])
    logging.debug("===== last_df from DB =====")
    logging.debug(last_df)
    w_df['amount'] = (w_df['weight'] * port_value).apply(math.floor)
    # w_df['amount'] = (w_df['weight'] * port_value).round(2)
    if len(last_df)>0:
        w_df['Currency'] = last_df['Currency']
        w_df['rate'] = last_df['rate']
        w_df['last'] = round(last_df['last'] / w_df['rate'], 4)
        w_df['shares'] = w_df.apply(calc_shares, axis=1)
    else:
        w_df['last'] = 0.0
        w_df['shares'] = 0
    w_df.reset_index(inplace=True)
    logging.debug(w_df)
    df_dict = w_df.to_dict(orient='records')
    data = {
        'weights': df_dict,  # Use the property to get the parsed weights
        'total_w': w_sum
    }
    return JsonResponse(data)

def portweights(request):
    portfolio = request.GET.get('pid')
    port_value = request.GET.get('pvalue')
    logging.info(f'portweights({portfolio}, {port_value})')
    if portfolio is not None:
        weights = Weight.objects.using('trading').filter(port_name=portfolio)
        df = pd.DataFrame(columns=['ID','Date','Port Name','Risk Measure','Objective','Interval'])
        if len(weights)>0:
            msg = f'{portfolio} weightings.'
        else:
            msg = f'{portfolio} has no weighting data.'
        for w in weights:
            dt_str = w.date.strftime("%y-%m-%d")
            df.loc[len(df.index)] = [w.id, dt_str,w.port_name,w.risk_mes,w.obj_type,w.int_type]
        logging.debug(df)
        logging.debug(df.info())
        if len(df)>0:
            # df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
            js_str = df.to_json(orient='records')
            w_data = json.dumps(json.loads(js_str))
        context = {"chart_msg": msg, "weights_json": w_data, "weights": weights}
        print(context)
        return render(request, "portweights_info.html", context=context)
    else:
        return render(request, "portweights.html")
    
