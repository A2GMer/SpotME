
from flask import Flask, request, abort
import psycopg2
import os

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
def hello_world():
    return "hello world!"

## 1 ##
#Webhookからのリクエストをチェックします。
@app.route("/callback", methods=['POST'])
# # 返事取得関数（今は暫定で日付返す関数）
# def get_response_message():
    # with get_connection() as conn:
        # with conn.cursor(name="cs") as cur:
        #     try:
        #         sqlStr = "SELECT TO_CHAR(CURRENT_DATE, 'yyyy/mm/dd');"
        #         cur.execute(sqlStr)
        #         cur.fetchone()
        #         # return mes
        #     except:
        #         mes = "exception"
        #         # return mes



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
#LINEのメッセージの取得と返信内容の設定(オウム返し)
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
    
    # 返信メッセージ作成
    # sendMessage = '{0} {1}'.format(msg[0], msg2)

    # with get_connection() as conn:
    #     with conn.cursor(name="cs") as cur:
    #         try:
    #             sqlStr = "SELECT TO_CHAR(CURRENT_DATE, 'yyyy/mm/dd');"
    #             cur.execute(sqlStr)
    #             (mes,) = cur.fetchone()
    #         except:
    #             mes = "exception"

    # sendMessage = '{0}さんが {1}円 立て替えました。{2}'.format(msg[1], msg[2])
    sendMessage = get_response_message()

    line_bot_api.reply_message(
        event.reply_token,
        #ここでメッセージを返します。
        TextSendMessage(text=sendMessage))


if __name__ == "__main__":
#    app.run()
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

# DB接続
def get_connection():
    dsn = 'host={0} port=5432 dbname={1} user={2} password={3}'.format(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
    return psycopg2.connect(dsn)

# お試し（日付取得 SQL）
def get_response_message():
    with get_connection() as conn:
        with get_connection() as conn:
            with conn.cursor(name="cs") as cur:
                try:
                    sqlStr = "SELECT TO_CHAR(CURRENT_DATE, 'yyyy/mm/dd');"
                    cur.execute(sqlStr)
                    (mes,) = cur.fetchone()
                except:
                    mes = "exception"