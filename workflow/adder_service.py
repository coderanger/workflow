import threading
import time
import xmlrpclib

from flask import Flask
from flaskext.xmlrpc import XMLRPCHandler, Fault

def delay_add(cb, uuid, x, y):
    print 'Starting delay_add'
    time.sleep(2)
    server = xmlrpclib.ServerProxy(cb)
    server.defer_return(uuid, x+y)
    print 'Response sent'

app = Flask(__name__)

handler = XMLRPCHandler('api')
handler.connect(app, '/')

@handler.register
def add(cb, uuid, x, y):
    threading.Thread(target=delay_add, args=[cb, uuid, x, y]).start()
    return

app.run(port=5001)
