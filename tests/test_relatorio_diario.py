"""Testes unitários para o módulo de relatório diário."""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List
from unittest.mock import MagicMock, patch

from sei_client import Documento, Processo
from sei_client.config import Settings, load_settings
from sei_client.relatorio_diario import (
    DailyReportSettings,
    _aplicar_limites_processos,
    _construir_corpo_email_html,
    _construir_corpo_email_texto,
    _identificar_processos_novos_e_atualizados,
    load_daily_report_settings,
)


def criar_processo_teste(numero: str, id_proc: str, categoria: str = "Recebidos") -> Processo:
    """Cria um processo de teste com valores padrão."""
    return Processo(
        numero_processo=numero,
        id_procedimento=id_proc,
        url=f"https://example.com/processo?id={id_proc}",
        visualizado=False,
        categoria=categoria,
        titulo=f"Processo {numero}",
        marcadores=["Teste"],
        documentos=[],
    )


def criar_documento_teste(id_doc: str, eh_novo: bool = False) -> Documento:
    """Cria um documento de teste."""
    return Documento(
        id_documento=id_doc,
        titulo=f"Documento {id_doc}",
        eh_novo=eh_novo,
    )


class TestIdentificarProcessosNovosEAtualizados(unittest.TestCase):
    """Testes para identificação de processos novos e atualizados."""

    def test_identifica_processos_novos(self) -> None:
        """Deve identificar processos ausentes no histórico como novos."""
        historico: Dict[str, Dict] = {
            "PROC-001": {
                "numero_processo": "0001/2025",
                "id_procedimento": "PROC-001",
                "marcadores": [],
                "documentos": [],
            }
        }

        processos = [
            criar_processo_teste("0001/2025", "PROC-001"),
            criar_processo_teste("0002/2025", "PROC-002"),  # Novo
            criar_processo_teste("0003/2025", "PROC-003"),  # Novo
        ]

        novos, atualizados = _identificar_processos_novos_e_atualizados(historico, processos)

        self.assertEqual(len(novos), 2)
        self.assertEqual(len(atualizados), 0)
        self.assertIn(processos[1], novos)
        self.assertIn(processos[2], novos)

    def test_identifica_processos_atualizados_por_marcadores(self) -> None:
        """Deve identificar processos com marcadores diferentes como atualizados."""
        historico: Dict[str, Dict] = {
            "PROC-001": {
                "numero_processo": "0001/2025",
                "id_procedimento": "PROC-001",
                "marcadores": ["Aguardando"],
                "documentos": [],
            }
        }

        processo = criar_processo_teste("0001/2025", "PROC-001")
        processo.marcadores = ["Assinado"]  # Mudou

        novos, atualizados = _identificar_processos_novos_e_atualizados(historico, [processo])

        self.assertEqual(len(novos), 0)
        self.assertEqual(len(atualizados), 1)
        self.assertIn(processo, atualizados)

    def test_identifica_processos_atualizados_por_documentos_novos(self) -> None:
        """Deve identificar processos com novos documentos como atualizados."""
        historico: Dict[str, Dict] = {
            "PROC-001": {
                "numero_processo": "0001/2025",
                "id_procedimento": "PROC-001",
                "marcadores": [],
                "documentos": [{"id_documento": "DOC-001"}],
            }
        }

        processo = criar_processo_teste("0001/2025", "PROC-001")
        processo.documentos = [
            criar_documento_teste("DOC-001"),
            criar_documento_teste("DOC-002", eh_novo=True),  # Novo documento
        ]

        novos, atualizados = _identificar_processos_novos_e_atualizados(historico, [processo])

        self.assertEqual(len(novos), 0)
        self.assertEqual(len(atualizados), 1)

    def test_identifica_processos_atualizados_por_indicadores(self) -> None:
        """Deve identificar processos com mudanças em indicadores como atualizados."""
        historico: Dict[str, Dict] = {
            "PROC-001": {
                "numero_processo": "0001/2025",
                "id_procedimento": "PROC-001",
                "tem_documentos_novos": False,
                "tem_anotacoes": False,
                "documentos": [],
            }
        }

        processo = criar_processo_teste("0001/2025", "PROC-001")
        processo.tem_documentos_novos = True  # Mudou

        novos, atualizados = _identificar_processos_novos_e_atualizados(historico, [processo])

        self.assertEqual(len(novos), 0)
        self.assertEqual(len(atualizados), 1)


class TestAplicarLimitesProcessos(unittest.TestCase):
    """Testes para aplicação de limites em processos novos."""

    def test_aplica_limite_correto(self) -> None:
        """Deve limitar a quantidade de processos selecionados."""
        processos = [criar_processo_teste(f"{i:04d}/2025", f"PROC-{i:03d}") for i in range(1, 21)]

        selecionados, ignorados = _aplicar_limites_processos(processos, max_novos=10)

        self.assertEqual(len(selecionados), 10)
        self.assertEqual(len(ignorados), 10)

    def test_nao_limita_se_quantidade_menor(self) -> None:
        """Não deve limitar se a quantidade for menor que o máximo."""
        processos = [criar_processo_teste(f"{i:04d}/2025", f"PROC-{i:03d}") for i in range(1, 6)]

        selecionados, ignorados = _aplicar_limites_processos(processos, max_novos=10)

        self.assertEqual(len(selecionados), 5)
        self.assertEqual(len(ignorados), 0)

    def test_mantem_ordem(self) -> None:
        """Deve manter a ordem original dos processos."""
        processos = [criar_processo_teste(f"{i:04d}/2025", f"PROC-{i:03d}") for i in range(1, 6)]

        selecionados, _ = _aplicar_limites_processos(processos, max_novos=3)

        self.assertEqual(len(selecionados), 3)
        self.assertEqual(selecionados[0].numero_processo, "0001/2025")
        self.assertEqual(selecionados[2].numero_processo, "0003/2025")


class TestConstruirCorpoEmailTexto(unittest.TestCase):
    """Testes para construção do corpo do e-mail em texto."""

    def test_constroi_corpo_com_processos_novos(self) -> None:
        """Deve construir corpo com seção de processos novos."""
        processos_novos = [
            criar_processo_teste("0001/2025", "PROC-001"),
            criar_processo_teste("0002/2025", "PROC-002"),
        ]

        corpo = _construir_corpo_email_texto(
            unidade="TESTE/UNIDADE",
            data_relatorio="2025-01-15",
            processos_novos=processos_novos,
            processos_atualizados=[],
            processos_ignorados={},
            processos_com_pdf=set(),
            caminhos_pdf={},
        )

        self.assertIn("Processos novos (2)", corpo)
        self.assertIn("0001/2025", corpo)
        self.assertIn("0002/2025", corpo)

    def test_constroi_corpo_com_processos_atualizados(self) -> None:
        """Deve construir corpo com seção de processos atualizados."""
        processo = criar_processo_teste("0001/2025", "PROC-001")
        processo.documentos = [criar_documento_teste("DOC-001", eh_novo=True)]

        corpo = _construir_corpo_email_texto(
            unidade="TESTE/UNIDADE",
            data_relatorio="2025-01-15",
            processos_novos=[],
            processos_atualizados=[processo],
            processos_ignorados={},
            processos_com_pdf=set(),
            caminhos_pdf={},
        )

        self.assertIn("Processos atualizados (1)", corpo)
        self.assertIn("0001/2025", corpo)
        self.assertIn("Novos docs: 1", corpo)

    def test_constroi_corpo_com_processos_ignorados(self) -> None:
        """Deve construir corpo com seção de processos ignorados."""
        processos_ignorados = {
            "PROC-001": "PDF > 100MB",
            "PROC-002": "Limite de processos novos excedido",
        }

        corpo = _construir_corpo_email_texto(
            unidade="TESTE/UNIDADE",
            data_relatorio="2025-01-15",
            processos_novos=[],
            processos_atualizados=[],
            processos_ignorados=processos_ignorados,
            processos_com_pdf=set(),
            caminhos_pdf={},
        )

        self.assertIn("Não analisados", corpo)
        self.assertIn("PROC-001", corpo)
        self.assertIn("PDF > 100MB", corpo)


class TestConstruirCorpoEmailHTML(unittest.TestCase):
    """Testes para construção do corpo do e-mail em HTML."""

    def test_constroi_html_valido(self) -> None:
        """Deve construir HTML válido com estrutura correta."""
        processos_novos = [criar_processo_teste("0001/2025", "PROC-001")]

        html = _construir_corpo_email_html(
            unidade="TESTE/UNIDADE",
            data_relatorio="2025-01-15",
            processos_novos=processos_novos,
            processos_atualizados=[],
            processos_ignorados={},
            processos_com_pdf=set(),
            caminhos_pdf={},
        )

        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<h1>", html)
        self.assertIn("TESTE/UNIDADE", html)
        self.assertIn("0001/2025", html)

    def test_html_contem_listas(self) -> None:
        """Deve conter elementos de lista HTML."""
        processos_novos = [criar_processo_teste("0001/2025", "PROC-001")]

        html = _construir_corpo_email_html(
            unidade="TESTE/UNIDADE",
            data_relatorio="2025-01-15",
            processos_novos=processos_novos,
            processos_atualizados=[],
            processos_ignorados={},
            processos_com_pdf=set(),
            caminhos_pdf={},
        )

        self.assertIn("<ul>", html)
        self.assertIn("<li>", html)


class TestDailyReportSettings(unittest.TestCase):
    """Testes para configurações do relatório diário."""

    def setUp(self) -> None:
        """Prepara ambiente de teste."""
        self.settings_base = load_settings()

    @patch.dict("os.environ", {}, clear=True)
    def test_load_settings_com_defaults(self) -> None:
        """Deve carregar configurações com valores padrão."""
        settings = load_daily_report_settings(self.settings_base)

        self.assertEqual(settings.max_processos_novos, 10)
        self.assertEqual(settings.max_tamanho_pdf_mb, 100)
        self.assertEqual(settings.smtp_port, 587)
        self.assertTrue(settings.smtp_use_tls)

    @patch.dict(
        "os.environ",
        {
            "SEI_REL_MAX_PROCESSOS_NOVOS_DIA": "5",
            "SEI_REL_MAX_TAMANHO_PDF_MB": "50",
            "SEI_REL_EMAIL_FROM": "teste@example.com",
            "SEI_REL_EMAIL_TO": "dest1@example.com,dest2@example.com",
            "SEI_REL_SMTP_HOST": "smtp.test.com",
            "SEI_REL_SMTP_PORT": "465",
            "SEI_REL_SMTP_USER": "user",
            "SEI_REL_SMTP_PASS": "pass",
            "SEI_REL_SMTP_USE_TLS": "false",
        },
        clear=True,
    )
    def test_load_settings_de_variaveis_ambiente(self) -> None:
        """Deve carregar configurações de variáveis de ambiente."""
        settings = load_daily_report_settings(self.settings_base)

        self.assertEqual(settings.max_processos_novos, 5)
        self.assertEqual(settings.max_tamanho_pdf_mb, 50)
        self.assertEqual(settings.email_from, "teste@example.com")
        self.assertEqual(len(settings.email_to), 2)
        self.assertIn("dest1@example.com", settings.email_to)
        self.assertEqual(settings.smtp_host, "smtp.test.com")
        self.assertEqual(settings.smtp_port, 465)
        self.assertEqual(settings.smtp_user, "user")
        self.assertEqual(settings.smtp_pass, "pass")
        self.assertFalse(settings.smtp_use_tls)


if __name__ == "__main__":
    unittest.main()

