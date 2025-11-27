# test_smtp.py
import smtplib
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("SEI_REL_SMTP_HOST")
port = int(os.getenv("SEI_REL_SMTP_PORT", "587"))
user = os.getenv("SEI_REL_SMTP_USER")
password = os.getenv("SEI_REL_SMTP_PASS")
use_tls = os.getenv("SEI_REL_SMTP_USE_TLS", "true").lower() == "true"

print(f"Testando conexão SMTP: {host}:{port}")

try:
    print(f"Conectando ao servidor {host} na porta {port}...")
    with smtplib.SMTP(host, port, timeout=15) as server:
        print("✅ Conexão TCP estabelecida!")
        
        if use_tls:
            print("Iniciando TLS...")
            server.starttls()
            print("✅ TLS iniciado com sucesso!")
        
        if user and password:
            print(f"Autenticando como {user}...")
            server.login(user, password)
            print("✅ Autenticação SMTP bem-sucedida!")
        else:
            print("⚠️  Sem credenciais - pulando autenticação")
        
        print("\n✅ Conexão SMTP completa e funcional!")
        print("   Você pode enviar e-mails!")
        
except smtplib.SMTPAuthenticationError as e:
    print(f"❌ Falha de autenticação SMTP: {e}")
    print("\n💡 Possíveis soluções:")
    print("   - Para Gmail: Use 'Senha de App', não a senha normal")
    print("   - Verifique se 2FA está ativado (necessário para senha de app)")
    print("   - Verifique SEI_REL_SMTP_USER e SEI_REL_SMTP_PASS")
except smtplib.SMTPException as e:
    print(f"❌ Erro SMTP: {e}")
except TimeoutError:
    print("❌ Timeout ao conectar")
    print("\n💡 Possíveis causas:")
    print("   - Firewall bloqueando conexão")
    print("   - Rede/VPN bloqueando porta 587")
    print("   - Servidor SMTP indisponível")
    print("\n   Tente:")
    print("   - Verificar firewall/antivírus")
    print("   - Testar de outra rede")
    print("   - Verificar se porta 587 está aberta")
except Exception as e:
    print(f"❌ Erro ao conectar: {e}")
    print(f"   Tipo: {type(e).__name__}")

