import json
import os
import threading
import time

from flask import Flask, request, Response

# from WeiXinHandler import WeiXinInstanceList
from WeiXinHandler import WeiXinInstanceList

instances = WeiXinInstanceList()

app = Flask('weixin')


def checkToken(token):
    return True


@app.route('/getlastcount', methods=['POST', 'GET'])
def getLastCount():
    uid = None
    if request.method == 'POST' and 'id' in request.form:
        uid = request.form['id']
    elif 'id' in request.args:
        uid = request.args['id']
    if not uid:
        return 'false'
    return str(instances[uid].getLastCount())


@app.route('/getinstancestatus', methods=['GET', 'POST'])
def getInstanceStatus():
    token = None
    if request.method == 'POST' and 'token' in request.form:
        token = request.form['token']
    elif 'token' in request.args:
        token = request.args['token']

    uid = None
    if request.method == 'POST' and 'id' in request.form:
        uid = request.form['id']
    elif 'id' in request.args:
        uid = request.args['id']

    if not uid or not checkToken(token):
        return 'false'
    return str(instances.getStatus(uid))


@app.route('/getinstances', methods=['GET', 'POST'])
def getInstances():
    token = None
    if request.method == 'POST' and 'token' in request.form:
        token = request.form['token']
    elif 'id' in request.args:
        token = request.args['token']

    if not checkToken(token):
        return 'false'
    return instances.getInfos()


@app.route('/getstatus', methods=['GET', 'POST'])
def getStatus():
    uid = None
    if request.method == 'POST' and 'id' in request.form:
        uid = request.form['id']
    elif 'id' in request.args:
        uid = request.args['id']

    if not uid:
        return 'false'

    if uid in instances:
        return 'true' if instances[uid].getStatus() else 'false'
    return 'false'


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    uid = None
    if request.method == 'POST' and 'id' in request.form:
        uid = request.form['id']
    elif 'id' in request.args:
        uid = request.args['id']
    if not uid:
        return 'false'
    if uid not in instances:
        return 'false'

    if not instances[uid].getStatus():
        return 'false'
    instances[uid].logout()
    # del instances[uid]
    return 'true'


@app.route('/setcondition', methods=['POST'])
def setCondition():
    uid = None
    if request.method == 'POST' and 'id' in request.form:
        uid = request.form['id']
    elif 'id' in request.args:
        uid = request.args['id']
    if not uid or uid not in instances or not instances[uid].getStatus():
        return 'false'
    if 'condition' in request.form:
        condition = json.loads(request.form['condition'])
    else:
        condition = None
        for i in request.form:
            condition = i
            break
        try:
            condition = json.loads(condition)
        except Exception as e:
            return e.__repr__()

        if 'condition' not in condition:
            return "false"
        condition = condition['condition']
    r = instances[uid].setCondition(condition)
    return str(r)


@app.route('/getcontact', methods=['GET', 'POST'])
def getContacts():
    uid = None
    if request.method == 'POST' and 'id' in request.form:
        uid = request.form['id']
    elif 'id' in request.args:
        uid = request.args['id']
    if uid not in instances or not instances[uid].getStatus():
        return 'false'
    return instances[uid].getContacts()


@app.route('/getweixininfo', methods=["GET", "POST"])
def getWeiXinInfos():
    uid = request.args.get('id')
    userName = request.args.get('username') or request.args.get('UserName')
    if not uid or not userName or uid not in instances or not instances[uid].getStatus():
        return 'false'
    infos = instances[uid].getWeiXinInfos()
    return Response(json.dumps(infos), mimetype='application/json')


@app.route('/getheadimg')
def getHeadImg():
    uid = request.args.get('id')
    userName = request.args.get('username') or request.args.get('UserName')

    if not uid or not userName or uid not in instances or not instances[uid].getStatus():
        return 'false'

    bytearray = instances[uid].getHeadImg(userName)
    res = Response(bytearray, mimetype='image/jpeg')
    return res


@app.route('/setmessage', methods=['POST'])
def setMessage():
    uid = None
    if request.method == 'POST' and 'id' in request.form:
        uid = request.form['id']
    elif 'id' in request.args:
        uid = request.args['id']

    if not uid or uid not in instances or not instances[uid].getStatus():
        return 'false'

    if 'message' in request.form:
        message = json.loads(request.form['message'])
    else:
        message = None
        for i in request.form:
            message = i
            break
        try:
            message = json.loads(message)
        except Exception as e:
            return e.__repr__()
        if 'message' not in message:
            return 'false'
        message = message['message']
        if type(message) is str:
            try:
                message = json.loads(message)
            except Exception as e:
                return e.__repr__()

    r = instances[uid].setMessage(message)

    return 'true' if r else 'false'


@app.route('/qunfa', methods=['GET', 'POST'])
def qunfa():
    uid = None
    if request.method == 'POST' and 'id' in request.form:
        uid = request.form['id']
    elif 'id' in request.args:
        uid = request.args['id']

    if not uid or uid not in instances or not instances[uid].getStatus():
        return 'false'
    r = instances[uid].qunfa()

    if type(r) is int:
        return str(r)
    else:
        return 'true' if r else 'false'


# @app.route('/start')
# def startMonitor():
#     instances.startMonitor()
#     return 'true'
#
#
# @app.route('/stop')
# def stopMonitor():
#     instances.stop()
#     return 'true'


@app.route('/login', methods=['GET', 'POST'])
def login():
    uid = None
    if request.method == 'POST' and 'id' in request.form:
        uid = request.form['id']
    elif 'id' in request.args:
        uid = request.args['id']

    if not uid:
        return 'false'

    if uid in instances and instances[uid].getStatus():
        return "已经登陆"

    if uid in instances and os.path.exists(uid):
        with open(uid, 'rb') as fin:
            pic = fin.read()
        res = Response(pic, mimetype='image/jpeg')
        return res

    instances[uid].login()

    tryTimes = 10
    while not os.path.exists(uid):
        tryTimes -= 1
        if tryTimes <= 0:
            return "登陆超时，请重试"
        time.sleep(1)

    with open(uid, 'rb') as fin:
        pic = fin.read()

    res = Response(pic, mimetype='image/jpeg')
    return res


def startThread():
    def fun():
        app.run(debug=True, host='10.105.63.245', port=5052, threaded=True)
        # app.run(debug=False, host='127.0.0.1', port=5000, threaded=True)

    th = threading.Thread(target=fun)
    th.start()
    th.join()


if __name__ == '__main__':
    app.run(debug=True, host='10.105.63.245', port=5052, threaded=True)
    # app.run(debug=False, host='127.0.0.1', port=5000, threaded=True)
    # startThread()
