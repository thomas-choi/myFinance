import socket

DDSmap = {'33': 'timestamp', '4':'4', '146':'146', '37':'high', '133':'open','32':'low', '3':'last',
          '0':'ticker','73':'spread_code','22':'22','23':'currency', '21':'name','505':'ch-name',
          '20':'20', '75':'75', '24':'24', '5':'5', '31':'pclose', '30':'30', '127':'close',
          '137':'137','17':'volume', '38':'38', '1':'bid', '16':'16', '2':'ask', '19':'19', 
          '25':'message', '39':'err_code'}

class TCPClient:
    def __init__(self, ip_address, port):
        self.ip_address = ip_address
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f'Connect: {ip_address},{port}')
        self.socket.connect((self.ip_address, self.port))
        # self.socket.settimeout(1)

    def convertRecord(self, message):
        lt = message.split('|')
        # print(lt)
        record = dict()
        record['header'] = lt[0]
        record['subject'] = lt[1]
        for i in range(2, len(lt)-1, 2):
            # print(lt[i], ',', lt[i+1])
            record[DDSmap[lt[i]]] = lt[i+1]
        return record

    def send_command_b(self, command):
        # print('send_command:', command.encode())
        self.socket.sendall(command.encode())
        # print('recv...')
        data = self.socket.recv(1024)
        print('recv: ', data)
        return data.decode(errors='ignore')
    
    def send_command(self, command):
        print('send_command:', command.encode())
        self.socket.sendall(command.encode())
        data = b''
        print('recv...')
        while True:
            try:
                chunk = self.socket.recv(1024)
                if not chunk:
                    break
                data += chunk
            except socket.timeout:
                break
        print('recv: ', data)
        return data.decode()
    
    def snapshot(self, ticker):
        cmd = f'open|{ticker}|{ticker}|mode|image|\n'
        reply = self.send_command_b(cmd)
        return self.convertRecord(reply)

defaultIP = "47.106.136.162" 
defaultPort = 9945

DDSServer = TCPClient(defaultIP, defaultPort)

if __name__ == '__main__':

    # StockList = ['AMD','BAC','C','CSCO','DIS','DKNG','KO','MSFT','MU','NVDA','OXY','PYPL','TFC','TSLA','UBER','USB','VZ','WFC','XOM']
    StockList = ['IBM']
    for sy in StockList:   
        reply = DDSServer.snapshot(sy)
        print(reply)