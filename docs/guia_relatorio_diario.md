# Guia Passo a Passo: Relatório Diário por E-mail

Este guia explica como configurar e executar a funcionalidade de relatório diário automatizado do SEI.

## 📋 Pré-requisitos

1. **Python e dependências instalados**
   ```bash
   # Verificar se o projeto está configurado
   uv sync
   ```

2. **Credenciais do SEI configuradas**
   - Login do SEI
   - Senha do SEI
   - Código do órgão
   - Nome da unidade SEI

3. **Configurações de e-mail SMTP**
   - Servidor SMTP (host)
   - Porta SMTP (geralmente 587 para TLS ou 465 para SSL)
   - Usuário e senha para autenticação SMTP
   - E-mail remetente
   - Lista de destinatários

## 🔧 Passo 1: Configurar Variáveis de Ambiente

Crie ou edite o arquivo `.env` na raiz do projeto:

### 1.1 Configurações Obrigatórias do SEI (já existentes)

```env
# Credenciais do SEI
SEI_USER=seu_login_sei
SEI_PASS=sua_senha_sei
SEI_ORGAO=28
SEI_UNIDADE=SEPLAG/AUTOMATIZAMG
```

### 1.2 Configurações do Relatório Diário

```env
# Limites de processamento
SEI_REL_MAX_PROCESSOS_NOVOS_DIA=10
SEI_REL_MAX_TAMANHO_PDF_MB=100

# Caminhos de saída
SEI_REL_XLSX_PATH=saida/relatorio_diario.xlsx
SEI_REL_PDF_DIR=pdfs/relatorio_diario

# Configurações de e-mail (OBRIGATÓRIAS para envio)
SEI_REL_EMAIL_FROM=seu_email@exemplo.com
SEI_REL_EMAIL_TO=destinatario1@exemplo.com,destinatario2@exemplo.com
SEI_REL_SMTP_HOST=smtp.exemplo.com
SEI_REL_SMTP_PORT=587
SEI_REL_SMTP_USER=usuario_smtp
SEI_REL_SMTP_PASS=senha_smtp
SEI_REL_SMTP_USE_TLS=true
```

### 1.3 Exemplo Completo de `.env`

```env
# === SEI - Obrigatórias ===
SEI_USER=joao.silva
SEI_PASS=MinhaSenh@123
SEI_ORGAO=28
SEI_UNIDADE=SEPLAG/AUTOMATIZAMG

# === Relatório Diário - Limites ===
SEI_REL_MAX_PROCESSOS_NOVOS_DIA=10
SEI_REL_MAX_TAMANHO_PDF_MB=100

# === Relatório Diário - Caminhos ===
SEI_REL_XLSX_PATH=saida/relatorio_diario.xlsx
SEI_REL_PDF_DIR=pdfs/relatorio_diario

# === Relatório Diário - E-mail ===
SEI_REL_EMAIL_FROM=noreply@exemplo.org.br
SEI_REL_EMAIL_TO=gerente@exemplo.org.br,equipe@exemplo.org.br
SEI_REL_SMTP_HOST=smtp.gmail.com
SEI_REL_SMTP_PORT=587
SEI_REL_SMTP_USER=noreply@exemplo.org.br
SEI_REL_SMTP_PASS=senha_app_gmail
SEI_REL_SMTP_USE_TLS=true

# === Opcionais ===
SEI_DEBUG=1
```

### 1.4 Configurações SMTP Comuns

#### Gmail
```env
SEI_REL_SMTP_HOST=smtp.gmail.com
SEI_REL_SMTP_PORT=587
SEI_REL_SMTP_USE_TLS=true
# Nota: Use senha de app, não a senha normal da conta
```

#### Outlook/Office 365
```env
SEI_REL_SMTP_HOST=smtp.office365.com
SEI_REL_SMTP_PORT=587
SEI_REL_SMTP_USE_TLS=true
```

#### Servidor SMTP Local/Corporativo
```env
SEI_REL_SMTP_HOST=smtp.suaempresa.com.br
SEI_REL_SMTP_PORT=587
SEI_REL_SMTP_USE_TLS=true
```

## 🚀 Passo 2: Primeira Execução (Baseline)

A primeira execução cria o histórico inicial com todos os processos da unidade.

### 2.1 Executar o Comando

```bash
# No diretório raiz do projeto
uv run sei-client relatorio-diario
```

### 2.2 O que Acontece na Primeira Execução

1. **Login no SEI** - Autentica e troca para a unidade configurada
2. **Coleta de processos** - Busca todos os processos (Recebidos + Gerados)
3. **Enriquecimento** - Coleta metadados de documentos de cada processo
4. **Histórico baseline** - Salva snapshot completo em `data/historico_processos.json`
5. **Planilha** - Gera `saida/relatorio_diario.xlsx` com todos os processos
6. **E-mail** - Envia e-mail de cadastro inicial com a planilha anexada

### 2.3 Verificar Resultados

```bash
# Verificar histórico criado
ls -lh data/historico_processos.json

# Verificar planilha gerada
ls -lh saida/relatorio_diario.xlsx

# Verificar e-mail enviado (caixa de entrada dos destinatários)
```

### 2.4 Saída Esperada no Terminal

```
10:30:15 [INFO] Abrindo página de login…
10:30:16 [INFO] Enviando POST de login…
10:30:17 [INFO] Autenticado com sucesso.
10:30:17 [INFO] Unidade SEI atual: SEPLAG/AUTOMATIZAMG
10:30:18 [INFO] Total de processos coletados: 105 (70 Recebidos, 35 Gerados)
10:30:25 [INFO] Executando baseline (primeira execução)...
10:30:45 [INFO] Histórico baseline salvo em data/historico_processos.json (105 processo(s))
10:30:46 [INFO] Planilha baseline gerada: saida/relatorio_diario.xlsx
10:30:47 [INFO] Enviando e-mail via SMTP smtp.gmail.com:587 (TLS: True) para 2 destinatário(s)...
10:30:50 [INFO] E-mail enviado com sucesso para: gerente@exemplo.org.br, equipe@exemplo.org.br
10:30:50 [INFO] E-mail de cadastro inicial enviado com sucesso.
```

### 2.5 Conteúdo do E-mail de Baseline

**Assunto:** `[SEI] Cadastro inicial concluído - SEPLAG/AUTOMATIZAMG`

**Corpo:**
- Informação sobre o cadastro inicial
- Total de processos registrados
- Distribuição (Recebidos vs Gerados)
- Planilha Excel anexada

## 📊 Passo 3: Execuções Seguintes (Relatório Diário)

Após a primeira execução, as próximas execuções identificam apenas processos novos e atualizados.

### 3.1 Executar Novamente

```bash
uv run sei-client relatorio-diario
```

### 3.2 O que Acontece nas Execuções Seguintes

1. **Login no SEI** - Autentica e valida unidade
2. **Snapshot atual** - Coleta todos os processos novamente
3. **Comparação** - Compara com histórico anterior para identificar:
   - **Processos novos**: ausentes no histórico
   - **Processos atualizados**: presentes mas com mudanças
4. **Aplicação de limites** - Seleciona até `SEI_REL_MAX_PROCESSOS_NOVOS_DIA` processos novos
5. **Download de PDFs** - Baixa PDFs dos processos novos + atualizados
   - Verifica tamanho máximo
   - Ignora PDFs que excedem o limite
6. **Atualização do histórico** - Salva snapshot atualizado com metadata
7. **Planilha** - Gera planilha com todos os processos e colunas de status
8. **E-mail** - Envia relatório estruturado com seções para novos, atualizados e não analisados

### 3.3 Saída Esperada no Terminal

```
10:30:15 [INFO] Executando relatório diário...
10:30:18 [INFO] Snapshot atual: 108 processos
10:30:20 [INFO] Processos novos: 3 | Processos atualizados: 5
10:30:25 [INFO] Baixando PDF para processo: 1500.01.0310980/2025-88
10:30:30 [INFO] PDF baixado com sucesso: processo_1500_01_0310980_2025-88.pdf (245.67 KB)
...
10:30:45 [INFO] Histórico atualizado salvo em data/historico_processos.json
10:30:46 [INFO] Planilha gerada: saida/relatorio_diario.xlsx
10:30:47 [INFO] Enviando e-mail via SMTP smtp.gmail.com:587 (TLS: True)...
10:30:50 [INFO] Relatório diário enviado por e-mail com sucesso.
```

### 3.4 Conteúdo do E-mail Diário

**Assunto:** `[SEI] Relatório diário - SEPLAG/AUTOMATIZAMG - 2025-01-15`

**Estrutura:**

#### Seção 1: Processos novos (N)
- Lista de processos que apareceram desde o último relatório
- Categoria (Recebidos/Gerados)
- Título
- Marcadores
- Status do PDF (se foi baixado e caminho)

#### Seção 2: Processos atualizados (M)
- Lista de processos com mudanças detectadas
- Quantidade de novos documentos
- Novos marcadores
- Status do PDF

#### Seção 3: Não analisados
- Processos que excederam limites (tamanho, quantidade)
- Motivo de não análise

**Anexo:** Planilha Excel com todos os processos e colunas de status

### 3.5 Verificar Arquivos Gerados

```bash
# Histórico atualizado
ls -lh data/historico_processos.json

# Planilha com status
ls -lh saida/relatorio_diario.xlsx

# PDFs baixados
ls -lh pdfs/relatorio_diario/

# Ver conteúdo da pasta de PDFs
find pdfs/relatorio_diario -name "*.pdf" -ls
```

## 🔍 Passo 4: Verificar e Analisar Resultados

### 4.1 Verificar Histórico JSON

```bash
# Ver estrutura do histórico
cat data/historico_processos.json | python -m json.tool | head -50

# Contar processos no histórico
cat data/historico_processos.json | python -c "import json, sys; data=json.load(sys.stdin); print(f'Total: {len(data)} processos')"

# Verificar metadata de um processo específico
cat data/historico_processos.json | python -c "import json, sys; data=json.load(sys.stdin); proc=data.get('PROC-001', {}); print(json.dumps(proc.get('_metadata', {}), indent=2))"
```

### 4.2 Analisar Planilha Excel

Abra o arquivo `saida/relatorio_diario.xlsx` no Excel ou similar:

**Colunas principais:**
- Número do Processo
- Categoria
- **É Novo Desde Último Relatório** (Sim/Não)
- **Teve Atualização Desde Último Relatório** (Sim/Não)
- **Ignorado Por Limite** (Sim/Não)
- **PDF Baixado** (Sim/Não)
- **Motivo Não Analisado** (texto explicativo)

**Filtros úteis:**
- Filtrar por "É Novo" = "Sim" para ver apenas novos
- Filtrar por "Teve Atualização" = "Sim" para ver atualizados
- Filtrar por "PDF Baixado" = "Sim" para ver processos com PDF disponível

### 4.3 Verificar PDFs Baixados

```bash
# Listar PDFs baixados
ls -lh pdfs/relatorio_diario/*.pdf

# Ver tamanho total dos PDFs
du -sh pdfs/relatorio_diario/

# Contar PDFs
find pdfs/relatorio_diario -name "*.pdf" | wc -l
```

### 4.4 Verificar Logs

Se houver problemas, os logs detalhados aparecem no terminal. Para mais detalhes:

```bash
# Executar com debug ativado
SEI_DEBUG=1 uv run sei-client relatorio-diario
```

## 🧪 Passo 5: Testes e Validações

### 5.1 Teste de Configuração (sem executar)

```bash
# Verificar se as variáveis estão configuradas
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

print('=== Configurações SEI ===')
print(f'SEI_USER: {os.getenv(\"SEI_USER\", \"NÃO CONFIGURADO\")}')
print(f'SEI_ORGAO: {os.getenv(\"SEI_ORGAO\", \"NÃO CONFIGURADO\")}')
print(f'SEI_UNIDADE: {os.getenv(\"SEI_UNIDADE\", \"NÃO CONFIGURADO\")}')

print('\n=== Configurações Relatório ===')
print(f'SEI_REL_MAX_PROCESSOS_NOVOS_DIA: {os.getenv(\"SEI_REL_MAX_PROCESSOS_NOVOS_DIA\", \"10 (default)\")}')
print(f'SEI_REL_EMAIL_FROM: {os.getenv(\"SEI_REL_EMAIL_FROM\", \"NÃO CONFIGURADO\")}')
print(f'SEI_REL_EMAIL_TO: {os.getenv(\"SEI_REL_EMAIL_TO\", \"NÃO CONFIGURADO\")}')
print(f'SEI_REL_SMTP_HOST: {os.getenv(\"SEI_REL_SMTP_HOST\", \"NÃO CONFIGURADO\")}')
"
```

### 5.2 Teste de Conexão SMTP (sem enviar e-mail real)

Crie um script de teste:

```python
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
    with smtplib.SMTP(host, port) as server:
        if use_tls:
            server.starttls()
        if user and password:
            server.login(user, password)
        print("✅ Conexão SMTP bem-sucedida!")
except Exception as e:
    print(f"❌ Erro na conexão SMTP: {e}")
```

Execute:
```bash
python test_smtp.py
```

### 5.3 Executar Testes Unitários

```bash
# Executar testes do módulo de relatório diário
uv run python -m pytest tests/test_relatorio_diario.py -v

# Executar todos os testes
uv run python -m pytest tests/ -v
```

## 🐛 Passo 6: Resolução de Problemas

### Problema 1: Erro de Autenticação SEI

**Sintomas:**
```
[ERROR] Falha no login.
```

**Soluções:**
- Verificar `SEI_USER` e `SEI_PASS` no `.env`
- Confirmar que as credenciais estão corretas
- Verificar se a conta não está bloqueada

### Problema 2: Erro de Unidade SEI

**Sintomas:**
```
[WARNING] Falha ao trocar unidade SEI para X. Continuando com a unidade atual.
```

**Soluções:**
- Verificar `SEI_UNIDADE` - deve ser exatamente como aparece no SEI
- Fazer login manual no SEI e verificar o nome exato da unidade
- O nome é case-insensitive, mas deve incluir barras e espaços corretamente

### Problema 3: Erro de Envio de E-mail

**Sintomas:**
```
[ERROR] Falha de autenticação SMTP
[ERROR] Erro SMTP ao enviar e-mail
```

**Soluções:**

1. **Gmail:**
   - Usar "Senha de App" (não a senha normal)
   - Ativar "Acesso a apps menos seguros" ou usar OAuth2
   - Verificar se 2FA está ativado (necessário para senha de app)

2. **Outlook/Office 365:**
   - Verificar se autenticação moderna está habilitada
   - Pode ser necessário usar autenticação OAuth2

3. **Servidor SMTP Corporativo:**
   - Verificar porta correta (587 ou 465)
   - Confirmar se TLS/SSL está configurado corretamente
   - Verificar firewall/proxy

4. **Teste manual:**
   ```bash
   # Usar script de teste SMTP (ver Passo 5.2)
   python test_smtp.py
   ```

### Problema 4: E-mail Enviado Mas Não Recebido

**Soluções:**
- Verificar pasta de spam/lixo eletrônico
- Confirmar lista de destinatários em `SEI_REL_EMAIL_TO`
- Verificar logs do servidor SMTP
- Verificar se o remetente (`SEI_REL_EMAIL_FROM`) está autorizado

### Problema 5: PDFs Não Estão Sendo Baixados

**Sintomas:**
```
[WARNING] PDF de X excede limite de tamanho: 150.23 MB
```

**Soluções:**
- Aumentar `SEI_REL_MAX_TAMANHO_PDF_MB` se necessário
- Verificar permissões da pasta `pdfs/relatorio_diario/`
- Verificar espaço em disco disponível

### Problema 6: Nenhum Processo Novo/Atualizado Detectado

**Causas possíveis:**
- O histórico está atualizado (tudo já foi processado)
- Os processos realmente não mudaram
- Problema na comparação de dados

**Verificação:**
```bash
# Ver data do último histórico
stat data/historico_processos.json

# Ver quantidade de processos no histórico
cat data/historico_processos.json | python -c "import json, sys; print(len(json.load(sys.stdin)))"
```

## 📅 Passo 7: Automação (Opcional)

### 7.1 Windows (Agendador de Tarefas)

1. Abrir "Agendador de Tarefas"
2. Criar nova tarefa básica
3. Configurar:
   - **Nome:** Relatório Diário SEI
   - **Gatilho:** Diariamente, às 08:00
   - **Ação:** Iniciar programa
   - **Programa:** `C:\caminho\para\uv.exe`
   - **Argumentos:** `run sei-client relatorio-diario`
   - **Iniciar em:** Diretório do projeto

### 7.2 Linux/macOS (Cron)

Editar crontab:
```bash
crontab -e
```

Adicionar linha (executa todo dia às 08:00):
```cron
0 8 * * * cd /caminho/para/projeto && /caminho/para/uv run sei-client relatorio-diario >> logs/relatorio_diario.log 2>&1
```

## ✅ Checklist Final

Antes de considerar tudo configurado, verifique:

- [ ] Arquivo `.env` configurado com todas as variáveis
- [ ] Credenciais SEI testadas e funcionando
- [ ] Primeira execução (baseline) concluída com sucesso
- [ ] E-mail de cadastro inicial recebido
- [ ] Histórico JSON criado em `data/historico_processos.json`
- [ ] Planilha Excel gerada em `saida/relatorio_diario.xlsx`
- [ ] Segunda execução identificou processos novos/atualizados (se houver)
- [ ] E-mail de relatório diário recebido corretamente
- [ ] PDFs sendo baixados corretamente (se houver processos novos/atualizados)
- [ ] Logs não mostram erros críticos

## 📚 Referências

- Documentação completa: `README.md`
- Arquitetura do sistema: `docs/architecture.md`
- Testes unitários: `tests/test_relatorio_diario.py`

## 💡 Dicas

1. **Primeira vez:** Execute em horário de menor uso do SEI para evitar impacto
2. **Frequência:** Execute uma vez por dia, preferencialmente pela manhã
3. **Monitoramento:** Verifique os logs após cada execução
4. **Backup:** Faça backup periódico do arquivo `data/historico_processos.json`
5. **Limpeza:** Periodicamente limpe a pasta `pdfs/relatorio_diario/` para liberar espaço

---

**Suporte:** Em caso de problemas, verifique os logs detalhados com `SEI_DEBUG=1` e consulte a seção de Resolução de Problemas acima.

