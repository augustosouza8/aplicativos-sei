# 🚀 Início Rápido - Relatório Diário

Guia rápido para começar a usar o relatório diário em 5 minutos.

## 1️⃣ Configurar Variáveis de Ambiente

Edite `.env` na raiz do projeto:

```env
# SEI (obrigatório)
SEI_USER=seu_login
SEI_PASS=sua_senha
SEI_ORGAO=28
SEI_UNIDADE=SEPLAG/AUTOMATIZAMG

# Relatório Diário (obrigatório para e-mail)
SEI_REL_EMAIL_FROM=seu_email@exemplo.com
SEI_REL_EMAIL_TO=destinatario@exemplo.com
SEI_REL_SMTP_HOST=smtp.gmail.com
SEI_REL_SMTP_PORT=587
SEI_REL_SMTP_USER=seu_email@exemplo.com
SEI_REL_SMTP_PASS=senha_app
SEI_REL_SMTP_USE_TLS=true
```

## 2️⃣ Testar Configurações

```bash
python scripts/testar_config_relatorio.py
```

## 3️⃣ Executar

### Primeira vez (baseline):
```bash
uv run sei-client relatorio-diario
```

### Execuções seguintes:
```bash
uv run sei-client relatorio-diario
```

## 📚 Documentação Completa

Para detalhes completos, consulte: **[guia_relatorio_diario.md](guia_relatorio_diario.md)**

