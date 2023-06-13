# from kafka.admin import KafkaAdminClient
from kafka import KafkaConsumer
import time

# admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
# topic_names = admin_client.list_topics()

class KafkaClient:
    def __init__(self, bootstrap_svr):
        self._bootstrap = bootstrap_svr

    # 
    def consume(self, topic_list):
        consumer = KafkaConsumer(topic_list, bootstrap_servers=self._bootstrap,
                         auto_offset_reset='latest', max_poll_records=1)
        msg_list = []
        for message in consumer:
            print(f"Received message: {message}")
            msg_list.append(message)
        return msg_list

if __name__ == '__main__':

    bootstrap_servers = ['192.168.11.106:9094']
    StockList = ['IBM']
    StockList = ['AMD','BAC','C','CSCO','DIS','DKNG','KO','MSFT','MU','NVDA','OXY','PYPL','TFC','TSLA','UBER','USB','VZ','WFC','XOM']
    kafka = KafkaClient(bootstrap_servers)

    while True:
        for sy in StockList:   
            reply = kafka.consume([sy])
            print(reply)
        time.sleep(60)