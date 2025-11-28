"""Módulo de relatórios diários automatizados do SEI enviados por e-mail."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from openpyxl import Workbook

from .client import SeiClient
from .config import Settings, _str_to_bool, load_settings
from .email_utils import enviar_email_relatorio
from .models import FilterOptions, PaginationOptions, PDFDownloadResult, Processo
from .storage import (
    carregar_historico_processos,
    exportar_processos_para_excel,
    salvar_historico_processos,
)

log = logging.getLogger(__name__)


@dataclass
class DailyReportSettings:
    """Configurações para o relatório diário de processos do SEI."""

    # Restrições de análise
    max_processos_novos: int = 10
    max_tamanho_pdf_mb: int = 100

    # Caminhos de saída
    historico_arquivo: Path = Path("data/historico_processos.json")
    pdf_dir: Path = Path("pdfs/relatorio_diario")
    xlsx_path: Path = Path("saida/relatorio_diario.xlsx")

    # Configuração de e-mail
    email_from: Optional[str] = None
    email_to: List[str] = field(default_factory=list)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_pass: Optional[str] = None
    smtp_use_tls: bool = True


def load_daily_report_settings(settings_base: Optional[Settings] = None) -> DailyReportSettings:
    """
    Carrega configurações do relatório diário a partir de variáveis de ambiente.

    Args:
        settings_base: Configurações base do SEI (opcional, usado para caminhos padrão).

    Returns:
        Instância de DailyReportSettings preenchida com valores de ambiente ou defaults.
    """
    env = os.environ
    settings = settings_base or load_settings()

    # Restrições
    max_processos_novos = 10
    if env.get("SEI_REL_MAX_PROCESSOS_NOVOS_DIA"):
        try:
            max_processos_novos = int(env["SEI_REL_MAX_PROCESSOS_NOVOS_DIA"])
            if max_processos_novos < 1:
                max_processos_novos = 10
        except ValueError:
            log.warning("Valor inválido para SEI_REL_MAX_PROCESSOS_NOVOS_DIA, usando default: 10")

    max_tamanho_pdf_mb = 100
    if env.get("SEI_REL_MAX_TAMANHO_PDF_MB"):
        try:
            max_tamanho_pdf_mb = int(env["SEI_REL_MAX_TAMANHO_PDF_MB"])
            if max_tamanho_pdf_mb < 1:
                max_tamanho_pdf_mb = 100
        except ValueError:
            log.warning("Valor inválido para SEI_REL_MAX_TAMANHO_PDF_MB, usando default: 100")

    # Caminhos
    historico_arquivo = settings.historico_path
    if env.get("SEI_REL_HISTORICO_ARQUIVO"):
        historico_arquivo = Path(env["SEI_REL_HISTORICO_ARQUIVO"]).expanduser()
        if not historico_arquivo.is_absolute():
            historico_arquivo = settings.data_dir / historico_arquivo

    pdf_dir = Path("pdfs/relatorio_diario")
    if env.get("SEI_REL_PDF_DIR"):
        pdf_dir = Path(env["SEI_REL_PDF_DIR"]).expanduser()
        if not pdf_dir.is_absolute():
            pdf_dir = Path(env["SEI_REL_PDF_DIR"])

    xlsx_path = Path("saida/relatorio_diario.xlsx")
    if env.get("SEI_REL_XLSX_PATH"):
        xlsx_path = Path(env["SEI_REL_XLSX_PATH"]).expanduser()
        if not xlsx_path.is_absolute():
            xlsx_path = Path(env["SEI_REL_XLSX_PATH"])

    # E-mail
    email_from = env.get("SEI_REL_EMAIL_FROM")
    email_to_raw = env.get("SEI_REL_EMAIL_TO", "")
    email_to = [e.strip() for e in email_to_raw.split(",") if e.strip()] if email_to_raw else []

    smtp_host = env.get("SEI_REL_SMTP_HOST")
    smtp_port = 587
    if env.get("SEI_REL_SMTP_PORT"):
        try:
            smtp_port = int(env["SEI_REL_SMTP_PORT"])
        except ValueError:
            log.warning("Valor inválido para SEI_REL_SMTP_PORT, usando default: 587")

    smtp_user = env.get("SEI_REL_SMTP_USER")
    smtp_pass = env.get("SEI_REL_SMTP_PASS")
    smtp_use_tls = _str_to_bool(env.get("SEI_REL_SMTP_USE_TLS")) is not False  # default True

    return DailyReportSettings(
        max_processos_novos=max_processos_novos,
        max_tamanho_pdf_mb=max_tamanho_pdf_mb,
        historico_arquivo=historico_arquivo,
        pdf_dir=pdf_dir,
        xlsx_path=xlsx_path,
        email_from=email_from,
        email_to=email_to,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_pass=smtp_pass,
        smtp_use_tls=smtp_use_tls,
    )


def _is_primeira_execucao(historico_path: Path) -> bool:
    """Verifica se é a primeira execução (histórico não existe ou está vazio)."""
    if not historico_path.exists():
        return True
    try:
        historico = carregar_historico_processos(None, historico_path)  # type: ignore
        return len(historico) == 0
    except Exception:
        return True


def _adicionar_metadata_historico(dados: Dict[str, Any], data_execucao: str, tipo: str) -> Dict[str, Any]:
    """
    Adiciona campos de metadata ao dicionário de dados do processo.

    Args:
        dados: Dicionário com dados do processo.
        data_execucao: Data/hora da execução no formato ISO.
        tipo: Tipo de operação ('primeira_vez' ou 'atualizacao').

    Returns:
        Dicionário com metadata adicionada.
    """
    if "_metadata" not in dados:
        dados["_metadata"] = {}

    metadata = dados["_metadata"]

    if tipo == "primeira_vez":
        metadata["data_primeira_vez_visto"] = data_execucao
        metadata["data_ultima_vez_visto"] = data_execucao
    elif tipo == "atualizacao":
        metadata["data_ultima_vez_visto"] = data_execucao
        if "data_ultima_atualizacao" not in metadata:
            metadata["data_ultima_atualizacao"] = data_execucao
        else:
            metadata["data_ultima_atualizacao"] = data_execucao

    return dados


def _identificar_processos_novos_e_atualizados(
    historico_anterior: Dict[str, Dict[str, Any]], snapshot_atual: List[Processo]
) -> Tuple[List[Processo], List[Processo]]:
    """
    Identifica processos novos e atualizados comparando snapshot atual com histórico anterior.

    Args:
        historico_anterior: Dicionário do histórico anterior (chave: id_procedimento).
        snapshot_atual: Lista de processos do snapshot atual.

    Returns:
        Tupla (processos_novos, processos_atualizados).
    """
    processos_novos: List[Processo] = []
    processos_atualizados: List[Processo] = []

    for processo in snapshot_atual:
        chave = processo.id_procedimento or processo.numero_processo
        historico_proc = historico_anterior.get(chave)

        if not historico_proc:
            # Processo novo
            processos_novos.append(processo)
        else:
            # Verificar se houve atualizações
            atualizado = False

            # Novos documentos (comparação por ID - detecta documentos realmente novos)
            docs_anteriores_ids = {doc.get("id_documento") for doc in historico_proc.get("documentos", [])}
            docs_atuais_ids = {doc.id_documento for doc in processo.documentos}
            if docs_atuais_ids - docs_anteriores_ids:
                atualizado = True

            # NOTA: Removida verificação de doc.eh_novo porque esse campo indica
            # status do SEI (ex: não visualizado), não se o documento é novo desde
            # o último relatório. A comparação de IDs acima já detecta documentos
            # realmente novos corretamente.

            # Mudanças em marcadores (normaliza strings vazias para comparação correta)
            marcadores_anteriores = {m for m in historico_proc.get("marcadores", []) if m and m.strip()}
            marcadores_atuais = {m for m in processo.marcadores if m and m.strip()}
            if marcadores_anteriores != marcadores_atuais:
                atualizado = True

            # NOTA: Removida verificação de tem_documentos_novos e tem_anotacoes porque
            # esses campos são estados do SEI (indicadores visuais), não mudanças desde
            # o último relatório. Novos documentos já são detectados pela comparação de
            # IDs acima. Esses campos podem mudar mesmo sem mudanças reais (ex: se
            # alguém visualizou documentos, tem_documentos_novos muda de True para False,
            # mas isso não indica uma atualização desde o último relatório).

            # Mudanças em assinantes
            assinantes_anteriores = set(historico_proc.get("assinantes", []))
            assinantes_atuais = set(processo.assinantes)
            if assinantes_anteriores != assinantes_atuais:
                atualizado = True

            if atualizado:
                processos_atualizados.append(processo)

    return processos_novos, processos_atualizados


def _aplicar_limites_processos(processos: List[Processo], max_novos: int) -> Tuple[List[Processo], List[Processo]]:
    """
    Aplica limite de processos novos a serem analisados (mantém ordem do SEI).

    Args:
        processos: Lista de processos novos.
        max_novos: Número máximo de processos a selecionar.

    Returns:
        Tupla (processos_selecionados, processos_ignorados).
    """
    if len(processos) <= max_novos:
        return processos, []

    selecionados = processos[:max_novos]
    ignorados = processos[max_novos:]
    return selecionados, ignorados


def _baixar_pdfs_com_limite(
    client: SeiClient, processos: List[Processo], settings: DailyReportSettings
) -> Dict[str, Tuple[PDFDownloadResult, Optional[str]]]:
    """
    Baixa PDFs dos processos respeitando limite de tamanho.

    Args:
        client: Instância do SeiClient autenticado.
        processos: Lista de processos para baixar PDFs.
        settings: Configurações do relatório diário.

    Returns:
        Dicionário {id_procedimento: (PDFDownloadResult, motivo_nao_analisado)}.
    """
    resultados: Dict[str, Tuple[PDFDownloadResult, Optional[str]]] = {}
    max_tamanho_bytes = settings.max_tamanho_pdf_mb * 1024 * 1024

    settings.pdf_dir.mkdir(parents=True, exist_ok=True)

    for processo in processos:
        chave = processo.id_procedimento or processo.numero_processo
        log.info("Baixando PDF para processo: %s", processo.numero_processo)

        try:
            resultado = client.generate_pdf(processo, diretorio_saida=str(settings.pdf_dir))

            motivo: Optional[str] = None

            if not resultado.sucesso or not resultado.caminho:
                motivo = resultado.erro or "Falha desconhecida no download"
                log.warning("Falha ao baixar PDF para %s: %s", processo.numero_processo, motivo)
            elif resultado.caminho.exists():
                tamanho = resultado.caminho.stat().st_size
                if tamanho > max_tamanho_bytes:
                    motivo = f"PDF > {settings.max_tamanho_pdf_mb}MB ({tamanho / (1024*1024):.2f}MB)"
                    log.warning(
                        "PDF de %s excede limite de tamanho: %.2f MB",
                        processo.numero_processo,
                        tamanho / (1024 * 1024),
                    )
                else:
                    log.info("PDF baixado com sucesso: %s (%.2f KB)", resultado.caminho.name, tamanho / 1024)

            resultados[chave] = (resultado, motivo)

        except Exception as exc:
            log.exception("Erro inesperado ao baixar PDF para %s: %s", processo.numero_processo, exc)
            # Criar resultado de falha
            from .models import PDFDownloadResult

            resultado_falha = PDFDownloadResult(
                processo=processo,
                sucesso=False,
                erro=str(exc),
            )
            resultados[chave] = (resultado_falha, f"Erro: {exc}")

    return resultados


def _atualizar_historico_com_datas(
    historico: Dict[str, Dict[str, Any]], processos: List[Processo], data_execucao: str
) -> Dict[str, Dict[str, Any]]:
    """
    Atualiza histórico adicionando campos de data para processos.

    Args:
        historico: Histórico existente.
        processos: Lista de processos a adicionar/atualizar.
        data_execucao: Data/hora da execução no formato ISO.

    Returns:
        Histórico atualizado.
    """
    from .storage import processo_para_dict

    for processo in processos:
        chave = processo.id_procedimento or processo.numero_processo
        if not chave:
            continue

        dados = processo_para_dict(processo)

        if chave not in historico:
            # Processo novo
            _adicionar_metadata_historico(dados, data_execucao, "primeira_vez")
        else:
            # Processo existente - atualizar metadata
            _adicionar_metadata_historico(dados, data_execucao, "atualizacao")

        historico[chave] = dados

    return historico


def _gerar_planilha_com_status(
    processos: List[Processo],
    processos_novos: Set[str],
    processos_atualizados: Set[str],
    processos_com_pdf: Set[str],
    processos_ignorados: Dict[str, str],
    settings: DailyReportSettings,
) -> Path:
    """
    Gera planilha XLSX com todos os processos e colunas de status.

    Args:
        processos: Lista de todos os processos da unidade.
        processos_novos: Set de IDs de processos novos.
        processos_atualizados: Set de IDs de processos atualizados.
        processos_com_pdf: Set de IDs de processos com PDF baixado.
        processos_ignorados: Dicionário {id: motivo} para processos ignorados.
        settings: Configurações do relatório diário.

    Returns:
        Caminho do arquivo XLSX gerado.
    """
    settings.xlsx_path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    if ws is None:
        ws = wb.create_sheet("Processos")
    else:
        ws.title = "Processos"

    cabecalho = [
        "Número do Processo",
        "Categoria",
        "Visualizado",
        "Título",
        "Tipo/Especificidade",
        "Responsável",
        "CPF Responsável",
        "Marcadores",
        "Documentos Novos",
        "Anotações",
        "ID Procedimento",
        "Hash",
        "URL",
        "É Novo Desde Último Relatório",
        "Teve Atualização Desde Último Relatório",
        "Ignorado Por Limite",
        "PDF Baixado",
        "Motivo Não Analisado",
    ]
    ws.append(cabecalho)

    for proc in processos:
        chave = proc.id_procedimento or proc.numero_processo
        eh_novo = chave in processos_novos
        teve_atualizacao = chave in processos_atualizados
        ignorado = chave in processos_ignorados
        pdf_baixado = chave in processos_com_pdf
        motivo = processos_ignorados.get(chave, "")

        ws.append(
            [
                proc.numero_processo,
                proc.categoria,
                "Sim" if proc.visualizado else "Não",
                proc.titulo or "",
                proc.tipo_especificidade or "",
                proc.responsavel_nome or "",
                proc.responsavel_cpf or "",
                ", ".join(proc.marcadores),
                "Sim" if proc.tem_documentos_novos else "Não",
                "Sim" if proc.tem_anotacoes else "Não",
                proc.id_procedimento,
                proc.hash,
                proc.url,
                "Sim" if eh_novo else "Não",
                "Sim" if teve_atualizacao else "Não",
                "Sim" if ignorado else "Não",
                "Sim" if pdf_baixado else "Não",
                motivo,
            ]
        )

    wb.save(settings.xlsx_path)
    log.info("Planilha gerada: %s", settings.xlsx_path)
    return settings.xlsx_path


def _construir_corpo_email_texto(
    unidade: str,
    data_relatorio: str,
    processos_novos: List[Processo],
    processos_atualizados: List[Processo],
    processos_ignorados: Dict[str, str],
    processos_com_pdf: Set[str],
    caminhos_pdf: Dict[str, Path],
) -> str:
    """
    Constrói corpo do e-mail em texto puro.

    Args:
        unidade: Nome da unidade SEI.
        data_relatorio: Data do relatório no formato legível.
        processos_novos: Lista de processos novos.
        processos_atualizados: Lista de processos atualizados.
        processos_ignorados: Dicionário {id: motivo} para processos ignorados.
        processos_com_pdf: Set de IDs de processos com PDF baixado.
        caminhos_pdf: Dicionário {id: caminho} dos PDFs baixados.

    Returns:
        Corpo do e-mail em texto puro.
    """
    linhas = [f"[SEI] Relatório diário - {unidade} - {data_relatorio}", ""]

    # Processos novos
    linhas.append(f"1. Processos novos ({len(processos_novos)}):")
    linhas.append("")
    if processos_novos:
        for proc in processos_novos:
            chave = proc.id_procedimento or proc.numero_processo
            marcadores_str = ", ".join(proc.marcadores) if proc.marcadores else "(nenhum)"
            pdf_info = ""
            if chave in processos_com_pdf and chave in caminhos_pdf:
                pdf_info = f" | PDF: baixado em {caminhos_pdf[chave]}"
            linhas.append(
                f"   - {proc.numero_processo} | {proc.categoria} | "
                f"Título: {proc.titulo or '(sem título)'} | "
                f"Marcadores: {marcadores_str}{pdf_info}"
            )
    else:
        linhas.append("   (nenhum processo novo)")
    linhas.append("")

    # Processos atualizados
    linhas.append(f"2. Processos atualizados ({len(processos_atualizados)}):")
    linhas.append("")
    if processos_atualizados:
        for proc in processos_atualizados:
            chave = proc.id_procedimento or proc.numero_processo
            docs_novos_count = sum(1 for doc in proc.documentos if doc.eh_novo)
            marcadores_novos = ", ".join(proc.marcadores) if proc.marcadores else "(nenhum)"
            pdf_info = ""
            if chave in processos_com_pdf and chave in caminhos_pdf:
                pdf_info = f" | PDF: já existente em {caminhos_pdf[chave]}"
            linhas.append(
                f"   - {proc.numero_processo} | "
                f"Novos docs: {docs_novos_count} | "
                f"Novos marcadores: [{marcadores_novos}]{pdf_info}"
            )
    else:
        linhas.append("   (nenhum processo atualizado)")
    linhas.append("")

    # Não analisados
    if processos_ignorados:
        linhas.append(f"3. Não analisados (limite/tamanho/erro) ({len(processos_ignorados)}):")
        linhas.append("")
        for proc_id, motivo in list(processos_ignorados.items())[:10]:  # Limitar a 10
            linhas.append(f"   - {proc_id} | Motivo: {motivo}")
        if len(processos_ignorados) > 10:
            linhas.append(f"   ... e mais {len(processos_ignorados) - 10} processo(s)")
        linhas.append("")

    linhas.append("Observação: resumos automáticos ainda não implementados (fase LLM futura).")

    return "\n".join(linhas)


def _construir_corpo_email_html(
    unidade: str,
    data_relatorio: str,
    processos_novos: List[Processo],
    processos_atualizados: List[Processo],
    processos_ignorados: Dict[str, str],
    processos_com_pdf: Set[str],
    caminhos_pdf: Dict[str, Path],
) -> str:
    """
    Constrói corpo do e-mail em HTML.

    Args:
        unidade: Nome da unidade SEI.
        data_relatorio: Data do relatório no formato legível.
        processos_novos: Lista de processos novos.
        processos_atualizados: Lista de processos atualizados.
        processos_ignorados: Dicionário {id: motivo} para processos ignorados.
        processos_com_pdf: Set de IDs de processos com PDF baixado.
        caminhos_pdf: Dicionário {id: caminho} dos PDFs baixados.

    Returns:
        Corpo do e-mail em HTML.
    """
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head><meta charset='UTF-8'></head>",
        "<body style='font-family: Arial, sans-serif;'>",
        f"<h1>[SEI] Relatório diário - {unidade} - {data_relatorio}</h1>",
    ]

    # Processos novos
    html_parts.append(f"<h2>1. Processos novos ({len(processos_novos)})</h2>")
    if processos_novos:
        html_parts.append("<ul>")
        for proc in processos_novos:
            chave = proc.id_procedimento or proc.numero_processo
            marcadores_str = ", ".join(proc.marcadores) if proc.marcadores else "(nenhum)"
            pdf_info = ""
            if chave in processos_com_pdf and chave in caminhos_pdf:
                pdf_info = f" | <strong>PDF:</strong> baixado em {caminhos_pdf[chave]}"
            html_parts.append(
                f"<li><strong>{proc.numero_processo}</strong> | {proc.categoria} | "
                f"Título: {proc.titulo or '(sem título)'} | "
                f"Marcadores: {marcadores_str}{pdf_info}</li>"
            )
        html_parts.append("</ul>")
    else:
        html_parts.append("<p>(nenhum processo novo)</p>")

    # Processos atualizados
    html_parts.append(f"<h2>2. Processos atualizados ({len(processos_atualizados)})</h2>")
    if processos_atualizados:
        html_parts.append("<ul>")
        for proc in processos_atualizados:
            chave = proc.id_procedimento or proc.numero_processo
            docs_novos_count = sum(1 for doc in proc.documentos if doc.eh_novo)
            marcadores_novos = ", ".join(proc.marcadores) if proc.marcadores else "(nenhum)"
            pdf_info = ""
            if chave in processos_com_pdf and chave in caminhos_pdf:
                pdf_info = f" | <strong>PDF:</strong> já existente em {caminhos_pdf[chave]}"
            html_parts.append(
                f"<li><strong>{proc.numero_processo}</strong> | "
                f"Novos docs: {docs_novos_count} | "
                f"Novos marcadores: [{marcadores_novos}]{pdf_info}</li>"
            )
        html_parts.append("</ul>")
    else:
        html_parts.append("<p>(nenhum processo atualizado)</p>")

    # Não analisados
    if processos_ignorados:
        html_parts.append(f"<h2>3. Não analisados (limite/tamanho/erro) ({len(processos_ignorados)})</h2>")
        html_parts.append("<ul>")
        for proc_id, motivo in list(processos_ignorados.items())[:10]:
            html_parts.append(f"<li><strong>{proc_id}</strong> | Motivo: {motivo}</li>")
        if len(processos_ignorados) > 10:
            html_parts.append(f"<li>... e mais {len(processos_ignorados) - 10} processo(s)</li>")
        html_parts.append("</ul>")

    html_parts.append("<p><em>Observação: resumos automáticos ainda não implementados (fase LLM futura).</em></p>")
    html_parts.append("</body>")
    html_parts.append("</html>")

    return "\n".join(html_parts)


def _executar_baseline(client: SeiClient, settings: DailyReportSettings, settings_base: Settings) -> None:
    """
    Executa primeira execução (baseline): coleta todos os processos e salva histórico inicial.

    Args:
        client: Instância do SeiClient autenticado.
        settings: Configurações do relatório diário.
        settings_base: Configurações base do SEI.
    """
    log.info("Executando baseline (primeira execução)...")

    # Coletar todos os processos
    filtros = FilterOptions()
    paginacao = PaginationOptions()

    todos_processos, processos_filtrados = client.collect_processes(filtros, paginacao)
    
    # Separar recebidos de gerados pela categoria
    processos_recebidos = [p for p in todos_processos if p.categoria == "Recebidos"]
    processos_gerados = [p for p in todos_processos if p.categoria == "Gerados"]

    log.info("Total de processos coletados: %s (Recebidos: %s, Gerados: %s)", len(todos_processos), len(processos_recebidos), len(processos_gerados))

    # Enriquecer com documentos
    from .models import EnrichmentOptions

    # Limite opcional para primeira execução (para testes rápidos)
    limite_baseline = os.getenv("SEI_REL_LIMITE_BASELINE")
    if limite_baseline:
        try:
            limite = int(limite_baseline)
            if limite > 0 and limite < len(todos_processos):
                log.info("Limitando baseline a %s processos (SEI_REL_LIMITE_BASELINE)", limite)
                todos_processos = todos_processos[:limite]
        except ValueError:
            pass

    enrichment = EnrichmentOptions(coletar_documentos=True)
    todos_processos = client.enrich_processes(todos_processos, enrichment)

    # Salvar histórico com metadata
    data_execucao = datetime.now().isoformat()
    historico_dict: Dict[str, Dict[str, Any]] = {}
    historico_dict = _atualizar_historico_com_datas(historico_dict, todos_processos, data_execucao)

    # Converter para lista de processos temporariamente para usar salvar_historico_processos
    # Mas precisamos salvar com metadata, então vamos salvar diretamente
    from .storage import processo_para_dict
    import json

    historico_para_salvar: Dict[str, Dict[str, Any]] = {}
    for processo in todos_processos:
        chave = processo.id_procedimento or processo.numero_processo
        if not chave:
            continue
        dados = processo_para_dict(processo)
        _adicionar_metadata_historico(dados, data_execucao, "primeira_vez")
        historico_para_salvar[chave] = dados

    settings.historico_arquivo.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.historico_arquivo, "w", encoding="utf-8") as f:
        json.dump(historico_para_salvar, f, ensure_ascii=False, indent=2)

    log.info("Histórico baseline salvo em %s (%s processo(s))", settings.historico_arquivo, len(historico_para_salvar))

    # Gerar planilha
    exportar_processos_para_excel(todos_processos, str(settings.xlsx_path))
    log.info("Planilha baseline gerada: %s", settings.xlsx_path)

    # Enviar e-mail
    data_relatorio = datetime.now().strftime("%Y-%m-%d")
    unidade = settings_base.unidade_alvo
    assunto = f"[SEI] Cadastro inicial concluído - {unidade}"

    corpo_texto = f"""Cadastro inicial concluído

O histórico inicial dos processos da unidade {unidade} foi gerado com sucesso.

Total de processos registrados: {len(todos_processos)}
- Recebidos: {len(processos_recebidos)}
- Gerados: {len(processos_gerados)}

A partir da próxima execução, os relatórios diários passarão a destacar apenas processos novos e atualizados.

Planilha completa anexada.
"""

    corpo_html = f"""<!DOCTYPE html>
<html>
<head><meta charset='UTF-8'></head>
<body style='font-family: Arial, sans-serif;'>
<h1>[SEI] Cadastro inicial concluído - {unidade}</h1>
<p>O histórico inicial dos processos da unidade <strong>{unidade}</strong> foi gerado com sucesso.</p>
<ul>
<li><strong>Total de processos registrados:</strong> {len(todos_processos)}</li>
<li><strong>Recebidos:</strong> {len(processos_recebidos)}</li>
<li><strong>Gerados:</strong> {len(processos_gerados)}</li>
</ul>
<p>A partir da próxima execução, os relatórios diários passarão a destacar apenas processos novos e atualizados.</p>
<p>Planilha completa anexada.</p>
</body>
</html>
"""

    try:
        enviar_email_relatorio(settings, assunto, corpo_texto, corpo_html, anexo_xlsx=settings.xlsx_path)
        log.info("E-mail de cadastro inicial enviado com sucesso.")
    except Exception as exc:
        log.error("Erro ao enviar e-mail de cadastro inicial: %s", exc)
        log.info("Relatório gerado em %s mesmo com falha no envio de e-mail.", settings.xlsx_path)


def _executar_relatorio_diario(
    client: SeiClient, settings: DailyReportSettings, historico_anterior: Dict[str, Dict[str, Any]], settings_base: Settings
) -> None:
    """
    Executa rotina diária: identifica processos novos/atualizados, baixa PDFs e envia relatório.

    Args:
        client: Instância do SeiClient autenticado.
        settings: Configurações do relatório diário.
        historico_anterior: Histórico anterior carregado.
        settings_base: Configurações base do SEI.
    """
    log.info("Executando relatório diário...")

    # Coletar snapshot atual
    filtros = FilterOptions()
    paginacao = PaginationOptions()

    todos_processos, processos_filtrados = client.collect_processes(filtros, paginacao)
    
    # Separar recebidos de gerados pela categoria (apenas para log)
    processos_recebidos = [p for p in todos_processos if p.categoria == "Recebidos"]
    processos_gerados = [p for p in todos_processos if p.categoria == "Gerados"]
    snapshot_atual = todos_processos

    log.info("Snapshot atual: %s processos (Recebidos: %s, Gerados: %s)", len(snapshot_atual), len(processos_recebidos), len(processos_gerados))

    # Enriquecer com documentos
    from .models import EnrichmentOptions

    enrichment = EnrichmentOptions(coletar_documentos=True)
    snapshot_atual = client.enrich_processes(snapshot_atual, enrichment)

    # Identificar processos novos e atualizados
    processos_novos, processos_atualizados = _identificar_processos_novos_e_atualizados(historico_anterior, snapshot_atual)
    log.info("Processos novos: %s | Processos atualizados: %s", len(processos_novos), len(processos_atualizados))

    # Aplicar limite de processos novos
    processos_novos_selecionados, processos_novos_ignorados = _aplicar_limites_processos(processos_novos, settings.max_processos_novos)
    processos_ignorados: Dict[str, str] = {}
    for proc in processos_novos_ignorados:
        chave = proc.id_procedimento or proc.numero_processo
        processos_ignorados[chave] = "Limite de processos novos excedido"

    # Baixar PDFs (novos + atualizados)
    processos_para_pdf = processos_novos_selecionados + processos_atualizados
    resultados_pdf = _baixar_pdfs_com_limite(client, processos_para_pdf, settings)

    # Processar resultados de PDF
    processos_com_pdf: Set[str] = set()
    caminhos_pdf: Dict[str, Path] = {}
    for chave, (resultado, motivo) in resultados_pdf.items():
        if resultado.sucesso and resultado.caminho and motivo is None:
            processos_com_pdf.add(chave)
            caminhos_pdf[chave] = resultado.caminho
        elif motivo:
            processos_ignorados[chave] = motivo

    # Atualizar histórico
    data_execucao = datetime.now().isoformat()
    historico_atualizado = historico_anterior.copy()
    historico_atualizado = _atualizar_historico_com_datas(historico_atualizado, snapshot_atual, data_execucao)

    # Persistir histórico atualizado
    from .storage import processo_para_dict
    import json

    historico_para_salvar: Dict[str, Dict[str, Any]] = {}
    for processo in snapshot_atual:
        chave = processo.id_procedimento or processo.numero_processo
        if not chave:
            continue
        dados = processo_para_dict(processo)
        if chave in historico_atualizado:
            # Preservar metadata existente e atualizar
            metadata_existente = historico_atualizado[chave].get("_metadata", {})
            dados["_metadata"] = metadata_existente
            if chave not in historico_anterior:
                _adicionar_metadata_historico(dados, data_execucao, "primeira_vez")
            else:
                _adicionar_metadata_historico(dados, data_execucao, "atualizacao")
        historico_para_salvar[chave] = dados

    settings.historico_arquivo.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.historico_arquivo, "w", encoding="utf-8") as f:
        json.dump(historico_para_salvar, f, ensure_ascii=False, indent=2)

    log.info("Histórico atualizado salvo em %s", settings.historico_arquivo)

    # Gerar planilha com status
    processos_novos_ids = {proc.id_procedimento or proc.numero_processo for proc in processos_novos}
    processos_atualizados_ids = {proc.id_procedimento or proc.numero_processo for proc in processos_atualizados}
    _gerar_planilha_com_status(
        snapshot_atual,
        processos_novos_ids,
        processos_atualizados_ids,
        processos_com_pdf,
        processos_ignorados,
        settings,
    )

    # Construir e enviar e-mail
    data_relatorio = datetime.now().strftime("%Y-%m-%d")
    unidade = settings_base.unidade_alvo
    assunto = f"[SEI] Relatório diário - {unidade} - {data_relatorio}"

    corpo_texto = _construir_corpo_email_texto(
        unidade,
        data_relatorio,
        processos_novos_selecionados,
        processos_atualizados,
        processos_ignorados,
        processos_com_pdf,
        caminhos_pdf,
    )

    corpo_html = _construir_corpo_email_html(
        unidade,
        data_relatorio,
        processos_novos_selecionados,
        processos_atualizados,
        processos_ignorados,
        processos_com_pdf,
        caminhos_pdf,
    )

    try:
        enviar_email_relatorio(settings, assunto, corpo_texto, corpo_html, anexo_xlsx=settings.xlsx_path)
        log.info("Relatório diário enviado por e-mail com sucesso.")
    except Exception as exc:
        log.error("Erro ao enviar e-mail do relatório diário: %s", exc)
        log.info("Relatório gerado em %s mesmo com falha no envio de e-mail.", settings.xlsx_path)


def run_daily_report(settings: DailyReportSettings | None = None) -> None:
    """
    Função principal que executa o relatório diário completo.

    Args:
        settings: Configurações do relatório diário (opcional, carrega de env se None).
    """
    settings_base = load_settings()

    if settings is None:
        settings = load_daily_report_settings(settings_base)

    # Instanciar cliente
    client = SeiClient(settings=settings_base)

    try:
        # Login e troca de unidade
        client.login()

        # Carregar histórico anterior
        historico_anterior = carregar_historico_processos(settings_base, settings.historico_arquivo)

        # Verificar se é primeira execução
        if _is_primeira_execucao(settings.historico_arquivo):
            _executar_baseline(client, settings, settings_base)
        else:
            _executar_relatorio_diario(client, settings, historico_anterior, settings_base)

    finally:
        client.close()

