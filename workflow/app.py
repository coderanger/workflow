from flask import Flask
from flaskext.xmlrpc import XMLRPCHandler, Fault

from workflow.interpreter import Evaluator

app = Flask(__name__)

handler = XMLRPCHandler('api')
handler.connect(app, '/')

def cb(value):
    print 'COMPLETE: %s'%value
e = Evaluator('any(add(1, 3), add(4, 5))', cb)

@handler.register
def defer_return(id, value):
    e.defer_return(id, value)

e()
app.run()
