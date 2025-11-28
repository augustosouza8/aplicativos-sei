"""
Teste completo do módulo de envio de e-mails SMTP.

Este script testa:
1. Conexão SMTP básica (conexão, TLS, autenticação)
2. Envio real de e-mail usando a função enviar_email_relatorio do módulo

Execute com: 
  uv run python tests/test_smtp.py          # Testa conexão e pergunta sobre envio
  uv run python tests/test_smtp.py --conexao  # Testa apenas conexão
  uv run python tests/test_smtp.py --envio    # Testa conexão + envio completo
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Adicionar src ao path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sei_client.email_utils import enviar_email_relatorio
from src.sei_client.relatorio_diario import load_daily_report_settings

load_dotenv()


def validar_configuracoes() -> tuple[bool, dict]:
    """
    Valida se as configurações SMTP estão presentes no .env.
    
    Returns:
        Tupla (valido, config) onde valido é True se todas as configs necessárias existem,
        e config é um dicionário com as configurações encontradas.
    """
    config = {
        "email_from": os.getenv("SEI_REL_EMAIL_FROM"),
        "email_to": os.getenv("SEI_REL_EMAIL_TO"),
        "smtp_host": os.getenv("SEI_REL_SMTP_HOST"),
        "smtp_port": os.getenv("SEI_REL_SMTP_PORT", "587"),
        "smtp_user": os.getenv("SEI_REL_SMTP_USER"),
        "smtp_pass": os.getenv("SEI_REL_SMTP_PASS"),
        "smtp_use_tls": os.getenv("SEI_REL_SMTP_USE_TLS", "true"),
    }
    
    faltando = []
    if not config["smtp_host"]:
        faltando.append("SEI_REL_SMTP_HOST")
    if not config["smtp_user"]:
        faltando.append("SEI_REL_SMTP_USER")
    if not config["smtp_pass"]:
        faltando.append("SEI_REL_SMTP_PASS")
    
    valido = len(faltando) == 0
    
    return valido, config


def testar_conexao_smtp() -> bool:
    """Testa conexão SMTP básica (sem enviar e-mail)."""
    print("\n" + "=" * 60)
    print("TESTE 1: Conexão SMTP Básica")
    print("=" * 60)
    
    import smtplib
    
    host = os.getenv("SEI_REL_SMTP_HOST")
    port_str = os.getenv("SEI_REL_SMTP_PORT", "587")
    user = os.getenv("SEI_REL_SMTP_USER")
    password = os.getenv("SEI_REL_SMTP_PASS")
    use_tls = os.getenv("SEI_REL_SMTP_USE_TLS", "true").lower() == "true"
    
    if not host:
        print("❌ SEI_REL_SMTP_HOST não configurado no .env")
        return False
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"❌ Porta SMTP inválida: {port_str}")
        return False
    
    print(f"\n📡 Conectando ao servidor {host}:{port}...")
    
    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            print("✅ Conexão TCP estabelecida!")
            
            if use_tls:
                print("🔒 Iniciando TLS...")
                server.starttls()
                print("✅ TLS iniciado com sucesso!")
            
            if user and password:
                print(f"🔐 Autenticando como {user}...")
                server.login(user, password)
                print("✅ Autenticação SMTP bem-sucedida!")
            else:
                print("⚠️  Sem credenciais - pulando autenticação")
            
            print("\n✅ Conexão SMTP completa e funcional!")
            return True
            
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ Falha de autenticação SMTP: {e}")
        print("\n💡 Possíveis soluções:")
        print("   - Para Gmail: Use 'Senha de App', não a senha normal")
        print("   - Verifique se 2FA está ativado (necessário para senha de app)")
        print("   - Verifique SEI_REL_SMTP_USER e SEI_REL_SMTP_PASS no .env")
        return False
    except smtplib.SMTPException as e:
        print(f"\n❌ Erro SMTP: {e}")
        return False
    except TimeoutError:
        print("\n❌ Timeout ao conectar")
        print("\n💡 Possíveis causas:")
        print("   - Firewall bloqueando conexão")
        print("   - Rede/VPN bloqueando porta")
        print("   - Servidor SMTP indisponível")
        return False
    except Exception as e:
        print(f"\n❌ Erro ao conectar: {e}")
        print(f"   Tipo: {type(e).__name__}")
        return False


def testar_envio_email() -> bool:
    """Testa envio real de e-mail usando a função do módulo."""
    print("\n" + "=" * 60)
    print("TESTE 2: Envio Real de E-mail")
    print("=" * 60)
    
    # Carregar configurações do .env
    try:
        settings = load_daily_report_settings()
        print("\n✅ Configurações carregadas do .env")
    except Exception as e:
        print(f"\n❌ Erro ao carregar configurações: {e}")
        return False
    
    # Validar configurações obrigatórias
    if not settings.email_from:
        print("\n❌ SEI_REL_EMAIL_FROM não configurado no .env")
        return False
    
    if not settings.email_to:
        print("\n❌ SEI_REL_EMAIL_TO não configurado no .env")
        return False
    
    if not settings.smtp_host:
        print("\n❌ SEI_REL_SMTP_HOST não configurado no .env")
        return False
    
    print(f"\n📧 Configurações de e-mail:")
    print(f"   Remetente: {settings.email_from}")
    print(f"   Destinatários: {', '.join(settings.email_to)}")
    print(f"   SMTP: {settings.smtp_host}:{settings.smtp_port}")
    print(f"   TLS: {settings.smtp_use_tls}")
    print(f"   Usuário SMTP: {settings.smtp_user or '(não configurado)'}")
    
    # Criar conteúdo de teste
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    assunto = f"[TESTE] Envio SMTP - {timestamp}"
    
    corpo_texto = f"""
Este é um e-mail de teste do módulo de envio SMTP do SEI.

Data/Hora: {timestamp}

Se você recebeu este e-mail, significa que:
✅ A conexão SMTP está funcionando
✅ A autenticação está correta
✅ O envio de e-mails está operacional

Este é apenas um teste. Você pode ignorar este e-mail.
"""
    
    corpo_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 15px; border-radius: 5px; }}
        .content {{ padding: 20px; background-color: #f9f9f9; border-radius: 5px; margin-top: 10px; }}
        .success {{ color: #4CAF50; font-weight: bold; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>✅ Teste de Envio SMTP</h2>
        </div>
        <div class="content">
            <p>Este é um e-mail de <strong>teste</strong> do módulo de envio SMTP do SEI.</p>
            
            <p><strong>Data/Hora:</strong> {timestamp}</p>
            
            <p>Se você recebeu este e-mail, significa que:</p>
            <ul>
                <li class="success">✅ A conexão SMTP está funcionando</li>
                <li class="success">✅ A autenticação está correta</li>
                <li class="success">✅ O envio de e-mails está operacional</li>
            </ul>
            
            <p><em>Este é apenas um teste. Você pode ignorar este e-mail.</em></p>
        </div>
        <div class="footer">
            <p>Enviado automaticamente pelo sistema de testes do SEI Client</p>
        </div>
    </div>
</body>
</html>
"""
    
    print(f"\n📝 Preparando e-mail de teste...")
    print(f"   Assunto: {assunto}")
    
    # Tentar enviar
    try:
        print(f"\n🚀 Enviando e-mail...")
        enviar_email_relatorio(
            settings=settings,
            assunto=assunto,
            corpo_texto=corpo_texto,
            corpo_html=corpo_html,
            anexo_xlsx=None,  # Sem anexo no teste
        )
        
        print(f"\n✅ E-mail enviado com sucesso!")
        print(f"   Verifique a caixa de entrada de: {', '.join(settings.email_to)}")
        print(f"   (Verifique também a pasta de spam/lixo eletrônico)")
        return True
        
    except ValueError as e:
        print(f"\n❌ Erro de configuração: {e}")
        print("   Verifique as variáveis de ambiente no .env")
        return False
    except Exception as e:
        print(f"\n❌ Erro ao enviar e-mail: {e}")
        print(f"   Tipo: {type(e).__name__}")
        return False


def main():
    """Executa todos os testes."""
    parser = argparse.ArgumentParser(
        description="Teste do módulo de envio de e-mails SMTP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--conexao",
        action="store_true",
        help="Testa apenas a conexão SMTP (sem envio de e-mail)",
    )
    parser.add_argument(
        "--envio",
        action="store_true",
        help="Testa conexão + envio completo de e-mail",
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("TESTE DO MÓDULO DE ENVIO DE E-MAILS SMTP")
    print("=" * 60)
    
    # Verificar se .env existe
    env_file = Path(".env")
    if not env_file.exists():
        print("\n⚠️  Arquivo .env não encontrado na raiz do projeto")
        print("   Crie um arquivo .env com as configurações necessárias")
        return
    
    # Validar configurações
    print("\n📋 Validando configurações do .env...")
    valido, config = validar_configuracoes()
    
    if not valido:
        print("\n❌ Configurações faltando no .env:")
        if not config["smtp_host"]:
            print("   - SEI_REL_SMTP_HOST")
        if not config["smtp_user"]:
            print("   - SEI_REL_SMTP_USER")
        if not config["smtp_pass"]:
            print("   - SEI_REL_SMTP_PASS")
        return
    
    print("✅ Configurações básicas encontradas:")
    print(f"   SMTP Host: {config['smtp_host']}")
    print(f"   SMTP Port: {config['smtp_port']}")
    print(f"   SMTP User: {config['smtp_user']}")
    print(f"   TLS: {config['smtp_use_tls']}")
    if config["email_from"]:
        print(f"   From: {config['email_from']}")
    if config["email_to"]:
        print(f"   To: {config['email_to']}")
    
    # Teste 1: Conexão SMTP
    conexao_ok = testar_conexao_smtp()
    
    if not conexao_ok:
        print("\n" + "=" * 60)
        print("❌ TESTE DE CONEXÃO FALHOU")
        print("=" * 60)
        print("\n💡 Corrija os problemas antes de tentar novamente.")
        return
    
    # Se apenas conexão foi solicitado, parar aqui
    if args.conexao:
        print("\n" + "=" * 60)
        print("✅ TESTE DE CONEXÃO CONCLUÍDO COM SUCESSO")
        print("=" * 60)
        print("\nA conexão SMTP está funcionando corretamente!")
        print("Para testar o envio completo, execute:")
        print("  uv run python tests/test_smtp.py --envio")
        return
    
    # Se envio foi solicitado, pular pergunta
    if args.envio:
        print("\n" + "-" * 60)
        print("Executando teste de envio completo...")
        envio_ok = testar_envio_email()
    else:
        # Perguntar se deve continuar com envio real
        print("\n" + "-" * 60)
        resposta = input("\n❓ Deseja testar o envio real de e-mail? (s/N): ").strip().lower()
        
        if resposta not in ['s', 'sim', 'y', 'yes']:
            print("\n⏭️  Pulando teste de envio real.")
            print("✅ Teste de conexão SMTP concluído com sucesso!")
            return
        
        # Teste 2: Envio real
        envio_ok = testar_envio_email()
    
    # Resumo final
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    print(f"✅ Conexão SMTP: {'PASSOU' if conexao_ok else 'FALHOU'}")
    print(f"{'✅' if envio_ok else '❌'} Envio de E-mail: {'PASSOU' if envio_ok else 'FALHOU' if conexao_ok else 'NÃO TESTADO'}")
    
    if conexao_ok and envio_ok:
        print("\n🎉 Todos os testes passaram! O módulo de e-mail está funcionando corretamente.")
    elif conexao_ok:
        print("\n⚠️  Conexão OK, mas envio falhou. Verifique os logs acima.")
    else:
        print("\n❌ Testes falharam. Corrija os problemas antes de usar o módulo.")


if __name__ == "__main__":
    main()

