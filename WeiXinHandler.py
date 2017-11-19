import base64
import json
import os
import random
import threading
import time

import itchat
import requests


class WeiXinInstanceList:
    def __init__(self):
        self.instances = {}
        # self.run = True

    def getInfos(self):
        ret = []
        for i in self.instances:
            ret.append({'uid': i, 'status': self.instances[i].getStatus()})
        return json.dumps(ret)

    def getStatus(self, uid):
        if uid in self.instances:
            return self.instances[uid].getStatus()
        return False

    def keys(self):
        return self.instances.keys()

    def getLastCount(self, uid):
        if uid not in self.instances:
            return -1
        return self.instances[uid].getLastCount()

    def __contains__(self, item):
        return item in self.instances

    def __delitem__(self, key):
        if key in self.instances:
            self.instances[key].logout()
            del self.instances[key]

    def __getitem__(self, item):
        if item in self.instances:
            return self.instances[item]
        self.instances[item] = WeiXinHandler(item)
        return self.instances[item]


class WeiXinHandler:
    instanceList = []
    cache = {}

    def __init__(self, uid):

        self.instance = None
        self.msg = None
        self.uid = uid
        self.status = None
        self.curCount = 0
        self.sendFriends = None
        self.condition = None

        self.qunfa_thread = None

        self.lastCount = -1

        # self.cache = {}

        # self.instanceList = []

    def _removeId(self):
        print('remove {}'.format(self.uid))
        if self.qunfa_thread and self.qunfa_thread.is_alive():
            WeiXinHandler.cache[self.uid] = {'lastCount': self.curCount, 'msg': self.msg, 'condition': self.condition}
            self.msg = None
            self.condition = None
            self.lastCount = -1
            self.curCount = 0
            self.sendFriends = None

        if self.qunfa_thread:
            self.qunfa_thread = None

        self.status = False

        if os.path.exists(self.uid):
            os.remove(self.uid)

        if self.instance:
            self.instance.logout()

        # if self.instance not in self.instanceList and self.instance:
        #     self.instanceList.append(self.instance)

        if self.instance and self.instance not in WeiXinHandler.instanceList:
            WeiXinHandler.instanceList.append(self.instance)

        self.instance = None

        self.canDel = True

    def _open_QR(self):

        def qrCallback(**kwargs):
            # print('qr callback')
            with open(self.uid, 'wb') as fout:
                fout.write(kwargs['qrcode'])

        instance = self.instance
        uuid = None
        for get_count in range(10):
            print('Getting uuid')
            uuid = instance.get_QRuuid()

            tryTimes = 10
            while not uuid and tryTimes > 0:
                uuid = instance.get_QRuuid()
                time.sleep(1)
                tryTimes -= 1

            print('Getting QR Code')
            if instance.get_QR(uuid, qrCallback=qrCallback):
                break
            elif get_count >= 9:
                print('Failed to get QR Code, please restart the program')
                return None
        print('Please scan the QR Code')
        return uuid

    def _myquit(self):
        self._removeId()

    def _sub_fun(self, uuid):
        instance = self.instance
        uid = self.uid

        waitForConfirm = False
        for i in range(20):
            status = instance.check_login(uuid)
            if status == '200':
                break
            elif status == '201':
                if waitForConfirm:
                    print('Please press confirm')
                    waitForConfirm = True
            elif status == '408':
                self._removeId()
                # del instance
                waitForConfirm = False
                return None

        userInfo = instance.web_init()
        instance.show_mobile_login()

        if os.path.exists(uid):
            os.remove(uid)

        instance.get_friends(True)

        self.status = True

        if self.uid in WeiXinHandler.cache:
            self.msg = WeiXinHandler.cache[self.uid].get('msg')
            self.condition = WeiXinHandler.cache[self.uid].get('condition')
            self.lastCount = WeiXinHandler.cache[self.uid].get('lastCount', -1)
            self.searchFriends(self.condition)

        print('Login successfully as %s' % userInfo['User']['NickName'])
        instance.start_receiving(exitCallback=self._myquit)

        @instance.msg_register([itchat.content.NOTE])
        def recNote(msg):
            if '请先发送朋友验证请求，对方验证通过后，才能聊天' in msg['Content']:
                instance.set_alias(msg.user.userName, "AAA_删除" + msg.user.remarkName)

        instance.run()

    def login(self):

        if not self.instance:
            if WeiXinHandler.instanceList:
                instance = WeiXinHandler.instanceList.pop()
            else:
                instance = itchat.Core()
            self.instance = instance
        try:
            uuid = self._open_QR()
        except Exception as e:
            print(e)
            # del instance
            self._removeId()
            return None

        if not uuid:
            return None
        threading.Thread(target=self._sub_fun, args=(uuid,)).start()

    def getWeiXinInfo(self):
        infos = {
            "Uin": "null",
            "HeadImage": "null",
            "NickName": "null",
        }
        if not self.status:
            return infos
        myself = self.instance.get_friends()[0]
        infos['Uin'] = myself.uin
        infos['HeadImage'] = base64.b64encode(self.getHeadImg(myself.userName)).decode('utf-8')
        infos['NickName'] = myself.nickName
        return infos

    def searchFriends(self, condition: dict):

        if not condition:
            return None

        instance = self.instance
        friends = instance.get_friends()[1:]
        retFriends = []
        if condition.get('ChatRoom', False):
            chatRooms = instance.get_chatrooms()
            retFriends.extend(chatRooms)

        if 'Count' not in condition:
            condition['Count'] = 500
        count = condition['Count']

        for friend in friends:
            flag = True
            for p in condition:
                if p == 'Count':
                    pass
                elif p == 'UserName':
                    if friend.get(p, None) not in condition[p]:
                        flag = False
                        break
                elif friend.get(p, None) != condition[p]:
                    flag = False
                    break
            if flag:
                count -= 1
                if count <= 0:
                    break
                retFriends.append(friend)

        sendFriends = retFriends

        sendFriends.sort(key=lambda x: x.nickName)

        sendFriendsCount = len(sendFriends)

        self.sendFriends = sendFriends

        return sendFriendsCount

    def getLastCount(self):
        return self.lastCount

    def getContacts(self):
        rets = []

        instance = self.instance

        friends = instance.get_friends()[1:]

        rets.extend(friends)

        rooms = instance.get_chatrooms()

        rets.extend(rooms)
        ret = []
        for x in rets:
            ret.append({"UserName": x.get("UserName"), "RemarkName": x.get('RemarkName'), "NickName": x.get("NickName"),
                        "Sex": x.get("Sex"),
                        "Province": x.get("Province"),
                        "City": x.get("City"), "ChatRoom": True if x.get("MemberCount") > 0 else False})
        return json.dumps(ret)

    def getHeadImg(self, username):
        return self.instance.get_head_img(username)

    def setMessage(self, msg):
        self.msg = msg
        return True

    def setCondition(self, condition):
        self.condition = condition
        return self.searchFriends(condition)

    def getStatus(self):
        return self.status

    def sendMsg(self, friend, msg: dict):
        keys = list(msg.keys())
        keys.sort()
        for k in keys:
            delay = msg[k].get("delay", [3, 3])
            time.sleep(random.randint(delay[0], delay[1]))
            picture = msg[k].get("_picture", None)
            if picture:
                self.instance.send_image(picture, friend.userName)
            text = msg[k].get("text", None)
            if text:
                self.instance.send(text, friend.userName)
        return True

    def _qunfa(self):
        if not self.status or not self.msg or not self.sendFriends:
            return False

        print('qunfa thread {} start'.format(self.uid))

        self.curCount = 0

        msg = self.msg
        uid = self.uid

        for k in msg:
            pic = msg[k].get('picture', None)
            if not pic:
                continue
            path = uid + k
            try:
                res = requests.get(msg[k]['picture'])
                with open(path, 'wb') as fout:
                    fout.write(res.content)
                msg[k]['_picture'] = path
            except Exception as e:
                print(e)
                del msg[k]['_picture']
                # r = instances[uid]['instance'].upload_file(pic, isPicture=True)
                # msg[k]['picture'] = r['MediaId']

        flag = False

        for friend in self.sendFriends:

            if self.curCount < self.lastCount:
                self.curCount += 1
                continue

            if not self.status:
                self.lastCount = self.curCount
                flag = True
                break

            try:
                self.sendMsg(friend, msg)
            except Exception as e:
                print(e)
                self.lastCount = self.curCount
                flag = True
                break
            self.curCount += 1

        for k in msg:
            path = msg[k].get('picture')
            if path and os.path.exists(path):
                os.remove(path)

        print('qunfa thread finished', self.uid)

        if not flag:
            self.msg = None
            self.sendFriends = None
            self.condition = None
            self.curCount = 0
            self.lastCount = -1

            # del self.cache[self.uid]

    def logout(self):
        self._removeId()

    def qunfa(self):
        if self.qunfa_thread and self.qunfa_thread.is_alive():
            return self.curCount

        if not self.msg or not self.sendFriends:
            return False

        if self.qunfa_thread is not None:
            del self.qunfa_thread

        th = threading.Thread(target=self._qunfa)
        self.qunfa_thread = th
        th.start()
        return True

    def __del__(self):
        if self.status:
            self.instance.logout()
        self._removeId()


if __name__ == '__main__':
    a = WeiXinHandler('1.png')
    a.login()
    while not a.getStatus():
        time.sleep(1)
    message = {'1': {'text': 'hello', 'delay': [2, 4], 'picture': 'http://static.runoob.com/images/icon/w3c.png'}}
    condition = {'Sex': 2, 'Count': 10}
    a.setCondition(condition)
    a.setMessage(message)

    a.qunfa()

    time.sleep(10)
    input()
    a.logout()
