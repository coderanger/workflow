from flask import Flask
from flaskext.xmlrpc import XMLRPCHandler, Fault

from workflow.interpreter import Evaluator

app = Flask(__name__)

handler = XMLRPCHandler('api')
handler.connect(app, '/')

e = Evaluator.from_string('add(1, 3)')

@handler.register
def defer_return(id, value):
    e.defer_return(id, value)

e()
app.run()
