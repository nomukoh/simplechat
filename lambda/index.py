# lambda/index.py
import json
import os
import re
import urllib.request
import urllib.error

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # Cognitoで認証されたユーザー情報を取得（必要なら）
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])

        print("Processing message:", message)

        # FastAPI に渡すペイロードを構築
        payload = {
            "message": message,
            "conversationHistory": conversation_history
        }
        data = json.dumps(payload).encode('utf-8')

        # FastAPI のエンドポイントURLを環境変数から取得
        FASTAPI_URL = os.environ.get("FASTAPI_URL")
        if not FASTAPI_URL:
            raise Exception("Missing FASTAPI_URL environment variable")

        print(f"Calling FastAPI at {FASTAPI_URL} with payload:", payload)

        # urllib で POST リクエストを送信
        req = urllib.request.Request(
            FASTAPI_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=10) as res:
            res_body = res.read().decode('utf-8')
            print("FastAPI response body:", res_body)
            api_response = json.loads(res_body)

        # FastAPI 側が返すキー名に合わせて取り出し
        if 'response' not in api_response:
            raise Exception("Invalid response from FastAPI: 'response' key not found")

        assistant_response = api_response['response']

        # 会話履歴に追加
        conversation_history.append({
            "role": "assistant",
            "content": assistant_response
        })

        # 成功レスポンスを返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": conversation_history
            })
        }

    except urllib.error.HTTPError as e:
        # HTTP エラー時のハンドリング
        error_body = e.read().decode('utf-8')
        print(f"HTTPError: {e.code} {e.reason}, body={error_body}")
        return {
            "statusCode": e.code,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "error": f"HTTPError {e.code}: {e.reason}",
                "details": error_body
            })
        }

    except Exception as error:
        print("Error:", str(error))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
