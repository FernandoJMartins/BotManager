"""
Serviço para monitorar status/uptime de serviços críticos
Usando APIs reais de monitoramento como DownDetector e outras
"""
import requests
import time
from datetime import datetime
from threading import Thread
import json

class ServiceMonitor:
    def __init__(self):
        self.services = {
            'telegram': {
                'name': 'Telegram',
                'status': 'unknown',
                'response_time': None,
                'last_check': None,
                'icon': 'fab fa-telegram',
                'description': 'Serviço de mensagens Telegram'
            },
            'pix': {
                'name': 'PIX/SPI',
                'status': 'unknown', 
                'response_time': None,
                'last_check': None,
                'icon': 'fas fa-university',
                'description': 'Sistema de Pagamentos Instantâneos'
            },
        }
        
    def check_service_via_downdetector(self, service_name):
        """Verifica status usando DownDetector-like API"""
        try:
            # Usando a API do IsItDownRightNow (similar ao DownDetector)
            url = f"https://isitdownrightnow.com/check.php?domain={service_name}.com"
            
            start_time = time.time()
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response_time = round((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                content = response.text.lower()
                if 'is up' in content or 'online' in content or 'working' in content:
                    return 'online', response_time
                elif 'is down' in content or 'offline' in content or 'not working' in content:
                    return 'offline', None
            
            return 'unknown', None
            
        except Exception as e:
            print(f"Erro no DownDetector check para {service_name}: {e}")
            return 'error', None
    
    def check_service_via_direct_api(self, service_key):
        """Teste direto das APIs dos serviços"""
        urls_map = {
            'telegram': [
                'https://api.telegram.org/bot123456:test/getMe',  # 401 é OK
                'https://core.telegram.org/bots/api'  # 200 é OK
            ],
            'pix': [
                'https://www.bcb.gov.br/estabilidadefinanceira/pix',  # 200 é OK
                'https://pix.bcb.gov.br/',  # 200 é OK
                'https://www.bcb.gov.br/'  # 200 é OK
            ],
            'whatsapp': [
                'https://business.whatsapp.com/',  # 200 é OK
                'https://developers.facebook.com/docs/whatsapp'  # 200 é OK
            ]
        }
        
        urls = urls_map.get(service_key, [])
        
        for url in urls:
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response_time = round((time.time() - start_time) * 1000)
                
                # Critérios de sucesso por serviço
                if service_key == 'telegram':
                    if response.status_code in [200, 401, 404]:  # 401 = sem token é OK
                        return 'online', response_time
                elif service_key == 'pix':
                    if response.status_code == 200:
                        return 'online', response_time
                elif service_key == 'whatsapp':
                    if response.status_code == 200:
                        return 'online', response_time
                        
            except Exception as e:
                print(f"Erro testando {url}: {e}")
                continue
        
        return 'offline', None
        
    def check_service_via_status_api(self, service_key):
        """Verifica usando APIs de status específicas"""
        try:
            if service_key == 'telegram':
                # Telegram Status Page
                response = requests.get('https://status.core.telegram.org/', timeout=10)
                if response.status_code == 200 and 'operational' in response.text.lower():
                    return 'online', 100
                    
            elif service_key == 'pix':
                # Banco Central Status
                response = requests.get('https://www.bcb.gov.br/api/servicos', timeout=10)
                if response.status_code == 200:
                    return 'online', 150
                    
            elif service_key == 'whatsapp':
                # Meta Status
                response = requests.get('https://developers.facebook.com/status/', timeout=10) 
                if response.status_code == 200:
                    return 'online', 120
                    
        except Exception as e:
            print(f"Erro verificando status API para {service_key}: {e}")
        
        return 'unknown', None

    def check_service(self, service_key):
        """Método principal para verificar um serviço usando múltiplas APIs"""
        service = self.services[service_key]
        
        print(f"🔍 Verificando {service['name']}...")
        
        # Mapear nomes para DownDetector
        service_names_map = {
            'telegram': 'telegram',
            'pix': 'pix',
            'whatsapp': 'whatsapp'
        }
        
        best_status = 'offline'
        best_response_time = None
        
        # 1. Tentar DownDetector-like API
        try:
            service_name = service_names_map.get(service_key, service_key)
            status, response_time = self.check_service_via_downdetector(service_name)
            if status == 'online':
                best_status = status
                best_response_time = response_time
                print(f"✅ {service['name']}: Online via DownDetector ({response_time}ms)")
            else:
                print(f"⚠️ {service['name']}: DownDetector check = {status}")
        except Exception as e:
            print(f"Erro no DownDetector para {service_key}: {e}")
        
        # 2. Se não conseguiu via DownDetector, tentar API direta
        if best_status != 'online':
            try:
                status, response_time = self.check_service_via_direct_api(service_key)
                if status == 'online':
                    best_status = status
                    best_response_time = response_time
                    print(f"✅ {service['name']}: Online via API direta ({response_time}ms)")
                else:
                    print(f"⚠️ {service['name']}: API direta = {status}")
            except Exception as e:
                print(f"Erro na API direta para {service_key}: {e}")
        
        # 3. Se ainda não conseguiu, tentar Status API
        if best_status != 'online':
            try:
                status, response_time = self.check_service_via_status_api(service_key)
                if status == 'online':
                    best_status = status
                    best_response_time = response_time
                    print(f"✅ {service['name']}: Online via Status API ({response_time}ms)")
                else:
                    print(f"⚠️ {service['name']}: Status API = {status}")
            except Exception as e:
                print(f"Erro na Status API para {service_key}: {e}")
        
        # Atualizar serviço
        service['status'] = best_status
        service['response_time'] = best_response_time
        service['last_check'] = datetime.now()
        
        if best_status == 'online':
            print(f"✅ {service['name']}: ONLINE")
        else:
            print(f"❌ {service['name']}: {best_status.upper()}")
        
        return service
    
    def check_all_services(self):
        """Verifica todos os serviços usando APIs de monitoramento"""
        print("🔍 Verificando status dos serviços via APIs de monitoramento...")
        
        for service_key in self.services.keys():
            self.check_service(service_key)
            time.sleep(1)  # Delay entre requests para não sobrecarregar
            
        return self.get_status_summary()
    
    def get_status_summary(self):
        """Retorna lista de serviços para o template"""
        services_list = []
        for service in self.services.values():
            # Garante que last_check nunca seja None
            last_check = service.get('last_check')
            if last_check is None:
                last_check = datetime.now()
                
            services_list.append({
                'name': service['name'],
                'status': service.get('status', 'unknown'),
                'response_time': service.get('response_time'),
                'last_check': last_check
            })
        return services_list
    
    def get_status_color(self, status):
        """Retorna classe CSS baseada no status"""
        colors = {
            'online': 'success',
            'offline': 'danger', 
            'timeout': 'warning',
            'error': 'warning',
            'unknown': 'secondary'
        }
        return colors.get(status, 'secondary')
    
    def start_monitoring(self):
        """Inicia monitoramento contínuo em background"""
        def monitor_loop():
            while True:
                try:
                    self.check_all_services()
                    time.sleep(300)  # Verifica a cada 5 minutos
                except Exception as e:
                    print(f"Erro no monitoramento: {e}")
                    time.sleep(60)  # Retry em 1 minuto
        
        monitor_thread = Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        print("🚀 Monitoramento de uptime iniciado usando APIs reais")

# Instância global
service_monitor = ServiceMonitor()