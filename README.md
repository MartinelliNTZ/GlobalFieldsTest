# 🌍 Global Fields of The World (FTW) - QGIS Integration

!QGIS
!Python
!DuckDB
!License

> **Democratizando o acesso a Big Data agrícola.** Este plugin é a ponte definitiva entre o poder do DuckDB e a infraestrutura da Source Cooperative, permitindo o streaming de talhões agrícolas globais diretamente no seu canvas.

---

## 🎯 1. A Visão: Por que construímos isso?
O setor agrícola gera terabytes de predições anuais. O desafio era: *Como permitir que um pesquisador no interior do Brasil visualize talhões de 2024 sem baixar 500GB de GeoParquet?*

Nossa solução foi implementar um **Cloud-Native Downloader** que:
- **Não baixa arquivos, faz streaming de queries**: O motor DuckDB lê apenas os bytes necessários.
- **Recorte Dinâmico**: O sistema entende o que você está vendo na tela e busca apenas aqueles dados.
- **Simplicidade Radical**: Ocultamos toda a complexidade de S3, SQL e Threads atrás de um único botão "Baixar Talhões".

## 🧠 2. Desafios de Engenharia (The War Stories)
O desenvolvimento não foi apenas "escrever código", foi uma batalha contra infraestruturas de rede e compatibilidade:

- **A Barreira do SSL/TLS**: Versões antigas de Python embutidas no QGIS falhavam no handshake com buckets S3 modernos. Enfrentamos erros de `IO Error: Connection error` que pareciam intransponíveis.
- **O Labirinto do Globbing**: Servidores HTTP não aceitam `*.parquet`. Tivemos que migrar toda a lógica para o protocolo nativo de S3 para permitir a listagem dinâmica de arquivos sem sacrificar a performance.
- **Gargalos de Memória**: Inicialmente, consultas em áreas muito grandes tentavam carregar milhões de polígonos. Implementamos travas de segurança e cálculos de área em graus quadrados para proteger o sistema do usuário.
- **Circularidade de Pacotes**: O ambiente de plugins do QGIS é sensível. Resolver `ImportError` em threads de background exigiu uma refatoração profunda na forma como o Python registra os módulos do plugin.

## 🛠️ 3. Arquitetura e Decisões Técnicas
Para garantir que o sistema fosse inquebrável, adotamos as melhores práticas de software:

### 🚄 DuckDB + Pushdown Espacial
Escolhemos o **DuckDB** com as extensões `spatial` e `httpfs`. A consulta SQL é injetada com filtros `struct_extract(bbox, ...)` diretamente no cabeçalho do Parquet. Isso significa que se você quer 1km², nós baixamos apenas alguns KB, não o arquivo inteiro.

### 🧵 Multithreading com QgsTask
A interface do QGIS nunca trava. Usamos a API `QgsTask` para delegar o processamento pesado ao background. O sistema de sinalização (`finished`, `setProgress`) mantém o usuário informado sem interromper o fluxo de trabalho.

### 🛡️ Defesa em Profundidade
- **S3 Vhost Style**: Abandonamos o `path-style` para usar `vhost`, garantindo compatibilidade com o roteamento da AWS.
- **Anonymous Auth**: Configuramos o acesso S3 para ignorar credenciais locais, permitindo que qualquer pessoa acesse os dados abertos sem configurar chaves AWS.

## 🚀 4. Por que este projeto é um sucesso?
Diferente de outros plugins que "quebram silenciosamente", o **Global Fields FTW** foi construído com foco em **Observabilidade**:

1. **Diagnósticos Verbosos**: Em vez de um erro genérico, o plugin analisa o log do DuckDB e informa se o erro é no Firewall, no SSL ou no Servidor.
2. **Resiliência de Formato**: O sistema tenta converter para **GeoPackage** (padrão ouro do QGIS). Se o ambiente do usuário não suportar a extensão GDAL do DuckDB, ele faz o fallback inteligente para **GeoParquet**, garantindo que o dado chegue à tela de qualquer jeito.
3. **UX de Primeiro Mundo**: O plugin detecta automaticamente o CRS do mapa e faz a reprojeção para EPSG:4326 em tempo real antes de enviar a query para a nuvem.

---

## 📦 Instalação e Uso

1. Certifique-se de ter o DuckDB instalado (`pip install duckdb`).
2. Abra o plugin, selecione sua área de interesse no mapa.
3. Escolha uma pasta de destino e clique em **Baixar Talhões**.
4. Veja a mágica do streaming acontecer.

## 🛠️ Tecnologias

| Categoria | Tecnologia |
| :--- | :--- |
| **Linguagem** | Python 3.9+ |
| **GIS Core** | PyQGIS (QGIS API) |
| **Database** | DuckDB (Spatial / HTTPFS) |
| **Data Format** | Cloud Optimized GeoParquet |
| **Infra** | AWS S3 (via Source Cooperative) |

---

*“Este não é apenas um plugin de download. É uma vitrine de como o Cloud-Native Geospatial pode ser integrado ao desktop GIS de forma elegante e robusta.”*

**Desenvolvido com ❤️ por Taylor Geospatial & Source Cooperative.**