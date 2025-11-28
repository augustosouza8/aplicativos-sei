#!/usr/bin/env python3
"""Script auxiliar para testar configurações do relatório diário antes da execução."""

import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


def verificar_config_sei() -> bool:
    """Verifica configurações obrigatórias do SEI."""
    print("=== Verificando Configurações do SEI ===")
    
    ok = True
    configs = {
        "SEI_USER": "Login do SEI",
        "SEI_PASS": "Senha do SEI",
        "SEI_ORGAO": "Código do órgão",
        "SEI_UNIDADE": "Nome da unidade SEI",
    }
    
    for var, desc in configs.items():
        valor = os.getenv(var)
        if not valor:
            print(f"❌ {var} ({desc}): NÃO CONFIGURADO")
            ok = False
        else:
            # Ocultar senha
            display = valor if var != "SEI_PASS" else "*" * len(valor)
            print(f"✅ {var} ({desc}): {display}")
    
    return ok


def verificar_config_relatorio() -> bool:
    """Verifica configurações do relatório diário."""
    print("\n=== Verificando Configurações do Relatório Diário ===")
    
    ok = True
    
    # Limites
    print("\n📊 Limites:")
    max_processos = os.getenv("SEI_REL_MAX_PROCESSOS_NOVOS_DIA", "10")
    max_pdf = os.getenv("SEI_REL_MAX_TAMANHO_PDF_MB", "100")
    print(f"  ✅ Máximo de processos novos/dia: {max_processos}")
    print(f"  ✅ Tamanho máximo PDF (MB): {max_pdf}")
    
    # Caminhos
    print("\n📁 Caminhos:")
    xlsx_path = os.getenv("SEI_REL_XLSX_PATH", "saida/relatorio_diario.xlsx")
    pdf_dir = os.getenv("SEI_REL_PDF_DIR", "pdfs/relatorio_diario")
    print(f"  ✅ Planilha XLSX: {xlsx_path}")
    print(f"  ✅ Diretório PDFs: {pdf_dir}")
    
    # Verificar se diretórios podem ser criados
    try:
        Path(xlsx_path).parent.mkdir(parents=True, exist_ok=True)
        Path(pdf_dir).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ Diretórios podem ser criados")
    except Exception as e:
        print(f"  ❌ Erro ao criar diretórios: {e}")
        ok = False
    
    # E-mail
    print("\n📧 Configurações de E-mail:")
    email_from = os.getenv("SEI_REL_EMAIL_FROM")
    email_to = os.getenv("SEI_REL_EMAIL_TO")
    smtp_host = os.getenv("SEI_REL_SMTP_HOST")
    smtp_port = os.getenv("SEI_REL_SMTP_PORT", "587")
    smtp_user = os.getenv("SEI_REL_SMTP_USER")
    smtp_pass = os.getenv("SEI_REL_SMTP_PASS")
    smtp_tls = os.getenv("SEI_REL_SMTP_USE_TLS", "true")
    
    configs_email = {
        "SEI_REL_EMAIL_FROM": email_from,
        "SEI_REL_EMAIL_TO": email_to,
        "SEI_REL_SMTP_HOST": smtp_host,
        "SEI_REL_SMTP_PORT": smtp_port,
        "SEI_REL_SMTP_USER": smtp_user,
        "SEI_REL_SMTP_PASS": smtp_pass,
    }
    
    obrigatorias_ok = True
    for var, valor in configs_email.items():
        if not valor:
            print(f"  ❌ {var}: NÃO CONFIGURADO (obrigatório para envio de e-mail)")
            obrigatorias_ok = False
            ok = False
        else:
            # Ocultar senha
            display = valor if var != "SEI_REL_SMTP_PASS" else "*" * len(valor)
            if var == "SEI_REL_EMAIL_TO":
                emails = [e.strip() for e in valor.split(",") if e.strip()]
                display = f"{len(emails)} destinatário(s): {', '.join(emails)}"
            print(f"  ✅ {var}: {display}")
    
    if not obrigatorias_ok:
        print("\n  ⚠️  Aviso: E-mail não será enviado sem todas as configurações obrigatórias")
    
    print(f"  ✅ TLS habilitado: {smtp_tls.lower() == 'true'}")
    
    return ok


def testar_conexao_smtp() -> bool:
    """Testa conexão SMTP sem enviar e-mail."""
    print("\n=== Testando Conexão SMTP ===")
    
    smtp_host = os.getenv("SEI_REL_SMTP_HOST")
    smtp_port_str = os.getenv("SEI_REL_SMTP_PORT", "587")
    smtp_user = os.getenv("SEI_REL_SMTP_USER")
    smtp_pass = os.getenv("SEI_REL_SMTP_PASS")
    smtp_tls = os.getenv("SEI_REL_SMTP_USE_TLS", "true").lower() == "true"
    
    if not smtp_host:
        print("❌ SEI_REL_SMTP_HOST não configurado. Pulando teste de conexão.")
        return False
    
    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        print(f"❌ Porta SMTP inválida: {smtp_port_str}")
        return False
    
    print(f"  Conectando em {smtp_host}:{smtp_port} (TLS: {smtp_tls})...")
    
    try:
        import smtplib
        
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if smtp_tls:
                print("  Iniciando TLS...")
                server.starttls()
            
            if smtp_user and smtp_pass:
                print(f"  Autenticando como {smtp_user}...")
                server.login(smtp_user, smtp_pass)
            
            print("✅ Conexão SMTP bem-sucedida!")
            return True
            
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Falha de autenticação SMTP: {e}")
        print("   Verifique SEI_REL_SMTP_USER e SEI_REL_SMTP_PASS")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ Erro SMTP: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return False


def verificar_historico() -> bool:
    """Verifica se histórico existe e está válido."""
    print("\n=== Verificando Histórico ===")
    
    historico_path = Path(os.getenv("SEI_REL_HISTORICO_ARQUIVO", "data/historico_processos.json"))
    
    if not historico_path.exists():
        print(f"  ℹ️  Histórico não existe: {historico_path}")
        print("  ℹ️  Isso é normal na primeira execução (baseline)")
        return True
    
    try:
        import json
        
        with open(historico_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            qtd = len(data)
            print(f"  ✅ Histórico válido: {qtd} processo(s) registrado(s)")
            
            # Verificar se tem metadata
            com_metadata = sum(1 for p in data.values() if "_metadata" in p)
            if com_metadata > 0:
                print(f"  ✅ {com_metadata} processo(s) com metadata")
            
            return True
        else:
            print(f"  ❌ Formato inválido do histórico")
            return False
            
    except Exception as e:
        print(f"  ❌ Erro ao ler histórico: {e}")
        return False


def main():
    """Executa todas as verificações."""
    print("=" * 60)
    print("TESTE DE CONFIGURAÇÃO - Relatório Diário SEI")
    print("=" * 60)
    
    ok_sei = verificar_config_sei()
    ok_rel = verificar_config_relatorio()
    ok_smtp = testar_conexao_smtp() if ok_rel else False
    ok_hist = verificar_historico()
    
    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)
    
    print(f"Configurações SEI:        {'✅ OK' if ok_sei else '❌ FALTANDO'}")
    print(f"Configurações Relatório:  {'✅ OK' if ok_rel else '❌ FALTANDO'}")
    print(f"Conexão SMTP:             {'✅ OK' if ok_smtp else '❌ FALHOU'}")
    print(f"Histórico:                {'✅ OK' if ok_hist else '⚠️  VERIFICAR'}")
    
    if ok_sei and ok_rel:
        print("\n✅ Configurações básicas OK! Você pode executar:")
        print("   uv run sei-client relatorio-diario")
        
        if not ok_smtp:
            print("\n⚠️  E-mail não será enviado. Verifique configurações SMTP.")
        
        return 0
    else:
        print("\n❌ Configurações incompletas. Verifique os erros acima.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

