from flask import Flask, request, abort
import psycopg2
import itertools
import textwrap
import math
import os
# ヘルプ機能
# 名前が英語でもできるように
# userテーブルでメンバー登録機能
# 誰が払うとバランス良い？

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
#LINEのメッセージの取得と返信内容の設定
###############################################
#LINEでMessageEvent（普通のメッセージを送信された場合）が起こった場合に、
#def以下の関数を実行します。
#reply_messageの第一引数のevent.reply_tokenは、イベントの応答に用いるトークンです。
#第二引数には、linebot.modelsに定義されている返信用のTextSendMessageオブジェクトを渡しています。
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    recievedMessage = event.message.text
    # 起動キーワードを検知
    rtn, msg = is_execute(recievedMessage)
    if rtn == False:
        return
    
    # msg2 = execute(msg)

    # with get_connection() as conn:
    #     with conn.cursor(name="cs") as cur:
    #         try:
    #             sqlStr = "SELECT TO_CHAR(CURRENT_DATE, 'yyyy/mm/dd');"
    #             cur.execute(sqlStr)
    #             (mes,) = cur.fetchone()
    #         except:
    #             mes = "exception"

    # 返信メッセージ作成
    sendMessage = execute(msg)
    if sendMessage == '':
        return

    line_bot_api.reply_message(
        event.reply_token,
        #ここでメッセージを返します。
        TextSendMessage(text=sendMessage))


if __name__ == "__main__":
    # ポート番号の設定
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)

# 受け取ったメッセージから起動するかどうかを決定する
def is_execute(recievedMessage):
    
    # 空白区切りの起動フレーズ数で構成されているか？
    messageList = recievedMessage.split()
    # if len(messageList) != EXECUTE_ARGCNT:
    #     return False
    
    # if messageList[0] != EXECUTE_PHRASE:
    #     return False

    return True, messageList


def execute(msg):
    if msg[0] == "記録":
        # INSERT
        with get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    sqlStr = "INSERT INTO ledger(user_name, amount_money, content) VALUES('{0}', {1}, '{2}');".format(msg[1], msg[2], msg[3])
                    cur.execute(sqlStr)
                    conn.commit()
                    return '{0}さんが {1}円 立て替えました。'.format(msg[1], msg[2])
                except:
                    return '記録に失敗しました。'
    # elif msg[0] == "メンバー登録":
    # userテーブル作成の必要あり

    elif msg[0] == "記録クリア":
        with get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    sqlStr = sqlStr = "DELETE FROM ledger;"
                    cur.execute(sqlStr)
                    return '記録を削除しました。'
                except:
                    return '記録削除に失敗しました。'

    elif msg[0] == "精算":
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
        # TODO: 支払総額を取得
        total = 0
        for r in result:
            total += r[1]
        # TODO: 一人当たりの支払を算出
        membernum = 0
        for n, r in itertools.groupby(sorted(result, key=lambda x: x[0]), lambda x: x[0]):
            membernum += 1
        perpay = math.ceil(total / membernum)
        
        # msg = "1人あたりの支払額は、{0}円です。\n\n".format(perpay)
        m = "支払額：{0}円/1人\n\n".format(perpay)

        # TODO: 各人ごとにループ
        for n, r in itertools.groupby(sorted(result, key=lambda x: x[0]), lambda x: x[0]):
            # TODO: その人の支払合計額を算出
            pertotal = 0
            for l in list(r):
                pertotal += l[1]
            # TODO: その人の支払合計額 - 一人当たりの支払
            paid = math.ceil(pertotal - perpay)
            
            if paid == 0:
                # TODO: 0になればpaidequal
                m += "{0}さんは、精算の必要はありません。\n".format(n)
            elif paid < 0:
                # TODO: マイナスになればpaidlow
                m += "{0}さんは、{1}円 支払う必要があります。\n".format(n, abs(paid))
            elif paid > 0:
                # TODO: プラスになればpaidmuch
                m += "{0}さんは、{1}円 もらう必要があります。\n".format(n, abs(paid))
        
        m += "※小数点は切り上げてます。"
        return m
    elif msg[0] == "誰が払えばいい":
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
        # TODO: 一人当たりの支払を算出
        membernum = 0
        for n, r in itertools.groupby(sorted(result, key=lambda x: x[0]), lambda x: x[0]):
            membernum += 1
        perpay = math.ceil(total / membernum)

        m = "誰が払ってもいいよ。"

        # TODO: 各人ごとにループ
        for n, r in itertools.groupby(sorted(result, key=lambda x: x[0]), lambda x: x[0]):
            # TODO: その人の支払合計額を算出
            pertotal = 0
            for l in list(r):
                pertotal += l[1]

            # TODO: その人の支払合計額 - 一人当たりの支払
            paid = math.ceil(pertotal - perpay)
            
            if paid < 0:
                m = ""
                # TODO: マイナスになればpaidlow
                m += "{0}さん が払うといい感じです。".format(n)
        
        return m
        
    elif msg[0] == 'ヘルプ':
        # 外だしにしたい
        r = textwrap.dedent('''\
            どうも！SpotME!です。
            ■使い方
            【誰かが立て替えた時】
            記録 名前 金額(数字のみ)  立て替えたもの
            　例）記録 大翔 2000 マクド
            【精算したい時】
            精算
            【記録クリアしたい時】
            記録クリア
            
            ※多分バグが多いです。
            許してね。
            気が向いたら直します。
            
            【既知バグ】
            英語の名前がダメ⇨WINさんすみません。
            金額に数字以外を入れたらあかん
            【追加したい機能】
            誰が払うと丁度いいか教えてくれる機能
            メンバー登録機能
        ''')

        return r
    else:
        return ''




# DB接続
def get_connection():
    dsn = 'host={0} port=5432 dbname={1} user={2} password={3}'.format(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
    return psycopg2.connect(dsn)


# def insert_ledger(msg):
#     with get_connection() as conn:
#         with conn.cursor() as cur:
#             try:
#                 sqlStr = "INSERT INTO ledger (user_name, amount_money, content) VALUES ({0}, {1}, {2})".format(msg[1], msg[2], msg[3])
#                 cur.execute(sqlStr)
#                 # (mes,) = cur.fetchone()
#                 conn.commit()
#             except:
#                 mes = "exception"


# お試し（日付取得 SQL）
# def get_response_message():
#     with get_connection() as conn:
#         with get_connection() as conn:
#             with conn.cursor(name="cs") as cur:
#                 try:
#                     sqlStr = "SELECT TO_CHAR(CURRENT_DATE, 'yyyy/mm/dd');"
#                     cur.execute(sqlStr)
#                     (mes,) = cur.fetchone()
#                 except:
#                     mes = "exception"