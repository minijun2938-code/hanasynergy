import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY") 

if api_key:
    # transport='rest' 옵션을 추가하여 gRPC DNS 문제를 우회합니다.
    genai.configure(api_key=api_key, transport='rest')
    
    print("--- REST 방식으로 모델 리스트 조회 시도 ---")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"Model Name: {m.name}")
    except Exception as e:
        print(f"에러 발생: {e}")