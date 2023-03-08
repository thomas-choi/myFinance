import os
from os import environ
import pandas as pd
from sqlalchemy import create_engine
import logging
from datetime import datetime, timedelta
import pytz
import time
import sshtunnel

dbconn = None
__sTunnel = None

def setDBSSH():
    global __sTunnel
    global dbconn
    # Once has the SSH set, the following DB calls go thought SSH
    if __sTunnel is not None:
        __sTunnel.close()
    SSHHOST=environ.get("SSHHOST")
    SSHUSR=environ.get("SSHUSR")
    SSHPWD=environ.get("SSHPWD")
    DBHOST=environ.get("DBHOST")
    DBUSER=environ.get("DBUSER")
    DBPWD=environ.get("DBPWD")
    DB = environ.get("DBMKTDATA")
    DBPORT = int(environ.get("DBPORT"))
    __sTunnel = sshtunnel.SSHTunnelForwarder(
        (SSHHOST),ssh_username=SSHUSR, ssh_password=SSHPWD,
        remote_bind_address=(DBHOST, DBPORT)
        )
    logging.debug(f'sTunnel: {__sTunnel}')
    __sTunnel.start()
    dbpath = "mysql+pymysql://{user}:{pw}@{host}:{port}/{db}".format(host="127.0.0.1",
    db=DB, user=DBUSER, pw=DBPWD, port=__sTunnel.local_bind_port)
    logging.info(f'setup DBengine to {dbpath}')
    # Create SQLAlchemy engine to connect to MySQL Database
    dbconn = create_engine(dbpath)
    logging.debug(f'dbconn=>{dbconn}')

def nowbyTZ(tzName):
    tformats = '%Y-%m-%d %H:%M:%S'
    tzinfo = time.tzname
    tNow = datetime.now()
    logging.info(f'Local System TimeZone info: {tzinfo[0]} and local time: {tNow}')

    targetNow = datetime.strptime(tNow.astimezone(pytz.timezone(tzName)).strftime(tformats), tformats)
    logging.info(f'Target TimeZone {tzName}:   Target time: {targetNow}')
    return targetNow

def get_Symbollist(listname):
    basedir = environ.get("PROD_LIST_DIR")
    logging.debug(f'Load symbol list {listname} from {basedir}')
    listpath = os.path.join(basedir, f'{listname}.csv')
    s_list = pd.read_csv(listpath)['Symbol'].unique()
    return s_list

def get_DBengine():
    global dbconn
    if dbconn is None:
        hostname=environ.get("DBHOST")
        uname=environ.get("DBUSER")
        pwd=environ.get("DBPWD")
        DB = environ.get("DBMKTDATA")
        DBPORT = environ.get("DBPORT")

        dbpath = "mysql+pymysql://{user}:{pw}@{host}:{port}/{db}".format(host=hostname, db=DB, user=uname, pw=pwd,port=DBPORT)
        logging.info(f'setup DBengine to {dbpath}')
        # Create SQLAlchemy engine to connect to MySQL Database
        dbconn = create_engine(dbpath)
        logging.info(f'dbconn=>{dbconn}')
    return dbconn

def get_Max_date(dbntable, symbol=None):
    try:
        if symbol is None:
            query = f"SELECT max(Date) as maxdate from {dbntable} ;"
        else:
            query = f"SELECT max(Date) as maxdate from {dbntable} where symbol = \'{symbol}\';"
        logging.info(f'get_Max_date :{query}')
        df = pd.read_sql(query, get_DBengine())
        max_date = df.maxdate.iloc[0]
        logging.info(f"get_Max_date() => {max_date} ")
        return max_date
    except Exception as e:
        logging.error("Exception occurred at get_Max_date()", exc_info=True)

def get_Max_Options_date(dbntable, symbol=None):
    try:
        if symbol is None:
            query = f'SELECT max(Date) as maxdate, section FROM {dbntable} group by section order by maxdate desc, section desc;'
        else:
            query = f'SELECT max(Date) as maxdate, section FROM {dbntable} where UnderlyingSymbol = \'{symbol}\' group by section order by maxdate desc, section desc;'

        logging.info(f'get_Max_date :{query}')
        df = pd.read_sql(query, get_DBengine())
        logging.debug(df.head())
        max_date = df.maxdate.iloc[0]
        section = df.section.iloc[0]
        logging.info(f"get_Max_date() => {max_date},{section} ")
        return max_date, section
    except Exception as e:
        logging.error("Exception occurred at get_Max_Options_date()", exc_info=True)

def ExecSQL(query):
    logging.info(f"ExecSQL: {query}")
    try:
        results = get_DBengine().execute(query)
        logging.info(f'number of rows execed: {results.rowcount}')
    except Exception as e:
        logging.error("Exception occurred at load_df(np.linspace)", exc_info=True)

def load_df_SQL(query):
    """
    Return dataframe from SQL statement
    """
    logging.info(f'load_df_SQL({query}).')
    try:
        df = pd.read_sql(query, get_DBengine())
        return df
    except Exception as e:
        logging.error("Exception occurred at load_df_SQL(np.linspace)", exc_info=True)

def StoreEOD(eoddata, DBn, TBLn):
    try:
        logging.info(f'StoreEOD size: {len(eoddata)} in table:{TBLn} on DB:{DBn}')
        dbcon = get_DBengine()
        logging.info(f'StoreEOD dbcon: {dbcon}')
        # Convert dataframe to sql table
        eoddata.to_sql(name=TBLn, con=dbcon, if_exists='append', index=False)
    except Exception as e:
        logging.error("Exception occurred", exc_info=True)


def load_eod_price(ticker, start, end):
    DB = environ.get("DBMKTDATA")
    TBL = environ.get("TBLDLYPRICE")
    query = f"SELECT * from {DB}.{TBL} where symbol = \'{ticker}\' and Date >= \'{start}\' and Date <= \'{end}\' order by Date;"
    return load_df_SQL(query)
