#!/usr/bin/env python
import xmlrpclib

server_url = "http://127.0.0.1:5000/xmlrpc.py"
server = xmlrpclib.ServerProxy(server_url,verbose=True)
result = server.metaWeblog.newPost('user', 'pass', {'content':{'description':'http://127.0.0.1/'}})
print result
