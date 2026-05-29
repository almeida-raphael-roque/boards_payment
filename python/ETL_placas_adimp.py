import awswrangler as awr
import pandas as pd
import os
import datetime as dt  # Adicionado para gerar os timestamps dos logs

class ETL_relat_placas_adimp:
    PATHS = {
        "faturas_baixadas": r"C:\Users\raphael.almeida\Documents\Processos\relatorio_placas_adimplentes\sql\faturas_baixadas.sql",
        "faturas_posvencimento_recente": r"C:\Users\raphael.almeida\Documents\Processos\relatorio_placas_adimplentes\sql\faturas_posvencimento_recente.sql",
        "faturas_posvencimento_45": r"C:\Users\raphael.almeida\Documents\Processos\relatorio_placas_adimplentes\sql\faturas_posvencimento_45.sql",
        "output_dir": r"C:\Users\raphael.almeida\OneDrive - Grupo Unus\analise de dados - Arquivos em excel\Relatório Adimplência e Inadimplência"
    }

    def __init__(self):
        # Inicialização dos DataFrames
        self.df_adimplentes = None
        self.df_faturas_recente = None
        self.df_faturas_45 = None
        self.df_placas_pagamento = None

    def run(self):
        """Orquestrador principal da classe."""
        self.extrair_dados()
        self.processar_dados()
        self.salvar_excel()

    def ler_sql(self, path_key):
        """Lê os arquivos SQL baseado na chave do dicionário PATHS."""
        with open(self.PATHS[path_key], 'r', encoding='utf-8') as arquivo:
            return arquivo.read()

    def extrair_dados(self):
        """Executa as consultas no AWS Athena e popula os DataFrames iniciais."""
        print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] 1/3 - Extraindo dados do Athena...")
        
        self.df_adimplentes = awr.athena.read_sql_query(
            sql=self.ler_sql("faturas_baixadas"), database='silver'
        )
        
        self.df_faturas_recente = awr.athena.read_sql_query(
            sql=self.ler_sql("faturas_posvencimento_recente"), database='silver'
        )
        
        self.df_faturas_45 = awr.athena.read_sql_query(
            sql=self.ler_sql("faturas_posvencimento_45"), database='silver'
        )

    def aplicar_regras_negocio(self, df):
        """Centraliza a limpeza de clientes específicos a pedido do setor de Cobranças."""
        if df.empty:
            return df
        
        # Regra 1: Remover APROSSIL das empresas especificadas
        mask_aprossil = (
            (df['empresa'].isin(['Viavante', 'Stcoop', 'Segtruck'])) &
            (df['associado'] == "APROSSIL - ASSOCIACAO DE PROPRIETARIOS DE CAMINHOES DO SUL D")
        )
        df_filtrado = df[~mask_aprossil]
        
        # Regra 2: Remover associados com 'TESTE'
        df_filtrado = df_filtrado[~df_filtrado['associado'].str.contains('TESTE', na=False)]
        
        return df_filtrado

    def processar_dados(self):
        """Aplica filtros, regras de negócio e concatena as bases."""
        print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] 2/3 - Processando dataframes e aplicando regras de negócio...")
        
        # Gerando set de boletos pagos para filtro (mais rápido para validações "in")
        boletos_pagos = set(
            zip(
                self.df_adimplentes['ponteiro'],
                self.df_adimplentes['empresa'],
                self.df_adimplentes['conjunto']
            )
        )

        # Filtrando inadimplentes recentes (utilizando .copy() para evitar SettingWithCopyWarning)
        df_inadimplentes_recente = self.df_faturas_recente[
            ~self.df_faturas_recente.apply(
                lambda row: (row['ponteiro'], row['empresa'], row['conjunto']) in boletos_pagos, axis=1
            )
        ].copy()

        # Filtrando inadimplentes 45+
        df_inadimplentes_45 = self.df_faturas_45[
            ~self.df_faturas_45.apply(
                lambda row: (row['ponteiro'], row['empresa'], row['conjunto']) in boletos_pagos, axis=1
            )
        ].copy()

        # Aplicando regras de negócio (limpeza de associados)
        df_inadimplentes_recente = self.aplicar_regras_negocio(df_inadimplentes_recente)
        df_inadimplentes_45 = self.aplicar_regras_negocio(df_inadimplentes_45)

        # Adicionando categorias de pagamento
        df_inadimplentes_recente["pagamento"] = "inadimplente"
        df_inadimplentes_45["pagamento"] = "inadimplente 45+"
        self.df_adimplentes["pagamento"] = "adimplente"

        # Concatenando os resultados
        self.df_placas_pagamento = pd.concat(
            [df_inadimplentes_recente, df_inadimplentes_45, self.df_adimplentes], 
            ignore_index=True
        )

    def salvar_excel(self):
        """Salva o DataFrame final no formato Excel, substituindo o arquivo anterior se existir."""
        print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] 3/3 - Exportando relatório para Excel...")
        
        caminho_pasta = self.PATHS["output_dir"]
        caminho_arquivo = os.path.join(caminho_pasta, 'relatorio_adimplencia_inadimplencia.xlsx')
        
        os.makedirs(caminho_pasta, exist_ok=True)
        
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)
            print(f"[{dt.datetime.now().strftime('%H:%M:%S')}]       -> Arquivo antigo removido. Iniciando salvamento do novo arquivo...")
            
        self.df_placas_pagamento.to_excel(
            caminho_arquivo, 
            engine='openpyxl', 
            index=False, 
            sheet_name='faturas'
        )
        print(f"[{dt.datetime.now().strftime('%H:%M:%S')}]       -> Sucesso! Arquivo salvo em: {caminho_arquivo}")

    @classmethod
    def ETL_placas_adimp(cls):
        """Método de inicialização da classe com logs de tempo."""
        inicio = dt.datetime.now()
        print("\n=======================================================")
        print(f"[{inicio.strftime('%H:%M:%S')}] INICIANDO ETL DE ADIMPLÊNCIA")
        print("=======================================================\n")
        
        try:
            relatorio = cls()
            relatorio.run()
            status = "SUCESSO"
        except Exception as e:
            print(f"\n[{dt.datetime.now().strftime('%H:%M:%S')}] [ERRO CRÍTICO] O processo falhou: {e}")
            status = "FALHA"
        finally:
            fim = dt.datetime.now()
            duracao = fim - inicio
            print("\n=======================================================")
            print(f"[{fim.strftime('%H:%M:%S')}] PROCESSO FINALIZADO COM {status}")
            print(f"[{fim.strftime('%H:%M:%S')}] Tempo total de execução: {duracao}")
            print("=======================================================\n")

if __name__ == "__main__":
    ETL_relat_placas_adimp.ETL_placas_adimp()