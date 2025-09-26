#!/usr/bin/env python3
"""
Script de teste para a API PushinPay
"""

import requests
import json

def test_pushinpay_api():
    # Configure seu token aqui
    token = "SEU_TOKEN_AQUI"  # Substitua pelo token real
    
    # URL da API
    url = "https://api.pushinpay.com.br/api/pix/cashIn"
    
    # Headers
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Payload simples
    payload = {
        "value": 70,  # 0.70 reais = 70 centavos
        "webhook_url": "http://localhost:5000/webhook/pushinpay"
    }
    
    print("=== TESTE PUSHINPAY API ===")
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text}")
        
        if response.status_code == 200 or response.status_code == 201:
            print("✅ Sucesso!")
            try:
                data = response.json()
                print(f"JSON Response: {json.dumps(data, indent=2)}")
            except:
                print("❌ Resposta não é JSON válido")
        else:
            print(f"❌ Erro: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Erro JSON: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Erro text: {response.text}")
                
    except Exception as e:
        print(f"❌ Exceção: {e}")

if __name__ == "__main__":
    test_pushinpay_api()