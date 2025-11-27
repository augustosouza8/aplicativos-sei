#!/usr/bin/env python3
"""Script para listar processos coletados do SEI e identificar possíveis duplicatas."""

import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sei_client.client import SeiClient
from sei_client.config import load_settings
from collections import Counter

def main():
    print("=" * 70)
    print("LISTAGEM DE PROCESSOS DO SEI")
    print("=" * 70)
    
    settings = load_settings()
    client = SeiClient(settings=settings)
    
    try:
        print("\n[1/3] Fazendo login no SEI...")
        client.login()
        print(f"[OK] Login bem-sucedido. Unidade: {settings.unidade_alvo}")
        
        print("\n[2/3] Coletando processos...")
        from sei_client.models import FilterOptions, PaginationOptions
        
        filtros = FilterOptions()
        paginacao = PaginationOptions()
        
        todos_processos, processos_filtrados = client.collect_processes(filtros, paginacao)
        
        # Separar recebidos de gerados pela categoria
        processos_recebidos = [p for p in todos_processos if p.categoria == "Recebidos"]
        processos_gerados = [p for p in todos_processos if p.categoria == "Gerados"]
        
        print(f"\n[3/3] Análise dos processos coletados:")
        print(f"\n=== RESUMO ===")
        print(f"   - Recebidos: {len(processos_recebidos)} processos")
        print(f"   - Gerados: {len(processos_gerados)} processos")
        print(f"   - TOTAL: {len(todos_processos)} processos")
        
        # Verificar duplicatas por número de processo
        todos_numeros = [p.numero_processo for p in todos_processos]
        contador = Counter(todos_numeros)
        duplicatas = {num: count for num, count in contador.items() if count > 1}
        
        if duplicatas:
            print(f"\n[ATENCAO] DUPLICATAS ENCONTRADAS: {len(duplicatas)} processo(s) aparecem multiplas vezes")
            for num, count in list(duplicatas.items())[:10]:  # Mostrar primeiras 10
                print(f"   - {num}: aparece {count} vez(es)")
            if len(duplicatas) > 10:
                print(f"   ... e mais {len(duplicatas) - 10} duplicata(s)")
        else:
            print(f"\n[OK] Nenhuma duplicata encontrada (todos os processos sao unicos)")
        
        # Verificar duplicatas por ID de procedimento
        todos_ids = [p.id_procedimento for p in todos_processos]
        contador_ids = Counter(todos_ids)
        duplicatas_ids = {pid: count for pid, count in contador_ids.items() if count > 1}
        
        if duplicatas_ids:
            print(f"\n[ATENCAO] DUPLICATAS POR ID: {len(duplicatas_ids)} ID(s) aparecem multiplas vezes")
            for pid, count in list(duplicatas_ids.items())[:10]:
                print(f"   - ID {pid}: aparece {count} vez(es)")
        
        # Listar primeiros 20 processos recebidos
        print(f"\n=== PRIMEIROS 20 PROCESSOS RECEBIDOS ===")
        for i, proc in enumerate(processos_recebidos[:20], 1):
            print(f"   {i:2d}. {proc.numero_processo:25s} | ID: {proc.id_procedimento} | Categoria: {proc.categoria}")
        if len(processos_recebidos) > 20:
            print(f"   ... e mais {len(processos_recebidos) - 20} processo(s) recebido(s)")
        
        # Listar primeiros 20 processos gerados
        print(f"\n=== PRIMEIROS 20 PROCESSOS GERADOS ===")
        for i, proc in enumerate(processos_gerados[:20], 1):
            print(f"   {i:2d}. {proc.numero_processo:25s} | ID: {proc.id_procedimento} | Categoria: {proc.categoria}")
        if len(processos_gerados) > 20:
            print(f"   ... e mais {len(processos_gerados) - 20} processo(s) gerado(s)")
        
        # Verificar processos únicos por número
        processos_unicos = set(todos_numeros)
        print(f"\n=== ANALISE DE UNICIDADE ===")
        print(f"   - Total de números de processo: {len(todos_numeros)}")
        print(f"   - Processos únicos (por número): {len(processos_unicos)}")
        if len(todos_numeros) != len(processos_unicos):
            print(f"   [ATENCAO] Diferenca: {len(todos_numeros) - len(processos_unicos)} processo(s) duplicado(s)")
        
        # Listar todos os números de processo para verificação manual
        print(f"\n=== LISTA COMPLETA DE NUMEROS DE PROCESSO ===")
        print(f"\n   RECEBIDOS ({len(processos_recebidos)} processos):")
        for proc in sorted(processos_recebidos, key=lambda p: p.numero_processo):
            print(f"      {proc.numero_processo}")
        
        print(f"\n   GERADOS ({len(processos_gerados)} processos):")
        for proc in sorted(processos_gerados, key=lambda p: p.numero_processo):
            print(f"      {proc.numero_processo}")
        
        print(f"\n" + "=" * 70)
        print("Análise concluída!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERRO] Erro: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        client.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

