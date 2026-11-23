import socket
s = socket.socket()
res = s.connect_ex(('127.0.0.1', 5432))
print('Port 5432 reachable:', res == 0)
s.close()
