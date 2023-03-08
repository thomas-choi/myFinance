import math
import numpy as np

def standard_deviation(price_data, window=30, trading_periods=252, clean=True):

    log_return = (price_data["Close"] / price_data["Close"].shift(1)).apply(np.log)

    result = log_return.rolling(window=window, center=False).std() * math.sqrt(
        trading_periods
    )

    if clean:
        return result.dropna()
    else:
        return result

# Parkinson’s volatility uses the stock’s high and low price of the day rather than just
# close to close prices. It’s useful to capture large price movements during the day.
def parkinson(price_data, window=30, trading_periods=252, clean=True):

    rs = (1.0 / (4.0 * math.log(2.0))) * (
        (price_data["High"] / price_data["Low"]).apply(np.log)
    ) ** 2.0

    def f(v):
        return (trading_periods * v.mean()) ** 0.5

    result = rs.rolling(window=window, center=False).apply(func=f)

    if clean:
        return result.dropna()
    else:
        return result

# Garman-Klass volatility extends Parkinson’s volatility by taking into account the
# opening and closing price. As markets are most active during the opening and closing of a
#  trading session, it makes volatility estimation more accurate.
def garman_klass(price_data, window=30, trading_periods=252, clean=True):

    log_hl = (price_data["High"] / price_data["Low"]).apply(np.log)
    log_co = (price_data["Close"] / price_data["Open"]).apply(np.log)

    rs = 0.5 * log_hl ** 2 - (2 * math.log(2) - 1) * log_co ** 2

    def f(v):
        return (trading_periods * v.mean()) ** 0.5

    result = rs.rolling(window=window, center=False).apply(func=f)

    if clean:
        return result.dropna()
    else:
        return result

# Hodges-Tompkins volatility is a bias correction for estimation using an overlapping data sample
# that produces unbiased estimates and a substantial gain in efficiency
def hodges_tompkins(price_data, window=30, trading_periods=252, clean=True):

    log_return = (price_data["Close"] / price_data["Close"].shift(1)).apply(np.log)

    vol = log_return.rolling(window=window, center=False).std() * math.sqrt(
        trading_periods
    )

    h = window
    n = (log_return.count() - h) + 1

    adj_factor = 1.0 / (1.0 - (h / n) + ((h ** 2 - 1) / (3 * n ** 2)))

    result = vol * adj_factor

    if clean:
        return result.dropna()
    else:
        return

# Rogers-Satchell is an estimator for measuring the volatility of securities with an average return
#  not equal to zero. Unlike Parkinson and Garman-Klass estimators, Rogers-Satchell incorporates a
#  drift term (mean return not equal to zero).
def rogers_satchell(price_data, window=30, trading_periods=252, clean=True):

    log_ho = (price_data["High"] / price_data["Open"]).apply(np.log)
    log_lo = (price_data["Low"] / price_data["Open"]).apply(np.log)
    log_co = (price_data["Close"] / price_data["Open"]).apply(np.log)

    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)

    def f(v):
        return (trading_periods * v.mean()) ** 0.5

    result = rs.rolling(window=window, center=False).apply(func=f)

    if clean:
        return result.dropna()
    else:
        return result

# Yang-Zhang volatility is the combination of the overnight (close-to-open volatility), a weighted
#  average of the Rogers-Satchell volatility and the day’s open-to-close volatility.
def yang_zhang(price_data, window=30, trading_periods=252, clean=True):

    log_ho = (price_data["High"] / price_data["Open"]).apply(np.log)
    log_lo = (price_data["Low"] / price_data["Open"]).apply(np.log)
    log_co = (price_data["Close"] / price_data["Open"]).apply(np.log)

    log_oc = (price_data["Open"] / price_data["Close"].shift(1)).apply(np.log)
    log_oc_sq = log_oc ** 2

    log_cc = (price_data["Close"] / price_data["Close"].shift(1)).apply(np.log)
    log_cc_sq = log_cc ** 2

    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)

    close_vol = log_cc_sq.rolling(window=window, center=False).sum() * (
        1.0 / (window - 1.0)
    )
    open_vol = log_oc_sq.rolling(window=window, center=False).sum() * (
        1.0 / (window - 1.0)
    )
    window_rs = rs.rolling(window=window, center=False).sum() * (1.0 / (window - 1.0))

    k = 0.34 / (1.34 + (window + 1) / (window - 1))
    result = (open_vol + k * close_vol + (1 - k) * window_rs).apply(
        np.sqrt
    ) * math.sqrt(trading_periods)

    if clean:
        return result.dropna()
    else:
        return result

windows = [30, 60, 90, 120]
quantiles = [0.25, 0.75]

def volMethod(methodName):
    print(f'get  VolMethod by {methodName}')
    if  methodName == 'yang_zhang':
        fptr = yang_zhang
    elif methodName == 'rogers_satchell':
        fptr = rogers_satchell
    elif methodName == 'hodges_tompkins':
        fptr = hodges_tompkins
    elif methodName == 'garman_klass':
        fptr = garman_klass
    elif methodName == 'parkinson':
        fptr = parkinson
    else:
        fptr = standard_deviation
    return fptr

def Volality_Cone(symbol, data, Wins, method="yang_zhang"):
    min_ = []
    max_ = []
    median = []
    top_q = []
    bottom_q = []
    realized = []
    for window in Wins:
        # get a dataframe with realized volatility
        estimator = volMethod(method)(window=window, price_data=data)

        # append the summary stats to a list
        min_.append(estimator.min())
        max_.append(estimator.max())
        median.append(estimator.median())
        top_q.append(estimator.quantile(quantiles[1]))
        bottom_q.append(estimator.quantile(quantiles[0]))
        realized.append(estimator[-1])
    vol_ret = dict()
    vol_ret["symbol"] = symbol
    vol_ret["min"] = min_
    vol_ret["max"] = max_
    vol_ret["median"] = median
    vol_ret["top_q"] = top_q
    vol_ret["bottom_q"] = bottom_q
    vol_ret["realized"] = realized
    return vol_ret

def realized_vol(price_data, window=30):

    log_return = (price_data["Close"] / price_data["Close"].shift(1)).apply(np.log)

    return log_return.rolling(window=window, center=False).std() * math.sqrt(252)





