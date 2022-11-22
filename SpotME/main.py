from flask import Flask, request, abort
import psycopg2
import itertools
import textwrap
import math
import os
# 名前が英語でもできるように
# userテーブルでメンバー登録機能

class Execute_Mode:
    INSERT = "記録"
    HISTORY = "履歴"
    HELP = "ヘルプ"
    WHOPAY = "誰が払えばいい"
    CLEAR = "記録クリア"
    CALCULATE = "精算"

Execute_List = [Execute_Mode]

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

app = Flask(__name__)

#環境変数取得
YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]
DB_HOST = os.environ["DB_HOST"]
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]

EXECUTE_ARGCNT = 4
EXECUTE_PHRASE = "記録"

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

@app.route("/")
# def hello_world():
    # return "hello world!"

## 1 ##
#Webhookからのリクエストをチェックします。
@app.route("/callback", methods=['POST'])
def callback():
    # リクエストヘッダーから署名検証のための値を取得します。
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # リクエストボディを取得します。
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 署名を検証し、問題なければhandleに定義されている関数を呼び出す。
    # handle webhook body
    try:
        handler.handle(body, signature)

        # 署名検証で失敗した場合、例外を出す。
    except InvalidSignatureError:
        abort(400)

    # handleの処理を終えればOK
    return 'OK'

## 2 ##
###############################################
#Get messages and set reply messages
###############################################
#When a MessageEvent (recieved text messages) occurs on LINE,
#The first argument of reply_message, event.reply_token, is the token used to respond to the event.
#The second argument is passed a TextSendMessage object for the reply defined in linebot.models.
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    recievedMessage = event.message.text
    sendMessage = ''
    # 複数行対応のため、改行コードでSplit
    # For multi-line, split by newline code
    for l in recievedMessage.split('\n'):
        if is_execute(l) == False: return
        # split by space
        # 空白でSplit
        m = recievedMessage.split()
        # make reply messages
        sendMessage += execute(m)
        if sendMessage == '':
            return
        
    line_bot_api.reply_message(
            event.reply_token,
            #ここでメッセージを返します。
            TextSendMessage(text=sendMessage))


if __name__ == "__main__":
    # set the port
    # ポート番号の設定
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)

# 受け取ったメッセージから起動するかどうかを決定する
def is_execute(recievedMessage):
    
    # 起動フレーズが含まれているか？
    messageList = recievedMessage.split()
    if messageList[0] in Execute_List == False:
        return False
    return True


def execute(msg):
    if msg[0] == Execute_Mode.INSERT:
        # INSERT
        with get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    sqlStr = "INSERT INTO ledger(user_name, amount_money, content) VALUES('{0}', {1}, '{2}');".format(msg[1], msg[2], msg[3])
                    cur.execute(sqlStr)
                    conn.commit()
                    return '{0}さんが {1}円 立て替え。\n'.format(msg[1], msg[2])
                except:
                    return '記録に失敗しました。'
    # elif msg[0] == "メンバー登録":
    # userテーブル作成の必要あり
    elif msg[0] == Execute_Mode.HISTORY:
        with get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    sqlStr = "SELECT * FROM ledger;"
                    cur.execute(sqlStr)
                    result = cur.fetchall()
                except:
                    return '精算情報取得に失敗しました。'
        if len(result) < 1:
            return "履歴はありません。"
        
        m = ""
        for r in result:
            m += "{0}さんが、{1} を {2}円 で立て替え\n".format(r[0], r[2], r[1])
        return m

        
    elif msg[0] == Execute_Mode.CLEAR:
        with get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    sqlStr = sqlStr = "DELETE FROM ledger;"
                    cur.execute(sqlStr)
                    return '記録を削除しました。'
                except:
                    return '記録削除に失敗しました。'

    elif msg[0] == Execute_Mode.CALCULATE:
        # SHOW
        with get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    sqlStr = "SELECT * FROM ledger;"
                    cur.execute(sqlStr)
                    result = cur.fetchall()
                except:
                    return '精算情報取得に失敗しました。'
        
        if len(result) < 1:
            return '登録情報はありません。'
        # 支払総額を取得
        total = 0
        for r in result:
            total += r[1]
        # 一人当たりの支払を算出
        membernum = 0
        for n, r in itertools.groupby(sorted(result, key=lambda x: x[0]), lambda x: x[0]):
            membernum += 1
        perpay = math.ceil(total / membernum)
        
        m = "支払額：{0}円/1人\n\n".format(perpay)

        # 各人ごとにループ
        for n, r in itertools.groupby(sorted(result, key=lambda x: x[0]), lambda x: x[0]):
            # その人の支払合計額を算出
            pertotal = 0
            for l in list(r):
                pertotal += l[1]
            # その人の支払合計額 - 一人当たりの支払
            paid = math.ceil(pertotal - perpay)
            
            if paid == 0:
                # 0になればpaidequal
                m += "{0}さん === 精算不要\n".format(n)
            elif paid < 0:
                # マイナスになればpaidlow
                m += "{0}さん --> {1}円 支払い\n".format(n, abs(paid))
            elif paid > 0:
                # プラスになればpaidmuch
                m += "{0}さん <-- {1}円 もらう\n".format(n, abs(paid))
        
        m += "※小数点は切り上げてます。"
        return m
    elif msg[0] == Execute_Mode.WHOPAY:
        with get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    sqlStr = "SELECT * FROM ledger;"
                    cur.execute(sqlStr)
                    result = cur.fetchall()
                except:
                    return '精算情報取得に失敗しました。'
        if len(result) < 1:
            return '登録情報はありません。'

        total = 0
        
        for r in result:
            total += r[1]
        # 一人当たりの支払を算出
        membernum = 0
        for n, r in itertools.groupby(sorted(result, key=lambda x: x[0]), lambda x: x[0]):
            membernum += 1
        perpay = math.ceil(total / membernum)

        m = "誰が払ってもいいよ。"

        # 各人ごとにループ
        for n, r in itertools.groupby(sorted(result, key=lambda x: x[0]), lambda x: x[0]):
            # その人の支払合計額を算出
            pertotal = 0
            for l in list(r):
                pertotal += l[1]

            # その人の支払合計額 - 一人当たりの支払
            paid = math.ceil(pertotal - perpay)
            
            if paid < 0:
                m = ""
                # マイナスになればpaidlow
                m += "{0}さん が払うといい感じです。".format(n)
        
        return m
        
    elif msg[0] == Execute_Mode.HELP:

        f = open('help_message.txt', 'r', encoding='UTF-8')
        data = f.read()
        f.close()

        return data
    else:
        return ''




# DB接続
def get_connection():
    dsn = 'host={0} port=5432 dbname={1} user={2} password={3}'.format(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
    return psycopg2.connect(dsn)