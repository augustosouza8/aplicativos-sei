"""Utilitários para envio de e-mails de relatórios diários do SEI."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .relatorio_diario import DailyReportSettings

log = logging.getLogger(__name__)


def enviar_email_relatorio(
    settings: Any,  # DailyReportSettings - usando Any para evitar import circular
    assunto: str,
    corpo_texto: str,
    corpo_html: str,
    anexo_xlsx: Path | None = None,
) -> None:
    """
    Envia e-mail com relatório diário do SEI.

    Suporta multipart/alternative (texto + HTML) e anexa planilha XLSX se fornecida.

    Args:
        settings: Configurações do relatório diário com dados SMTP.
        assunto: Assunto do e-mail.
        corpo_texto: Versão em texto puro do corpo do e-mail.
        corpo_html: Versão HTML do corpo do e-mail.
        anexo_xlsx: Caminho opcional para planilha XLSX a ser anexada.

    Raises:
        ValueError: Se configurações SMTP obrigatórias estiverem ausentes.
        Exception: Erro de rede ou autenticação SMTP (logado antes de lançar).
    """
    if not settings.email_from:
        raise ValueError("SEI_REL_EMAIL_FROM é obrigatório para envio de e-mail.")

    if not settings.email_to:
        raise ValueError("SEI_REL_EMAIL_TO é obrigatório para envio de e-mail (pelo menos um destinatário).")

    if not settings.smtp_host:
        raise ValueError("SEI_REL_SMTP_HOST é obrigatório para envio de e-mail.")

    if not settings.smtp_user or not settings.smtp_pass:
        log.warning(
            "SEI_REL_SMTP_USER ou SEI_REL_SMTP_PASS não configurados. "
            "Tentando envio sem autenticação (pode falhar em alguns servidores)."
        )

    # Criar mensagem de e-mail
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = ", ".join(settings.email_to)
    msg["Subject"] = assunto

    # Adicionar versões texto e HTML (multipart/alternative)
    msg.set_content(corpo_texto)
    msg.add_alternative(corpo_html, subtype="html")

    # Anexar planilha se fornecida
    if anexo_xlsx and anexo_xlsx.exists():
        try:
            with open(anexo_xlsx, "rb") as f:
                dados_xlsx = f.read()
            msg.add_attachment(
                dados_xlsx,
                maintype="application",
                subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=anexo_xlsx.name,
            )
            log.info("Planilha XLSX anexada: %s (%.2f KB)", anexo_xlsx.name, len(dados_xlsx) / 1024)
        except Exception as exc:
            log.warning("Erro ao anexar planilha XLSX %s: %s. Continuando sem anexo.", anexo_xlsx, exc)

    # Enviar via SMTP
    try:
        log.info(
            "Enviando e-mail via SMTP %s:%s (TLS: %s) para %s destinatário(s)...",
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_use_tls,
            len(settings.email_to),
        )

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls()

            if settings.smtp_user and settings.smtp_pass:
                server.login(settings.smtp_user, settings.smtp_pass)

            server.send_message(msg)

        log.info("E-mail enviado com sucesso para: %s", ", ".join(settings.email_to))

    except smtplib.SMTPAuthenticationError as exc:
        log.error("Falha de autenticação SMTP: %s", exc)
        raise
    except smtplib.SMTPException as exc:
        log.error("Erro SMTP ao enviar e-mail: %s", exc)
        raise
    except Exception as exc:
        log.error("Erro inesperado ao enviar e-mail: %s", exc)
        raise

