# rebalance/views.py

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from .models import Weight
import main.dataUtil as DU
import pandas as pd
import logging
import json

def weights_by_port_name(request):
    port_name = request.GET.get('pid')
    port_value = request.GET.get('pvalue')
    print(f'weights_by_port_name({port_name}, {port_value})')
    weights = Weight.objects.using('trading').filter(port_name=port_name)
    return render(request, 'weights_table.html', {'weights': weights})

def get_weights_details(request):
    id = request.GET.get('id')
    port_value = float(request.GET.get('pvalue'))
    logging.info(f'get_weights_details({id}, {port_value})')
    weight = get_object_or_404(Weight.objects.using('trading'), id=id)
    data = {
        'weights': weight.weights_list  # Use the property to get the parsed weights
    }
    w_df = weight.get_weights_df()
    sym_list = ','.join(map("'{0}'".format, w_df.index.to_list()))
    sql_str = f"SELECT Symbol, last FROM GlobalMarketData.snapshot  where Symbol in ({sym_list});"
    logging.debug(sql_str)
    last_df = DU.load_df_SQL(sql_str)
    last_df = last_df.set_index(['Symbol'])
    logging.debug(last_df)
    w_df['amount'] = w_df['weight'] * port_value
    if len(last_df)>0:
        w_df['last'] = last_df['last']
        w_df['shares'] = (w_df['amount'] / w_df['last']).round(0)
    else:
        w_df['last'] = 0.0
        w_df['shares'] = 0
    w_df.reset_index(inplace=True)
    logging.debug(w_df)
    df_dict = w_df.to_dict(orient='records')
    data = {
        'weights': df_dict  # Use the property to get the parsed weights
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
    
